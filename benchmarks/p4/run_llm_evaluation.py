"""P4 LLM extraction evaluation runner (Parts A + B).

Runs the benchmark v2 (dev + held-out eval) in up to three arms and writes
raw model outputs + metrics without any manual correction of model output.

Usage:
  PYCL_LLM_API_KEY=... PYCL_LLM_MODEL=... \
  .venv-ecosystem312/bin/python benchmarks/p4/run_llm_evaluation.py --arm all

Arms:
  offline         deterministic non-LLM baseline (no API needed)
  llm_rag         general-purpose LLM with retrieval + evidence grounding
  llm_noretrieval the same LLM with an empty evidence block (fair ablation)

Outputs (results/p4/benchmark_v2/):
  report_<arm>.json       metrics + per-item scores + run metadata
  raw_outputs_<arm>.jsonl verbatim model outputs (preserve, never corrected)
  summary.md              cross-arm comparison table

API keys are read from the environment and never written to any artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.eval.benchmark_p4 import (  # noqa: E402
    RetryClient,
    load_items_v2,
    rescore_arm_from_raw,
    run_arm,
)
from pybamm_closed_loop.literature.extraction import (  # noqa: E402
    OfflineDeterministicExtractor,
    OpenAICompatibleClient,
)
from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

OUT_DIR = REPO_ROOT / "results/p4/benchmark_v2"
STORE_DIR = REPO_ROOT / "data/literature_store"

DOCS = [
    dict(
        document_id="chen2020_supplement_s1",
        kind="supplement",
        title=(
            "Supplementary data for: Development of Experimental Techniques "
            "for Parameterization of Multi-scale Lithium-ion Battery Models"
        ),
        doi_or_url="10.1149/1945-7111/ab9050 (supplementary)",
        pdf=REPO_ROOT / "data/raw_documents/chen2020_supplement/JES_167_8_080534_suppdata.pdf",
    ),
    dict(
        document_id="pybamm_parameter_sets_docs",
        kind="structured-dataset",
        title="PyBaMM documentation: Parameter Sets (latest, retrieved 2026-11-08)",
        doi_or_url="https://docs.pybamm.org/en/latest/source/api/parameters/parameter_sets.html",
        text=REPO_ROOT
        / "data/raw_documents/pybamm_parameter_sets_docs/parameter_sets_fulltext.txt",
    ),
]


def ensure_documents(store: DocumentStore) -> None:
    have = {d.document_id for d in store.documents()}
    for doc in DOCS:
        if doc["document_id"] in have:
            continue
        if "pdf" in doc:
            store.ingest_pdf(
                doc["document_id"],
                doc["pdf"],
                kind=doc["kind"],
                title=doc["title"],
                doi_or_url=doc["doi_or_url"],
                retrieved="2026-11-08",
                meta={"page_numbering": "1-based PDF page indices (pypdf)"},
            )
        else:
            store.ingest_text(
                doc["document_id"],
                doc["text"].read_text(),
                kind=doc["kind"],
                title=doc["title"],
                source_url=doc["doi_or_url"],
                doi_or_url=doc["doi_or_url"],
                retrieved="2026-11-08",
            )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["offline", "llm_rag", "llm_noretrieval", "all"], default="all")
    ap.add_argument("--items", default="data/eval/extraction_benchmark_v2.jsonl")
    ap.add_argument("--split", choices=["dev", "eval", "all"], default="all")
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="re-score existing raw_outputs_<arm>.jsonl deterministically "
        "instead of calling the model again (offline arm is re-run cheaply)",
    )
    args = ap.parse_args()

    store = DocumentStore(STORE_DIR)
    ensure_documents(store)
    items = load_items_v2(REPO_ROOT / args.items)
    if args.split != "all":
        items = [it for it in items if it.split == args.split]

    arms = ["offline", "llm_rag", "llm_noretrieval"] if args.arm == "all" else [args.arm]
    need_call = any(a.startswith("llm") for a in arms) and not args.rescore
    llm_client = None
    if need_call:
        llm_client = OpenAICompatibleClient()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        print(f"=== running arm: {arm} ({len(items)} items) ===", flush=True)
        raw_path = OUT_DIR / f"raw_outputs_{arm}.jsonl"

        # ---- rescore mode: deterministic re-scoring of frozen raw outputs
        if args.rescore and arm != "offline":
            if not raw_path.exists():
                raise SystemExit(f"--rescore needs {raw_path.name}; run the arm first")
            raw_rows = [
                json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()
            ]
            report = rescore_arm_from_raw(items, store, raw_rows, arm=arm)
            report["run_metadata"] = dict(
                arm=arm,
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=report["raw_outputs"][0]["provider"] if report["raw_outputs"] else arm,
                items_file=args.items,
                split=args.split,
                n_items=len(items),
                rescored=True,
                rescored_from=str(raw_path.relative_to(REPO_ROOT)),
            )
            (OUT_DIR / f"report_{arm}.json").write_text(
                json.dumps(report, indent=2, sort_keys=True)
            )
            print(json.dumps(report["metrics"]["all"], indent=2), flush=True)
            continue

        if arm == "offline" and raw_path.exists():
            # deliberate re-run guard: a previous (possibly partial) run's
            # raw outputs exist; delete the file to regenerate this arm
            print(f"=== arm {arm}: {raw_path.name} exists, skipping (delete to re-run) ===", flush=True)
            continue

        # ---- normal run: fresh model calls (offline arm's raw file is
        # transient; it is deleted first so the guard above never blocks it)
        client = OfflineDeterministicExtractor() if arm == "offline" else None
        if arm == "offline":
            if raw_path.exists():
                raw_path.unlink()
        else:
            if raw_path.exists():
                # deliberate re-run guard: delete the file to re-run this arm
                print(f"=== arm {arm}: {raw_path.name} exists, skipping (delete to re-run) ===", flush=True)
                continue
            client = RetryClient(llm_client)  # transparent transport retries

        t0 = time.monotonic()
        with raw_path.open("w") as raw_sink:

            def progress(idx, item_id, n_cands, abstained, raw_content=None):
                tag = "abstain" if abstained else f"{n_cands} cand"
                print(
                    f"  [{arm}] {idx + 1}/{len(items)} {item_id}: {tag} "
                    f"({time.monotonic() - t0:.0f}s elapsed)",
                    flush=True,
                )

            report = run_arm(
                items,
                store,
                arm=arm,
                client=client,
                raw_sink=raw_sink,
                on_progress=progress,
            )
        report["run_metadata"] = dict(
            arm=arm,
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=getattr(client, "name", arm),
            endpoint_host=(llm_client.base_url if llm_client else None),
            model=(llm_client.model if llm_client else None),
            items_file=args.items,
            split=args.split,
            n_items=len(items),
        )
        (OUT_DIR / f"report_{arm}.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps(report["metrics"]["all"], indent=2))

    # summary merges every report present on disk (not just this run's arms)
    disk_reports = {
        p.stem.removeprefix("report_"): json.loads(p.read_text())
        for p in sorted(OUT_DIR.glob("report_*.json"))
    }
    if len(disk_reports) > 1 or "offline" in disk_reports:
        reports = disk_reports
        lines = [
            "# P4 benchmark v2 - cross-arm comparison",
            "",
            f"items: {len(items)} (split filter: {args.split}); generated "
            f"{datetime.now(timezone.utc).isoformat()}",
            "",
        ]
        for arm in reports:
            md = reports[arm].get("run_metadata", {}).get("model")
            lines.append(  # keep the provenance of each arm visible
                f"- arm `{arm}`: model={md or 'deterministic (no LLM)'}"
            )
        lines += [
            "",
            "| metric | " + " | ".join(reports) + " |",
            "|---|" + "---|" * len(reports),
        ]
        metric_names = list(next(iter(reports.values()))["metrics"]["all"].keys())
        for m in metric_names:
            row = [m]
            for arm in reports:
                v = reports[arm]["metrics"]["all"][m]
                row.append(f"{v:.3f}" if v == v else "n/a")
            lines.append("| " + " | ".join(row) + " |")
        for split in ("dev", "eval"):
            lines += ["", f"## {split} split", "", "| metric | " + " | ".join(reports) + " |", "|---|" + "---|" * len(reports)]
            for m in metric_names:
                row = [m]
                for arm in reports:
                    v = reports[arm]["metrics"].get(split, {}).get(m, float("nan"))
                    row.append(f"{v:.3f}" if v == v else "n/a")
                lines.append("| " + " | ".join(row) + " |")
        (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n")
        print(f"wrote {OUT_DIR}/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
