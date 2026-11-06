"""P3 literature-extraction benchmark runner (Part H).

Usage:
    .venv-ecosystem312/bin/python benchmarks/p3/run_extraction_benchmark.py \
        [--provider offline|llm] [--out results/p3]

- provider=offline (default): deterministic non-LLM baseline (CI-safe).
- provider=llm: general-purpose LLM + retrieval baseline via the
  OpenAI-compatible endpoint (requires PYCL_LLM_API_KEY / PYCL_LLM_MODEL).

Scores the 7 metrics of docs/EXTRACTION_METHODOLOGY.md on the expert-
reviewed fixture data/eval/extraction_benchmark_v1.jsonl. No fine-tuning.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.eval.benchmark import load_items, run_benchmark  # noqa: E402
from pybamm_closed_loop.literature.extraction import (  # noqa: E402
    OfflineDeterministicExtractor,
    OpenAICompatibleClient,
)
from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

DOC_ID = "chen2020_jes_167_080534"
RAW_TEXT = (
    REPO_ROOT
    / "data/raw_documents/chen2020_jes_167_080534/chen2020_jes_167_080534_fulltext.txt"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["offline", "llm"], default="offline")
    ap.add_argument("--out", default="results/p3")
    ap.add_argument("--items", default="data/eval/extraction_benchmark_v1.jsonl")
    args = ap.parse_args()

    store = DocumentStore(REPO_ROOT / "data/literature_store")
    if DOC_ID not in {d.document_id for d in store.documents()}:
        store.ingest_text(
            DOC_ID,
            RAW_TEXT.read_text(),
            kind="paper",
            source_url="https://iopscience.iop.org/article/10.1149/1945-7111/ab9050",
            doi_or_url="10.1149/1945-7111/ab9050",
            title=(
                "Development of Experimental Techniques for Parameterization "
                "of Multi-scale Lithium-ion Battery Models"
            ),
            retrieved="2026-11-04",
        )
    items = load_items(REPO_ROOT / args.items)
    client = (
        OpenAICompatibleClient()
        if args.provider == "llm"
        else OfflineDeterministicExtractor()
    )
    report = run_benchmark(items, store, client=client)

    out_dir = REPO_ROOT / args.out / f"extraction_benchmark_v1_{args.provider}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        f"# Extraction benchmark v1 ({report['provider']})",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    for k, v in report["metrics"].items():
        lines.append(f"| {k} | {v:.3f} |")
    lines += ["", "## Per item", ""]
    for it in report["per_item"]:
        lines.append(
            f"- {it['item_id']}: extracted={it['n_extracted']} "
            f"identified={it['identified']}/{it['gold']} "
            f"value_ok={it['value_ok']} abstained={it['abstained']}"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report["metrics"], indent=2))
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
