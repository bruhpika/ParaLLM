"""P5 Task 3 retrieval/knowledge ablation runner over benchmark v3.

Runs three conditions (same model, task, schema, scoring) with repeated
runs to expose run-to-run variance:

  retrieval_strict      +/-260-char archive passage + strict evidence prompt
  no_retrieval_strict   no evidence + strict prompt (must abstain)
  no_retrieval_memory   no evidence + knowledge-permitted prompt
                        (document_id="model_knowledge", quote null)

Optionally also the deterministic offline baseline (for regression context).

Usage:
  PYCL_LLM_API_KEY=... PYCL_LLM_BASE_URL=... PYCL_LLM_MODEL=... \
  .venv-ecosystem312/bin/python benchmarks/p5/run_ablation.py --condition all --repeats 3

Outputs (results/p5/benchmark_v3/):
  raw_outputs_<condition>_r<k>.jsonl   verbatim model outputs per repeat
  report_<condition>_r<k>.json       metrics + per-item scores + metadata
  aggregate_<condition>.json         mean/std across repeats
  summary.md                         cross-condition comparison (mean +/- std)

No API key is ever written to an artifact. Existing raw files are skipped
(delete them to re-run); --rescore re-scores frozen raw output deterministically.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.eval.benchmark_p5 import RobustLLMClient  # noqa: E402
from pybamm_closed_loop.eval.benchmark_p5 import (  # noqa: E402
    CONDITIONS,
    aggregate_repeats,
    load_items_v3,
    rescore_from_raw,
    run_condition,
)
from pybamm_closed_loop.literature.extraction import (  # noqa: E402
    OfflineDeterministicExtractor,
    OpenAICompatibleClient,
)
from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

OUT_DIR = REPO_ROOT / "results/p5/benchmark_v3"
STORE_DIR = REPO_ROOT / "data/literature_store"

ALL_CONDITIONS = ("offline",) + CONDITIONS


def _write_summary(disk: dict[str, dict], items_path: str, repeats: int) -> None:
    lines = [
        "# P5 benchmark v3 - retrieval/knowledge ablation",
        "",
        f"items: `{items_path}`; repeats per condition: {repeats}; "
        f"generated {datetime.now(timezone.utc).isoformat()}",
        "",
        "Means are over repeats; +/- is the population standard deviation.",
        "",
    ]
    models = {}
    for cond, r in disk.items():
        meta = r.get("run_metadata") or {}
        if isinstance(meta, list):
            meta = meta[0] if meta else {}
        models[cond] = meta.get("model")
    for cond in disk:
        lines.append(f"- `{cond}`: model={models[cond] or 'deterministic (no LLM)'}")
    lines += ["", "## all items (mean +/- std over repeats)", ""]
    header = "| metric | " + " | ".join(disk) + " |"
    lines += [header, "|---|" + "---|" * len(disk)]
    for metric in disk[next(iter(disk))]["aggregate"]["all"]:
        row = [metric]
        for cond in disk:
            cell = disk[cond]["aggregate"]["all"][metric]
            if cell["mean"] is None:
                row.append("n/a")
            else:
                row.append(f"{cell['mean']:.3f} +/- {cell['std']:.3f}")
        lines.append("| " + " | ".join(row) + " |")

    for scope in ("eval", "dev"):
        present = [c for c in disk if scope in disk[c]["aggregate"]]
        if not present:
            continue
        lines += ["", f"## {scope} split (mean +/- std)", "", "| metric | " + " | ".join(present) + " |", "|---|" + "---|" * len(present)]
        for metric in disk[present[0]]["aggregate"][scope]:
            row = [metric]
            for cond in present:
                cell = disk[cond]["aggregate"][scope][metric]
                row.append(
                    "n/a"
                    if cell["mean"] is None
                    else f"{cell['mean']:.3f} +/- {cell['std']:.3f}"
                )
            lines.append("| " + " | ".join(row) + " |")

    lines += ["", "## provenance diagnostics (mean over repeats)", ""]
    keys = list(disk[next(iter(disk))]["aggregate"]["provenance"])
    lines += ["| check | " + " | ".join(disk) + " |", "|---|" + "---|" * len(disk)]
    for key in keys:
        row = [key]
        for cond in disk:
            v = disk[cond]["aggregate"]["provenance"][key]
            row.append("n/a" if v is None or v != v else f"{v:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_DIR / 'summary.md'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--condition",
        choices=list(ALL_CONDITIONS) + ["all"],
        default="all",
    )
    ap.add_argument("--items", default="data/eval/extraction_benchmark_v3.jsonl")
    ap.add_argument("--split", choices=["dev", "eval", "all"], default="all")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="re-score frozen raw outputs instead of calling the model again",
    )
    args = ap.parse_args()

    store = DocumentStore(STORE_DIR)
    items = load_items_v3(REPO_ROOT / args.items)
    if args.split != "all":
        items = [it for it in items if it.split == args.split]

    conditions = list(ALL_CONDITIONS) if args.condition == "all" else [args.condition]
    needs_llm = any(c != "offline" for c in conditions) and not args.rescore
    llm_client = OpenAICompatibleClient() if needs_llm else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for condition in conditions:
        repeats = 1 if condition == "offline" else args.repeats
        reports: list[dict] = []
        for repeat in range(repeats):
            raw_path = OUT_DIR / f"raw_outputs_{condition}_r{repeat}.jsonl"
            if condition == "offline":
                raw_path = OUT_DIR / "raw_outputs_offline.jsonl"

            if args.rescore and condition != "offline":
                if not raw_path.exists():
                    raise SystemExit(f"--rescore needs {raw_path.name}")
                raw_rows = [
                    json.loads(line)
                    for line in raw_path.read_text().splitlines()
                    if line.strip()
                ]
                report = rescore_from_raw(items, store, raw_rows, condition, repeat)
                report["run_metadata"] = dict(
                    condition=condition,
                    repeat=repeat,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    items_file=args.items,
                    split=args.split,
                    n_items=len(items),
                    rescored=True,
                    rescored_from=str(raw_path.relative_to(REPO_ROOT)),
                )
            else:
                if (
                    condition == "offline"
                    and raw_path.exists()
                    and not (OUT_DIR / f"report_{condition}_r{repeat}.json").exists()
                ):
                    raw_path.unlink()
                if raw_path.exists():
                    print(
                        f"=== {condition} r{repeat}: {raw_path.name} exists, "
                        "skipping (delete to re-run) ===",
                        flush=True,
                    )
                    reports.append(json.loads((OUT_DIR / f"report_{condition}_r{repeat}.json").read_text()))
                    continue
                if condition == "offline":
                    client = OfflineDeterministicExtractor()
                else:
                    client = RobustLLMClient(llm_client)

                print(
                    f"=== condition {condition} repeat {repeat + 1}/{repeats} "
                    f"({len(items)} items) ===",
                    flush=True,
                )
                t0 = time.monotonic()
                with raw_path.open("w") as raw_sink:

                    def progress(idx, item_id, n_cands, abstained, raw_content=None):
                        tag = "abstain" if abstained else f"{n_cands} cand"
                        print(
                            f"  [{condition} r{repeat}] {idx + 1}/{len(items)} "
                            f"{item_id}: {tag} ({time.monotonic() - t0:.0f}s)",
                            flush=True,
                        )

                    report = run_condition(
                        items,
                        store,
                        condition=condition,
                        client=client,
                        raw_sink=raw_sink,
                        repeat_index=repeat,
                        on_progress=progress,
                    )
                report["run_metadata"] = dict(
                    condition=condition,
                    repeat=repeat,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider=getattr(client, "name", condition),
                    endpoint_host=(llm_client.base_url if llm_client else None),
                    model=(llm_client.model if llm_client else None),
                    items_file=args.items,
                    split=args.split,
                    n_items=len(items),
                    temperature=0,
                )
            (OUT_DIR / f"report_{condition}_r{repeat}.json").write_text(
                json.dumps(report, indent=2, sort_keys=True)
            )
            print(json.dumps(report["metrics"]["all"], indent=2), flush=True)
            reports.append(report)

        aggregate = aggregate_repeats(reports)
        (OUT_DIR / f"aggregate_{condition}.json").write_text(
            json.dumps(
                dict(
                    condition=condition,
                    repeats=len(reports),
                    aggregate=aggregate,
                    run_metadata=[r.get("run_metadata", {}) for r in reports],
                ),
                indent=2,
                sort_keys=True,
            )
        )

    disk: dict[str, dict] = {}
    for path in sorted(OUT_DIR.glob("aggregate_*.json")):
        payload = json.loads(path.read_text())
        disk[payload["condition"]] = payload
    if disk:
        _write_summary(disk, args.items, args.repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
