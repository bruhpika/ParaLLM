"""P5 benchmark harness: P4 metrics on benchmark v3 under three knowledge
conditions, with repeated runs.

Conditions (Task 3 ablation; identical model, task, schema and rubric):

  retrieval_strict      evidence = the +/-260-char archive passage,
                        system prompt = P5 evidence-grounded rules
  no_retrieval_strict   evidence = none, same strict prompt
  no_retrieval_memory   evidence = none, P5 prompt that PERMITS model
                        knowledge (must mark document_id="model_knowledge",
                        quote null - no fabricated provenance)

Each condition is run N times (default 3) because the model has shown
run-to-run variance at temperature 0; raw outputs are preserved verbatim
for every repeat (${\\rm results}/p5/...). Metrics are the frozen P4 eight,
computed by P4's `_metrics` on P5-scored rows, so P4/P5 numbers are
comparable.

P5 vocabulary extensions (scoring-only, documented; P0-P4 code untouched):
- name groups: symmetry factor / charge transfer coefficient, activation
  energy, cell area;
- units: J.mol-1.K-1, kJ.mol-1.K-1, C.mol-1 (and A.s.mol-1), mol.L-1 (M);
- leading positive power-of-ten unit scales ("10^4 A.m-2").
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmark_p4 import (
    BenchmarkItemP4,
    GoldEntryP4,
    _accepted_qualifiers,
    _groups,
    _metrics,
    load_items_v2,
    resolve_passage,
)
from .extraction_prompt_p5 import build_extraction_prompt_p5, extract_with_prompt
from .provenance_p5 import ProvenanceReport, summarize, verify_candidate
from ..literature.extraction import run_extraction
from ..literature.ingest import DocumentStore
from ..literature.retrieval import RAGContext, RetrievalFacets, RetrievedSegment
from ..registry.textnorm import ascii_fold
from ..registry.units import is_exchange_current_reaction_rate_unit, to_canonical
from .benchmark import unit_matches, value_matches

# ---------------------------------------------------------------------------
# P5 scoring vocabulary extensions
# ---------------------------------------------------------------------------
_P5_SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
    "symmetry_factor": (
        "symmetry factor",
        "charge transfer coefficient",
        "charge-transfer coefficient",
        "transfer coefficient",
        "anodic transfer coefficient",
    ),
    "activation_energy": ("activation energy", "arrhenius activation"),
    "cell_area": ("cell area", "electrode area", "active area", "cross-sectional area"),
}

_P5_BASE_CONVERSIONS: dict[str, tuple[str, float]] = {
    "J.mol-1.K-1": ("J.mol-1.K-1", 1.0),
    "kJ.mol-1.K-1": ("J.mol-1.K-1", 1e3),
    "C.mol-1": ("C.mol-1", 1.0),
    "s.A.mol-1": ("C.mol-1", 1.0),
    "A.s.mol-1": ("C.mol-1", 1.0),
    "mol.L-1": ("mol.m-3", 1e3),
    "mol.l-1": ("mol.m-3", 1e3),
    "mol/l": ("mol.m-3", 1e3),
    "mol/L": ("mol.m-3", 1e3),
    "M": ("mol.m-3", 1e3),
    "mS.m-1": ("S.m-1", 1e-3),
    "mS.cm-1": ("S.m-1", 1e-1),
}


def _unit_variants(key: str) -> set[str]:
    variants = {key}
    variants.add(key.replace("/", "."))
    for v in list(variants):
        variants.add(v.replace(".", " "))
        variants.add(v.replace(" ", "."))
    return variants


_P5_CONVERSIONS: dict[str, tuple[str, float]] = {
    variant: target
    for key, target in _P5_BASE_CONVERSIONS.items()
    for variant in _unit_variants(key)
}

_P5_SCALE_RE = re.compile(
    r"^(10\^?\s*(-?\d+)|[0-9]+(?:\.[0-9]+)?\s*[eE][-+]?[0-9]+)\s+(.+)$"
)


def _groups_p5(name: Any) -> set[str]:
    out = _groups(name)
    low = ascii_fold(str(name).replace("_", " ").lower())
    for group, aliases in _P5_SYNONYM_GROUPS.items():
        for alias in aliases:
            a = ascii_fold(alias.lower())
            if a in low or low in a:
                out.add(group)
                break
    return out


def _scale_factor_p5(token: str) -> tuple[str, float]:
    t = ascii_fold(str(token)).replace("^", "").strip()
    m = _P5_SCALE_RE.match(t)
    if not m:
        return t, 1.0
    lead = ascii_fold(m.group(1)).replace(" ", "").lower()
    if lead.startswith("10"):
        factor = 10.0 ** float(lead[2:])
    else:
        factor = float(lead)
    return m.group(3), factor


def _canonical_unit_p5(unit: str) -> tuple[str, float]:
    rest, factor = _scale_factor_p5(unit)
    if is_exchange_current_reaction_rate_unit(rest):
        return "A.m-2.(m3.mol-1)^1.5", factor
    for candidate in (rest, rest.replace("/", "."), rest.replace(" ", ".")):
        if candidate in _P5_CONVERSIONS:
            canonical, f = _P5_CONVERSIONS[candidate]
            return canonical, factor * f
    canonical, f = to_canonical(rest)
    return canonical, factor * f


def _extracted_canonical_p5(payload: dict[str, Any]) -> float | None:
    try:
        v = float(payload["value"])
        _, factor = _canonical_unit_p5(payload.get("unit") or "dimensionless")
        return v * factor
    except (ValueError, KeyError, TypeError):
        return None


def _gold_canonical(g: GoldEntryP4) -> tuple[float, str] | None:
    if g.value is None:
        return None
    if g.canonical_value is not None and g.canonical_unit is not None:
        return float(g.canonical_value), g.canonical_unit
    if is_exchange_current_reaction_rate_unit(g.unit or "dimensionless"):
        return float(g.value), "A.m-2.(m3.mol-1)^1.5"
    canonical, factor = _canonical_unit_p5(g.unit or "dimensionless")
    return float(g.value) * factor, canonical


# ---------------------------------------------------------------------------
# scoring (P4 semantics + provenance diagnostics)
# ---------------------------------------------------------------------------
def score_item_p5(
    item: BenchmarkItemP4,
    candidates: list[dict[str, Any]],
    abstained: bool,
    store: DocumentStore,
    raw_doc_text: str,
) -> dict[str, Any]:
    golds = item.gold
    matched = value_ok = unit_ok = cond_ok = prov_ok = qual_ok = 0
    for g in golds:
        ggroups = _groups_p5(g.parameter_name)
        cands = [c for c in candidates if _groups_p5(c.get("parameter_name", "")) & ggroups]
        if not cands:
            continue
        matched += 1
        gold_canon = _gold_canonical(g)
        if gold_canon is not None:
            gval, gunit = gold_canon
            if any(_value_match_p5(c, gval) for c in cands):
                value_ok += 1
            if any(_unit_match_p5(c, gunit) for c in cands):
                unit_ok += 1
        if any(
            c.get("temperature") is not None
            and c.get("cell_config") not in (None, "UNRESOLVED")
            for c in cands
        ):
            cond_ok += 1
        if any(_prov_ok(c, store, item.document_id, raw_doc_text) for c in cands):
            prov_ok += 1
        if g.qualifier and any(c.get("qualifier") in _accepted_qualifiers(g) for c in cands):
            qual_ok += 1

    gold_groups = (
        set().union(*[_groups_p5(g.parameter_name) for g in golds]) if golds else set()
    )
    excess = false_extractions = 0
    for c in candidates:
        if _groups_p5(c.get("parameter_name", "")) & gold_groups:
            continue
        if _prov_ok(c, store, item.document_id, raw_doc_text):
            excess += 1
        else:
            false_extractions += 1

    provenance = [
        verify_candidate(c, store, item.document_id, raw_doc_text).to_dict()
        for c in candidates
    ]

    return dict(
        item_id=item.item_id,
        split=item.split,
        tier=item.tier,
        evidence_format=item.evidence_format,
        expect_abstain=item.expect_abstain,
        abstained=abstained,
        n_extracted=len(candidates),
        gold=len(golds),
        matched=matched,
        value_ok=value_ok,
        unit_ok=unit_ok,
        conditions_ok=cond_ok,
        provenance_ok=prov_ok,
        qualifier_ok=qual_ok,
        excess_extractions=excess,
        false_extractions=false_extractions,
        provenance=provenance,
    )


def _value_match_p5(c: dict[str, Any], gval: float) -> bool:
    try:
        v = float(c["value"])
    except (ValueError, KeyError, TypeError):
        return False
    if value_matches(v, gval):
        return True
    cv = _extracted_canonical_p5(c)
    return cv is not None and value_matches(cv, gval)


def _unit_match_p5(c: dict[str, Any], gunit: str) -> bool:
    try:
        u, _ = _canonical_unit_p5(c.get("unit") or "dimensionless")
    except KeyError:
        return False
    return unit_matches(u, gunit)


def _prov_ok(
    c: dict[str, Any], store: DocumentStore, document_id: str, raw_doc_text: str
) -> bool:
    """Frozen P4 provenance rule (doc id match + verbatim contiguous quote)."""
    report = verify_candidate(c, store, document_id, raw_doc_text)
    return report.document_match and report.quote_verbatim


def candidates_from_raw(raw_content: str) -> list[dict[str, Any]]:
    """Deterministic re-parse of a preserved raw model output (P4 filters)."""
    from ..literature.extraction import parse_llm_json
    from ..registry.model import validate_extraction_schema

    try:
        payloads = parse_llm_json(raw_content)
    except (ValueError, json.JSONDecodeError):
        return []
    out: list[dict[str, Any]] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        if payload.get("value") in ("UNRESOLVED", None) or payload.get(
            "parameter_name"
        ) == "UNRESOLVED":
            continue
        ok, _reason = validate_extraction_schema(payload)
        if ok:
            out.append(payload)
    return out


def rescore_from_raw(
    items: list[BenchmarkItemP4],
    store: DocumentStore,
    raw_rows: list[dict[str, Any]],
    condition: str,
    repeat: int,
) -> dict[str, Any]:
    """Re-score preserved raw outputs without model calls (reproducible)."""
    by_item = {r["item_id"]: r["raw"] for r in raw_rows if r.get("repeat") == repeat}
    per_item: list[dict[str, Any]] = []
    provenance_reports: list[ProvenanceReport] = []
    for item in items:
        if item.item_id not in by_item:
            raise SystemExit(
                f"raw outputs missing item {item.item_id} for {condition} r{repeat}"
            )
        raw_content = by_item[item.item_id]
        candidates = candidates_from_raw(raw_content) if raw_content else []
        abstained = not candidates
        raw_doc_text = (store.raw_dir / f"{item.document_id}.txt").read_text()
        per_item.append(
            score_item_p5(item, candidates, abstained, store, raw_doc_text)
        )
        provenance_reports.extend(
            verify_candidate(c, store, item.document_id, raw_doc_text)
            for c in candidates
        )
    return dict(
        condition=condition,
        repeat=repeat,
        per_item=per_item,
        raw_outputs=list(raw_rows),
        provenance_summary=summarize(provenance_reports),
        metrics=_metrics(per_item),
    )


# ---------------------------------------------------------------------------
# transport wrapper (T3 reliability; P4 RetryClient is not modified)
# ---------------------------------------------------------------------------
class RobustLLMClient:
    """Retries transient transport failures including HTTP chunking errors.

    P4's RetryClient covers URLError/Timeout/OSError but not
    http.client.IncompleteRead/RemoteDisconnected observed on long runs.
    """

    def __init__(self, inner: Any, attempts: int = 5, backoff_s: float = 6.0):
        import http.client as _http

        self._inner = inner
        self._attempts = attempts
        self._backoff_s = backoff_s
        self._transient = (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            _http.IncompleteRead,
            _http.RemoteDisconnected,
        )
        self.name = getattr(inner, "name", str(inner))
        self.base_url = getattr(inner, "base_url", None)
        self.model = getattr(inner, "model", None)

    def complete(self, system: str, user: str) -> str:
        import time as _time

        last: BaseException | None = None
        for attempt in range(self._attempts):
            try:
                return self._inner.complete(system, user)
            except self._transient as exc:
                last = exc
                if attempt < self._attempts - 1:
                    _time.sleep(self._backoff_s * (attempt + 1))
        assert last is not None
        raise last


# ---------------------------------------------------------------------------
# conditions
# ---------------------------------------------------------------------------
CONDITIONS = ("retrieval_strict", "no_retrieval_strict", "no_retrieval_memory")

_CONDITION_SPECS: dict[str, dict[str, Any]] = {
    "retrieval_strict": dict(memory_permitted=False, use_evidence=True),
    "no_retrieval_strict": dict(memory_permitted=False, use_evidence=False),
    "no_retrieval_memory": dict(memory_permitted=True, use_evidence=False),
}


def _user_block(item: BenchmarkItemP4, store: DocumentStore, use_evidence: bool) -> str:
    facets = RetrievalFacets(**item.facets)
    if use_evidence:
        passage = resolve_passage(store, item.document_id, item.passage_probe)
        context = RAGContext(
            query=facets.query_text(),
            facets=item.facets,
            segments=[
                RetrievedSegment(
                    segment_id=f"{item.item_id}#passage",
                    document_id=item.document_id,
                    page=None,
                    heading=None,
                    text=passage,
                    score=1.0,
                )
            ],
            retrieved_from=[item.document_id],
        )
        return context.to_prompt_block()
    return (
        f"QUERY: {facets.query_text()}\n\n"
        "(No evidence passages are available in this condition.)\n"
    )


def run_condition(
    items: list[BenchmarkItemP4],
    store: DocumentStore,
    condition: str,
    client: Any,
    raw_sink: Any | None = None,
    repeat_index: int = 0,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """One pass over ``items`` under one condition; raw outputs preserved."""
    if condition not in _CONDITION_SPECS and condition != "offline":
        raise ValueError(f"unknown condition {condition!r}")
    spec = _CONDITION_SPECS.get(condition, dict(memory_permitted=False, use_evidence=True))
    system_prompt = build_extraction_prompt_p5(memory_permitted=spec["memory_permitted"])

    per_item: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []
    provenance_reports: list[ProvenanceReport] = []

    for idx, item in enumerate(items):
        raw_doc_text = (store.raw_dir / f"{item.document_id}.txt").read_text()
        if condition == "offline":
            passage = resolve_passage(store, item.document_id, item.passage_probe)
            context = RAGContext(
                query=RetrievalFacets(**item.facets).query_text(),
                facets=item.facets,
                segments=[
                    RetrievedSegment(
                        segment_id=f"{item.item_id}#passage",
                        document_id=item.document_id,
                        page=None,
                        heading=None,
                        text=passage,
                        score=1.0,
                    )
                ],
                retrieved_from=[item.document_id],
            )
            batch = run_extraction(client, context)
            candidates = [c.payload for c in batch.valid()]
            abstained = batch.abstained or not candidates
            raw_content = None
        else:
            user_block = _user_block(item, store, spec["use_evidence"])
            candidates, abstained, raw_content = extract_with_prompt(
                client, system_prompt, user_block
            )

        row = dict(
            repeat=repeat_index,
            condition=condition,
            item_id=item.item_id,
            provider=getattr(client, "name", condition),
            raw=raw_content,
            n_candidates=len(candidates),
        )
        raw_outputs.append(row)
        if raw_sink is not None:
            raw_sink.write(json.dumps(row, sort_keys=True) + "\n")
            raw_sink.flush()

        scored = score_item_p5(item, candidates, abstained, store, raw_doc_text)
        per_item.append(scored)
        provenance_reports.extend(
            verify_candidate(c, store, item.document_id, raw_doc_text) for c in candidates
        )
        if on_progress is not None:
            on_progress(idx, item.item_id, len(candidates), abstained, raw_content)

    return dict(
        condition=condition,
        repeat=repeat_index,
        per_item=per_item,
        raw_outputs=raw_outputs,
        provenance_summary=summarize(provenance_reports),
        metrics=_metrics(per_item),
    )


_METRIC_NAMES = (
    "parameter_identification_accuracy",
    "value_extraction_accuracy",
    "unit_accuracy",
    "provenance_accuracy",
    "condition_completeness",
    "qualifier_classification_accuracy",
    "abstention_accuracy",
    "false_extraction_rate",
)


def aggregate_repeats(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean/std of every metric (all/dev/eval/tier:* scopes) across repeats."""
    scopes = sorted({scope for r in reports for scope in r["metrics"]})
    out: dict[str, Any] = {}
    for scope in scopes:
        out[scope] = {}
        for metric in _METRIC_NAMES:
            values = [
                r["metrics"][scope][metric]
                for r in reports
                if scope in r["metrics"] and metric in r["metrics"][scope]
            ]
            values = [v for v in values if v == v]  # drop NaN
            if not values:
                out[scope][metric] = dict(mean=None, std=None, n=0)
                continue
            out[scope][metric] = dict(
                mean=statistics.fmean(values),
                std=statistics.pstdev(values) if len(values) > 1 else 0.0,
                n=len(values),
            )
    prov = [r["provenance_summary"] for r in reports]
    out["provenance"] = {
        k: statistics.fmean([p[k] for p in prov]) if prov else None
        for k in (
            "document_match_rate",
            "quote_present_rate",
            "quote_verbatim_rate",
            "splice_rate",
            "paraphrase_warning_rate",
            "page_ok_rate",
            "locator_visible_rate",
            "conditions_ok_rate",
        )
    }
    return out


def load_items_v3(path: str | Path) -> list[BenchmarkItemP4]:
    """v3 fixture uses the P4 item schema verbatim (loader reused)."""
    return load_items_v2(path)
