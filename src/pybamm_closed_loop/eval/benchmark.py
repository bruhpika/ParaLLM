"""Literature-extraction benchmark harness (P3, Part H).

Small, expert-reviewed benchmark over the archived Chen2020 document.
Items carry passage probes (verbatim substrings of the archive), printed
gold values/units and expected abstentions. Metrics (7):

1. parameter identification accuracy
2. value extraction accuracy (canonical units, rel tol 1e-6)
3. unit correctness (canonical equality or dot-prefix, see unit_matches)
4. condition completeness (temperature + cell_config resolved)
5. provenance accuracy (correct document + quote verifiable in archive)
6. false extraction rate (extractions matching no gold parameter group)
7. abstention accuracy

The benchmark scores whatever extractor is provided; no fine-tuning is
performed (explicitly out of scope for P3).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..literature.extraction import (
    ExtractionBatch,
    OfflineDeterministicExtractor,
    run_extraction,
)
from ..literature.index import SYNONYMS
from ..literature.ingest import DocumentStore, validate_document_id
from ..literature.retrieval import RetrievalFacets
from ..registry.textnorm import ascii_fold
from ..registry.units import to_canonical, is_exchange_current_reaction_rate_unit

VALUE_REL_TOL = 1e-6


@dataclass
class GoldEntry:
    parameter_name: str
    value: float
    unit: str
    canonical_value: float | None = None
    canonical_unit: str | None = None


@dataclass
class BenchmarkItem:
    item_id: str
    document_id: str
    passage_probe: str
    facets: dict[str, Any]
    gold: list[GoldEntry] = field(default_factory=list)
    expect_abstain: bool = False
    expert_note: str = ""


def load_items(path: str | Path) -> list[BenchmarkItem]:
    items = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        items.append(
            BenchmarkItem(
                item_id=d["item_id"],
                document_id=d["document_id"],
                passage_probe=d["passage_probe"],
                facets=d.get("facets", {}),
                gold=[GoldEntry(**g) for g in d.get("gold", [])],
                expect_abstain=d.get("expect_abstain", False),
                expert_note=d.get("expert_note", ""),
            )
        )
    return items


def canonical_of(entry: GoldEntry) -> tuple[float, str]:
    if entry.canonical_value is not None and entry.canonical_unit:
        return entry.canonical_value, entry.canonical_unit
    if is_exchange_current_reaction_rate_unit(entry.unit):
        return float(entry.value), "A.m-2.(m3.mol-1)^1.5"
    canonical, factor = to_canonical(entry.unit)
    return float(entry.value) * factor, canonical


def groups_of(name: str) -> set[str]:
    low = ascii_fold(name.lower())
    out = set()
    for group, aliases in SYNONYMS.items():
        for alias in aliases:
            a = ascii_fold(alias.lower())
            if a in low or low in a:
                out.add(group)
                break
    return out


def unit_matches(extracted_unit: str, gold_unit: str) -> bool:
    if extracted_unit == gold_unit:
        return True
    return gold_unit.startswith(extracted_unit + ".")  # dot-prefix rule


def value_matches(extracted_value: float, gold_value: float) -> bool:
    if gold_value == 0:
        return abs(extracted_value) <= VALUE_REL_TOL
    return abs(extracted_value - gold_value) / abs(gold_value) <= VALUE_REL_TOL


def resolve_passage(store: DocumentStore, document_id: str, probe: str) -> str:
    """Return the archive passage around the probe (verbatim).

    The archived article text has no reliable paragraph/line structure, so
    the passage is a strict deterministic +/- 260-character window around
    the probe. No text is invented; offsets stay exact.
    """
    validate_document_id(document_id)  # document_id interpolates into a path
    raw = (store.raw_dir / f"{document_id}.txt").read_text()
    folded = ascii_fold(raw)
    idx = folded.find(ascii_fold(probe))
    if idx < 0:
        raise ValueError(f"probe {probe!r} not found in document {document_id}")
    lo = max(0, idx - 260)
    hi = min(len(raw), idx + len(probe) + 260)
    return raw[lo:hi]


def run_benchmark(
    items: list[BenchmarkItem],
    store: DocumentStore,
    client: Any | None = None,
) -> dict[str, Any]:
    client = client or OfflineDeterministicExtractor()
    per_item: list[dict[str, Any]] = []
    totals = dict(
        gold_params=0, identified=0, value_ok=0, unit_ok=0, conditions_ok=0,
        provenance_ok=0, extractions=0, false_extractions=0,
        abstain_items=0, abstain_correct=0,
    )
    for item in items:
        passage = resolve_passage(store, item.document_id, item.passage_probe)
        facets = RetrievalFacets(**item.facets)
        from ..literature.retrieval import RAGContext, RetrievedSegment

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
        batch: ExtractionBatch = run_extraction(client, context)
        extracted = batch.valid()
        totals["extractions"] += len(extracted)

        golds = item.gold
        totals["gold_params"] += len(golds)
        identified = value_ok = unit_ok = conditions_ok = provenance_ok = 0
        matched_groups: set[str] = set()
        for g in golds:
            gval, gunit = canonical_of(g)
            ggroups = groups_of(g.parameter_name)
            cands = [
                c
                for c in extracted
                if groups_of(c.payload["parameter_name"]) & ggroups
            ]
            if not cands:
                continue
            identified += 1
            matched_groups |= ggroups
            if any(
                value_matches(float(c.payload["value"]), gval)
                or value_matches(
                    float(c.payload["value"])
                    * (to_canonical(c.payload["unit"])[1]
                       if not is_exchange_current_reaction_rate_unit(c.payload["unit"])
                       else 1.0),
                    gval,
                )
                for c in cands
            ):
                value_ok += 1
            if any(
                unit_matches(
                    _extracted_canonical_unit(c.payload["unit"]), gunit
                )
                for c in cands
            ):
                unit_ok += 1
            if any(
                c.payload.get("temperature") is not None
                and c.payload.get("cell_config") not in (None, "UNRESOLVED")
                for c in cands
            ):
                conditions_ok += 1
            if any(
                (c.payload.get("source") or {}).get("document_id") == item.document_id
                and (c.payload.get("source") or {}).get("quote")
                and ascii_fold(c.payload["source"]["quote"]).strip()
                in ascii_fold(raw_text(store, item.document_id))
                for c in cands
            ):
                provenance_ok += 1
        false_extractions = sum(
            1
            for c in extracted
            if not (groups_of(c.payload["parameter_name"]) & set().union(
                *[groups_of(g.parameter_name) for g in golds] or [set()]
            ))
        )
        abstained = batch.abstained or not extracted
        if item.expect_abstain:
            totals["abstain_items"] += 1
            if abstained:
                totals["abstain_correct"] += 1
        totals["identified"] += identified
        totals["value_ok"] += value_ok
        totals["unit_ok"] += unit_ok
        totals["conditions_ok"] += conditions_ok
        totals["provenance_ok"] += provenance_ok
        totals["false_extractions"] += false_extractions
        per_item.append(
            dict(
                item_id=item.item_id,
                expect_abstain=item.expect_abstain,
                abstained=abstained,
                n_extracted=len(extracted),
                identified=identified,
                gold=len(golds),
                value_ok=value_ok,
                unit_ok=unit_ok,
                conditions_ok=conditions_ok,
                provenance_ok=provenance_ok,
                false_extractions=false_extractions,
                expert_note=item.expert_note,
            )
        )
    metrics = _metrics(totals)
    return dict(
        provider=getattr(client, "name", "unknown"),
        metrics=metrics,
        totals=totals,
        per_item=per_item,
    )


def _extracted_canonical_unit(unit: str) -> str:
    if is_exchange_current_reaction_rate_unit(unit):
        return "A.m-2.(m3.mol-1)^1.5"
    return to_canonical(unit)[0]


def raw_text(store: DocumentStore, document_id: str) -> str:
    validate_document_id(document_id)  # document_id interpolates into a path
    return (store.raw_dir / f"{document_id}.txt").read_text()


def _metrics(t: dict[str, int]) -> dict[str, float]:
    def frac(a: int, b: int) -> float:
        return (a / b) if b else float("nan")

    return {
        "parameter_identification_accuracy": frac(t["identified"], t["gold_params"]),
        "value_extraction_accuracy": frac(t["value_ok"], max(t["identified"], 1)),
        "unit_correctness": frac(t["unit_ok"], max(t["identified"], 1)),
        "condition_completeness": frac(t["conditions_ok"], max(t["identified"], 1)),
        "provenance_accuracy": frac(t["provenance_ok"], max(t["identified"], 1)),
        "false_extraction_rate": frac(t["false_extractions"], t["extractions"]),
        "abstention_accuracy": frac(t["abstain_correct"], t["abstain_items"]),
    }
