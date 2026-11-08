"""P4 evaluation harness: 8 metrics x 3 arms over benchmark v2 (Part A/B).

New code (P3's eval/benchmark.py is imported, never modified). Adds:

- qualifier classification metric (measured/fitted/calculated/assumed);
- dev/eval split + evidence-format tiers (leakage control);
- three arms: offline deterministic, LLM without retrieval (empty
  evidence block), LLM with retrieval + evidence grounding;
- raw model outputs preserved verbatim (no manual correction before
  scoring).

Metrics (8): parameter identification, value extraction, unit accuracy,
provenance accuracy, condition completeness, qualifier classification,
abstention accuracy, false extraction rate.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .benchmark import (
    canonical_of,
    groups_of,
    resolve_passage,
    unit_matches,
    value_matches,
)
from ..literature.extraction import (
    EXTRACTION_PROMPT_SYSTEM,
    OfflineDeterministicExtractor,
    run_extraction,
)
from ..literature.index import SYNONYMS
from ..literature.ingest import DocumentStore
from ..literature.retrieval import RAGContext, RetrievalFacets, RetrievedSegment
from ..registry.textnorm import ascii_fold

VALUE_REL_TOL = 1e-6


class RetryClient:
    """Transport-level retry wrapper (transparent, key never logged).

    Retries transient network/HTTP failures only; malformed model output is
    NOT retried (a JSON failure is a legitimate benchmark outcome, scored as
    such and preserved verbatim).
    """

    def __init__(self, inner: Any, attempts: int = 3, backoff_s: float = 5.0):
        self._inner = inner
        self._attempts = attempts
        self._backoff_s = backoff_s
        self.name = inner.name
        self.base_url = inner.base_url
        self.model = inner.model

    def complete(self, system: str, user: str) -> str:
        last_exc: BaseException | None = None
        for attempt in range(self._attempts):
            try:
                return self._inner.complete(system, user)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_exc = exc
                if attempt < self._attempts - 1:
                    time.sleep(self._backoff_s * (attempt + 1))
        assert last_exc is not None
        raise last_exc


@dataclass
class GoldEntryP4:
    parameter_name: str
    value: float | None
    unit: str | None
    canonical_value: float | None = None
    canonical_unit: str | None = None
    qualifier: str | None = None
    qualifier_alt: str | None = None
    uncertainty: float | None = None


@dataclass
class BenchmarkItemP4:
    item_id: str
    document_id: str
    passage_probe: str
    facets: dict[str, Any]
    gold: list[GoldEntryP4] = field(default_factory=list)
    expect_abstain: bool = False
    split: str = "eval"  # "dev" (used during development) | "eval" (held out)
    tier: str = "same-doc-heldout"
    evidence_format: str = "paper-text"
    expert_note: str = ""
    conflict_note: str | None = None


def load_items_v2(path: str | Path) -> list[BenchmarkItemP4]:
    items = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        d["gold"] = [GoldEntryP4(**g) for g in d.get("gold", [])]
        items.append(BenchmarkItemP4(**d))
    return items


def _extracted_canonical(unit: str) -> str:
    return _canonical_unit(unit)[0]


# Scorer-local vocabulary extension (documented): the P3 synonym table has no
# maximum-concentration family, so held-out items with that parameter cannot
# group-match anything. P4 extends scoring (and only scoring) with:
_MAX_CONC_ALIASES = (
    "maximum concentration",
    "max concentration",
    "maximum lithium concentration",
)

# Leading scale factor in a unit token, e.g. "1e-15 m2 s-1" or the paper-table
# style "10-15 m2 s-1" (Table V's caption carries the 1e-15 scale). Only
# powers-of-ten and scientific e-notation are accepted as factors; plain
# decimals never factor (no silent unit reinterpretation, rule 6).
_SCALE_LEAD_RE = re.compile(
    r"^(10\^?\s*(-\d+)|[0-9]+(?:\.[0-9]+)?\s*[eE][-+]?[0-9]+)\s+(.+)$"
)


def _groups(name: Any) -> set[str]:
    """Name groups with underscores folded to spaces (LLM naming style) and
    the scorer-local extension groups."""
    n = ascii_fold(str(name).replace("_", " ").lower())
    out = groups_of(n)
    a_low = ascii_fold(n)
    for alias in _MAX_CONC_ALIASES:
        al = alias.lower()
        if al in a_low or a_low in al:
            out.add("max_concentration")
            break
    return out


def _scale_factor(token: str) -> tuple[str, float]:
    """Split a leading power-of-ten factor from a unit token."""
    t = ascii_fold(str(token)).replace("^", "").strip()
    m = _SCALE_LEAD_RE.match(t)
    if not m:
        return t, 1.0
    lead = ascii_fold(m.group(1)).replace(" ", "").lower()
    if lead.startswith("10"):
        factor = 10.0 ** float(lead[2:])
    else:
        factor = float(lead)
    return m.group(3), factor


def _canonical_unit(unit: str) -> tuple[str, float]:
    from ..registry.units import is_exchange_current_reaction_rate_unit, to_canonical

    rest, factor = _scale_factor(unit)
    if is_exchange_current_reaction_rate_unit(rest):
        return "A.m-2.(m3.mol-1)^1.5", factor
    canonical, f = to_canonical(rest)
    return canonical, factor * f


def _extracted_canonical_value(payload: dict[str, Any]) -> float | None:
    try:
        v = float(payload["value"])
        _canonical, factor = _canonical_unit(payload.get("unit") or "dimensionless")
        return v * factor
    except (ValueError, KeyError, TypeError):
        return None


def score_item(
    item: BenchmarkItemP4,
    candidates: list[dict[str, Any]],
    abstained: bool,
    raw_doc_text: str,
) -> dict[str, Any]:
    """Score one item's extraction candidates (never mutates them)."""
    golds = item.gold
    matched = value_ok = unit_ok = cond_ok = prov_ok = qual_ok = 0
    matched_groups: set[str] = set()
    for g in golds:
        ggroups = _groups(g.parameter_name)
        cands = [
            c for c in candidates if _groups(c.get("parameter_name", "")) & ggroups
        ]
        if not cands:
            continue
        matched += 1
        matched_groups |= ggroups
        if g.value is not None:
            gval, gunit = (
                (g.canonical_value, g.canonical_unit)
                if g.canonical_value is not None
                else canonical_of(
                    # reuse P3 GoldEntry converter
                    _to_p3_gold(g)
                )
            )
            if any(
                _value_match(c, gval) for c in cands
            ):
                value_ok += 1
            if any(
                _unit_match(c, gunit) for c in cands
            ):
                unit_ok += 1
        if any(
            c.get("temperature") is not None
            and c.get("cell_config") not in (None, "UNRESOLVED")
            for c in cands
        ):
            cond_ok += 1
        if any(
            _quote_verified(c, item.document_id, raw_doc_text) for c in cands
        ):
            prov_ok += 1
        if g.qualifier and any(
            c.get("qualifier") in _accepted_qualifiers(g) for c in cands
        ):
            qual_ok += 1
    gold_groups = (
        set().union(*[_groups(g.parameter_name) for g in golds]) if golds else set()
    )
    # false extraction = evidence-UNVERIFIED candidate (hallucination risk);
    # a candidate whose quote is verbatim in the source document but that
    # corresponds to no gold parameter is "excess but grounded" and tracked
    # separately (excess_extractions).
    excess = false_extractions = 0
    for c in candidates:
        if _groups(c.get("parameter_name", "")) & gold_groups:
            continue
        if _quote_verified(c, item.document_id, raw_doc_text):
            excess += 1
        else:
            false_extractions += 1
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
    )


def _to_p3_gold(g: GoldEntryP4):
    from .benchmark import GoldEntry

    return GoldEntry(
        parameter_name=g.parameter_name,
        value=g.value if g.value is not None else 0.0,
        unit=g.unit or "dimensionless",
        canonical_value=g.canonical_value,
        canonical_unit=g.canonical_unit,
    )


def _accepted_qualifiers(g: GoldEntryP4) -> set[str]:
    out = {g.qualifier} if g.qualifier else set()
    if g.qualifier_alt:
        out.add(g.qualifier_alt)
    return out


def _value_match(c: dict[str, Any], gval: float) -> bool:
    try:
        v = float(c["value"])
    except (ValueError, KeyError, TypeError):
        return False
    if value_matches(v, gval):
        return True
    cv = _extracted_canonical_value(c)
    return cv is not None and value_matches(cv, gval)


def _unit_match(c: dict[str, Any], gunit: str) -> bool:
    try:
        u = _extracted_canonical(c.get("unit") or "dimensionless")
    except KeyError:
        return False
    return unit_matches(u, gunit)


def _quote_verified(c: dict[str, Any], document_id: str, raw_doc_text: str) -> bool:
    """Whitespace-robust verbatim quote check against the full raw document.

    A quote is verified when it appears contiguously in the document after
    unicode-folding and whitespace collapsing (line breaks inside sentences
    are typography, not provenance). Ellipsis-spliced ("...") or reordered
    quotes are NOT accepted: they are reported as provenance failures.
    """

    def norm(text: str) -> str:
        return " ".join(ascii_fold(text).split())

    src = c.get("source") or {}
    if src.get("document_id") != document_id:
        return False
    quote = src.get("quote")
    if not quote:
        return False
    return norm(quote) in norm(raw_doc_text)


# --------------------------------------------------------------------------
# arms
# --------------------------------------------------------------------------
def _parse_llm_payloads(raw_content: str) -> tuple[list[dict[str, Any]], bool]:
    """Schema-validate an LLM raw output string into extraction candidates.

    Shared by run-time extraction and rescore-from-raw so both paths apply
    exactly the same filters (same parse, same UNRESOLVED skipping, same
    schema validation).
    """
    from ..literature.extraction import parse_llm_json, validate_extraction_schema

    candidates: list[dict[str, Any]] = []
    try:
        payloads = parse_llm_json(raw_content)
    except (ValueError, json.JSONDecodeError):
        return [], True
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        if payload.get("value") in ("UNRESOLVED", None) or payload.get(
            "parameter_name"
        ) == "UNRESOLVED":
            continue
        ok, _reason = validate_extraction_schema(payload)
        if ok:
            candidates.append(payload)
    return candidates, not candidates


def _llm_extract(client: Any, context: RAGContext) -> tuple[list[dict[str, Any]], bool, str]:
    """LLM extraction that preserves the raw model output verbatim.

    Mirrors P3 run_extraction's semantics (schema-validated candidates,
    UNRESOLVED entries skipped) without modifying P3 code.
    """
    raw_content = client.complete(EXTRACTION_PROMPT_SYSTEM, context.to_prompt_block())
    candidates, abstained = _parse_llm_payloads(raw_content)
    return candidates, abstained, raw_content


def run_arm(
    items: list[BenchmarkItemP4],
    store: DocumentStore,
    arm: str,
    client: Any | None = None,
    raw_sink: Any | None = None,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """Run one arm and return {per_item, totals, metrics, raw_outputs}.

    arm: "offline" | "llm_rag" | "llm_noretrieval"
    raw_outputs: verbatim model/provider outputs per item (no corrections).
    raw_sink: optional file handle; each item's raw output row is appended
    and flushed immediately (crash-resilient partial runs).
    on_progress: optional callback (index, item_id, n_candidates, abstained)
    called after each item for transparent long runs.
    """
    if arm == "offline":
        client = client or OfflineDeterministicExtractor()
    elif client is None:
        raise ValueError(f"arm {arm!r} requires an LLM client")
    per_item: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        passage = resolve_passage(store, item.document_id, item.passage_probe)
        facets = RetrievalFacets(**item.facets)
        if arm == "llm_noretrieval":
            segments: list[RetrievedSegment] = []
        else:
            segments = [
                RetrievedSegment(
                    segment_id=f"{item.item_id}#passage",
                    document_id=item.document_id,
                    page=None,
                    heading=None,
                    text=passage,
                    score=1.0,
                )
            ]
        context = RAGContext(
            query=facets.query_text(),
            facets=item.facets,
            segments=segments,
            retrieved_from=[item.document_id] if segments else [],
        )
        if arm == "offline":
            batch = run_extraction(client, context)
            candidates = [c.payload for c in batch.valid()]
            abstained = batch.abstained or not candidates
            raw_content = None
            raw_outputs.append(
                dict(
                    item_id=item.item_id,
                    provider=getattr(client, "name", arm),
                    raw=None,
                    n_candidates=len(batch.candidates),
                )
            )
        else:
            candidates, abstained, raw_content = _llm_extract(client, context)
            raw_outputs.append(
                dict(
                    item_id=item.item_id,
                    provider=getattr(client, "name", arm),
                    raw=raw_content,
                    n_candidates=len(candidates),
                )
            )
        row = raw_outputs[-1]
        if raw_sink is not None:
            raw_sink.write(json.dumps(row, sort_keys=True) + "\n")
            raw_sink.flush()
        raw_doc_text = (store.raw_dir / f"{item.document_id}.txt").read_text()
        per_item.append(score_item(item, candidates, abstained, raw_doc_text))
        if on_progress is not None:
            on_progress(idx, item.item_id, len(candidates), abstained, raw_content)
    return dict(arm=arm, per_item=per_item, raw_outputs=raw_outputs, metrics=_metrics(per_item))


def rescore_arm_from_raw(
    items: list[BenchmarkItemP4],
    store: DocumentStore,
    raw_rows: list[dict[str, Any]],
    arm: str,
) -> dict[str, Any]:
    """Deterministically re-score previously frozen raw model outputs.

    The raw rows ({item_id, raw, provider, n_candidates}) must come from a
    run under the same items list; scoring is re-derived via
    _parse_llm_payloads (identical filters to run-time). No new model calls.
    """
    by_id = {row["item_id"]: row for row in raw_rows}
    per_item: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []
    for item in items:
        row = by_id.get(item.item_id)
        if row is None:
            raise ValueError(f"rescore: missing raw row for {item.item_id}")
        if row.get("raw") is None:
            # offline-compatible row: re-derive with the deterministic
            # extractor (free, produces the identical result)
            r = run_arm([item], store, arm="offline")
            per_item.append(r["per_item"][0])
            raw_outputs.append(r["raw_outputs"][0])
            continue
        candidates, abstained = _parse_llm_payloads(row["raw"])
        raw_outputs.append(
            dict(
                item_id=item.item_id,
                provider=row.get("provider"),
                raw=row["raw"],
                n_candidates=len(candidates),
            )
        )
        raw_doc_text = (store.raw_dir / f"{item.document_id}.txt").read_text()
        per_item.append(score_item(item, candidates, abstained, raw_doc_text))
    return dict(arm=arm, per_item=per_item, raw_outputs=raw_outputs, metrics=_metrics(per_item))


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def frac(a: int, b: int) -> float:
        return (a / b) if b else float("nan")

    def agg(sub: list[dict[str, Any]]) -> dict[str, float]:
        g = sum(r["gold"] for r in sub)
        m = sum(r["matched"] for r in sub)
        return {
            "parameter_identification_accuracy": frac(sum(r["matched"] for r in sub), g),
            "value_extraction_accuracy": frac(sum(r["value_ok"] for r in sub), m),
            "unit_accuracy": frac(sum(r["unit_ok"] for r in sub), m),
            "provenance_accuracy": frac(sum(r["provenance_ok"] for r in sub), m),
            "condition_completeness": frac(sum(r["conditions_ok"] for r in sub), m),
            "qualifier_classification_accuracy": frac(
                sum(r["qualifier_ok"] for r in sub), m
            ),
            "abstention_accuracy": frac(
                sum(1 for r in sub if r["expect_abstain"] and r["abstained"]),
                sum(1 for r in sub if r["expect_abstain"]),
            ),
            "false_extraction_rate": frac(
                sum(r["false_extractions"] for r in sub),
                sum(r["n_extracted"] for r in sub),
            ),
        }

    out = {"all": agg(rows)}
    for split in ("dev", "eval"):
        sub = [r for r in rows if r["split"] == split]
        if sub:
            out[split] = agg(sub)
    for tier in sorted({r["tier"] for r in rows}):
        sub = [r for r in rows if r["tier"] == tier]
        out[f"tier:{tier}"] = agg(sub)
    return out
