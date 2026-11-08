"""Compute per-item consistency and unsupported-claim diagnostics for P5 (v3)."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
OUT = REPO / "results/p5/benchmark_v3"


def item_scores(row: dict) -> dict:
    g = row["gold"]
    m = row["matched"]

    def f(a: int, b: int) -> float | None:
        return a / b if b else None

    unsupported = 0
    for p in row.get("provenance", []):
        if not (p.get("document_match") and p.get("quote_verbatim")):
            unsupported += 1
    return {
        "id": f(m, g),
        "value": f(row["value_ok"], m),
        "unit": f(row["unit_ok"], m),
        "provenance": f(row["provenance_ok"], m),
        "condition": f(row["conditions_ok"], m),
        "qualifier": f(row["qualifier_ok"], m),
        "abstention": (1.0 if row["abstained"] else 0.0)
        if row["expect_abstain"]
        else None,
        "false_extraction": row["false_extractions"] > 0,
        "unsupported_claims": unsupported,
        "n_extracted": row["n_extracted"],
    }


def build(condition: str) -> dict:
    reports = [
        json.loads(p.read_text())
        for p in sorted(OUT.glob(f"report_{condition}_r*.json"))
    ]
    per_item: dict[str, list[dict]] = {}
    for report in reports:
        for row in report["per_item"]:
            per_item.setdefault(row["item_id"], []).append(item_scores(row))
    out: dict[str, dict] = {}
    for iid, runs in per_item.items():
        out[iid] = {}
        for key in (
            "id",
            "value",
            "unit",
            "provenance",
            "condition",
            "qualifier",
            "abstention",
        ):
            vals = [x[key] for x in runs if x[key] is not None]
            if not vals:
                out[iid][key] = None
                continue
            out[iid][key] = dict(
                mean=statistics.fmean(vals),
                std=statistics.pstdev(vals) if len(vals) > 1 else 0.0,
                n=len(vals),
                consistent=(max(vals) - min(vals) == 0),
            )
        out[iid]["false_any"] = any(x["false_extraction"] for x in runs)
        out[iid]["unsupported_mean"] = statistics.fmean(
            [x["unsupported_claims"] for x in runs]
        )
        out[iid]["n_extracted_mean"] = statistics.fmean(
            [x["n_extracted"] for x in runs]
        )
    (OUT / f"consistency_{condition}.json").write_text(
        json.dumps(out, indent=2, sort_keys=True)
    )
    return out


def main() -> int:
    for condition in ("retrieval_strict", "no_retrieval_memory", "no_retrieval_strict"):
        if list(OUT.glob(f"report_{condition}_r*.json")):
            c = build(condition)
            var = sum(
                1
                for ks in c.values()
                for v in ks.values()
                if isinstance(v, dict) and v.get("std", 0) > 0
            )
            print(condition, "items", len(c), "metric-variances", var)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
