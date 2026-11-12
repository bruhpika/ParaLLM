"""Measure condition coverage of the evidence handed to the extractor (V2.5).

Deterministic, no LLM: for every benchmark item it compares the *compact*
±260-character window (v0.1 behaviour) with the *condition-aware* window
(V2.5) and reports which condition classes become available to the extractor.

This is an **evidence-side** metric. It says how much condition information the
retrieval layer supplies; whether the extractor then *uses* it is the
LLM-side condition-completeness metric (measured separately, on a private v4).

Usage:
    .venv-ecosystem312/bin/python benchmarks/v2/measure_condition_coverage.py \
        --items data/eval/extraction_benchmark_v3.jsonl \
        --out results/v2/condition_coverage
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.eval.benchmark_p4 import resolve_passage  # noqa: E402
from pybamm_closed_loop.literature.evidence import (  # noqa: E402
    build_evidence_window,
    document_conditions,
    extract_conditions,
)
from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

CLASSES = ("temperature", "soc", "c_rate", "cell", "chemistry", "method")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="data/eval/extraction_benchmark_v3.jsonl")
    ap.add_argument("--out", default="results/v2/condition_coverage")
    ap.add_argument("--compact-chars", type=int, default=260)
    ap.add_argument("--expand-chars", type=int, default=900)
    args = ap.parse_args()

    store = DocumentStore(REPO_ROOT / "data/literature_store")
    items = [
        json.loads(line)
        for line in (REPO_ROOT / args.items).read_text().splitlines()
        if line.strip()
    ]

    per_item = []
    counts = {
        "compact": {c: 0 for c in CLASSES},
        "expanded": {c: 0 for c in CLASSES},
        "with_document_conditions": {c: 0 for c in CLASSES},
        "any": {c: 0 for c in CLASSES},
    }
    n_items = 0
    for item in items:
        document_id = item["document_id"]
        probe = item["passage_probe"]
        raw = (store.raw_dir / f"{document_id}.txt").read_text()
        try:
            compact_text = resolve_passage(store, document_id, probe)
            window = build_evidence_window(
                raw,
                document_id,
                probe,
                compact_chars=args.compact_chars,
                expand_chars=args.expand_chars,
            )
        except ValueError:
            continue
        n_items += 1
        c_compact = extract_conditions(compact_text).coverage()
        c_expanded = window.conditions.coverage()
        doc_conditions = document_conditions(raw)
        c_doc = doc_conditions.coverage()
        for c in CLASSES:
            counts["compact"][c] += int(c_compact[c])
            counts["expanded"][c] += int(c_expanded[c])
            counts["with_document_conditions"][c] += int(c_expanded[c] or c_doc[c])
            counts["any"][c] += int(c_compact[c] or c_expanded[c] or c_doc[c])
        per_item.append(
            {
                "item_id": item["item_id"],
                "document_id": document_id,
                "tier": item.get("tier"),
                "compact_chars": len(compact_text),
                "expanded_chars": len(window.text),
                "coverage_compact": c_compact,
                "coverage_expanded": c_expanded,
                "coverage_document_conditions": c_doc,
                "newly_available": [c for c in CLASSES if c_expanded[c] and not c_compact[c]],
                "newly_available_with_document_conditions": [
                    c for c in CLASSES if (c_expanded[c] or c_doc[c]) and not c_compact[c]
                ],
            }
        )

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "items_file": args.items,
        "n_items": n_items,
        "compact_chars": args.compact_chars,
        "expand_chars": args.expand_chars,
        "class_coverage_rates": {
            mode: {c: (counts[mode][c] / n_items if n_items else float("nan")) for c in CLASSES}
            for mode in ("compact", "expanded", "with_document_conditions", "any")
        },
        "note": (
            "Evidence-side metric (deterministic, no LLM): the share of items whose "
            "evidence window contains each condition class. It does not measure whether "
            "the extractor uses the conditions."
        ),
    }

    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (out_dir / "per_item.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in per_item) + "\n"
    )

    lines = [
        "# V2.5 — condition coverage of the evidence block (deterministic)",
        "",
        f"items: `{args.items}` (n={n_items}); compact ±{args.compact_chars} chars vs "
        f"condition-aware ±{args.expand_chars} chars (+ document-level setup sentences)",
        "",
        "| condition class | compact (v0.1) | expanded window | + document conditions | either |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in CLASSES:
        lines.append(
            f"| {c} | {summary['class_coverage_rates']['compact'][c]:.3f} | "
            f"{summary['class_coverage_rates']['expanded'][c]:.3f} | "
            f"{summary['class_coverage_rates']['with_document_conditions'][c]:.3f} | "
            f"{summary['class_coverage_rates']['any'][c]:.3f} |"
        )
    lines += [
        "",
        "Evidence-side metric only: it measures how much condition information the "
        "retrieval layer supplies, not whether the extractor uses it.",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines))
    print(json.dumps(summary["class_coverage_rates"], indent=2))
    print(f"wrote {out_dir}/summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
