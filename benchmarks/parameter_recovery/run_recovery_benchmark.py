#!/usr/bin/env python
"""Synthetic parameter-recovery benchmark (TASK 1/3) over PyBOP.

Reproducible from a clean environment:
    .venv-ecosystem312/bin/python benchmarks/parameter_recovery/run_recovery_benchmark.py \
        --config configs/p2/recovery_single_1C.yaml --out results/p2

Writes a JSON report, a markdown summary and figures per run_id.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pybamm_closed_loop.calibration.fitting import (  # noqa: E402
    FitParameter,
    FitSpec,
    build_problem,
    run_fit_with_result,
)
from pybamm_closed_loop.calibration.synthetic import (  # noqa: E402
    SyntheticCondition,
    SyntheticSpec,
    generate_datasets,
)


def load_config(path: Path) -> tuple[SyntheticSpec, FitSpec, list[list[float]], dict]:
    raw = yaml.safe_load(path.read_text())
    multi_start = [list(map(float, row)) for row in raw.get("multi_start", [])]

    synth = SyntheticSpec(
        parameter_set=raw["parameter_set"],
        model_name=raw["model_name"],
        true_values={k: float(v) for k, v in raw["true_values"].items()},
        conditions=[SyntheticCondition(**c) for c in raw["conditions"]],
        noise_sigma_V=float(raw["noise_sigma_V"]),
        seed=int(raw["seed"]),
        description=raw.get("description", ""),
    )
    synth.validate()

    opt = raw.get("optimizer", {})
    fit = FitSpec(
        parameter_set=raw["parameter_set"],
        model_name=raw["model_name"],
        fit_parameters=[
            FitParameter(
                name=p["name"],
                initial_value=float(p["initial_value"]),
                bounds=(float(p["bounds"][0]), float(p["bounds"][1])),
            )
            for p in raw["fit_parameters"]
        ],
        cost=raw.get("cost", "SumSquaredError"),
        method=opt.get("method", "L-BFGS-B"),
        maxiter=int(opt.get("maxiter", 100)),
        jac=bool(opt.get("jac", True)),
        description=raw.get("description", ""),
    )
    fit.validate()
    return synth, fit, multi_start, raw


def _versions() -> dict:
    out = {}
    for pkg in ("pybamm", "pybop", "numpy", "scipy"):
        mod = __import__(pkg)
        out[pkg] = getattr(mod, "__version__", "unknown")
    return out


def _cost_convergence(result) -> list[float]:
    cc = getattr(result, "cost_convergence", None)
    if callable(cc):
        cc = cc()
    if cc is None:
        return []
    return [float(v) for v in np.asarray(cc).reshape(-1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    synth, fit, multi_start, raw = load_config(Path(args.config))
    out_dir = Path(args.out) / raw["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"run_id        : {raw['run_id']}")
    print(f"conditions    : {[c.name for c in synth.conditions]}")
    print(f"truth         : {synth.true_values}")
    print(f"noise sigma V : {synth.noise_sigma_V} | seed: {synth.seed}")

    t0 = time.perf_counter()
    datasets = generate_datasets(synth)
    gen_time = time.perf_counter() - t0
    data_meta = [m for _, _, m in datasets]
    for m in data_meta:
        print(f"  data [{m['condition']}]: {m['n_points']} pts, t_end={m['t_end_s']:.0f} s")

    problem, build_info = build_problem(datasets, fit)
    print(f"problem       : {build_info}")

    starts = multi_start or [fit.initial_values]
    runs = []
    for k, x0 in enumerate(starts):
        print(f"\n--- start {k}: {x0} ---")
        report, result = run_fit_with_result(
            problem, fit, truth=synth.true_values, initial_values=x0
        )
        report["start_index"] = k
        report["cost_convergence"] = _cost_convergence(result)
        runs.append(report)
        for name, rec in report.get("recovery", {}).items():
            print(f"  {name}: est={rec['estimate']:.5f} truth={rec['truth']:.5f} "
                  f"abs={rec['abs_error']:.5f}")
        print(f"  final_cost={report['final_cost']:.6e} runtime={report['runtime_s']:.1f} s "
              f"evals={report['n_evaluations']}")

    best_index = int(np.argmin([r["final_cost"] for r in runs]))
    report = {
        "run_id": raw["run_id"],
        "description": raw.get("description", ""),
        "config": raw,
        "generated_data": data_meta,
        "generation_runtime_s": float(gen_time),
        "build_info": build_info,
        "runs": runs,
        "best_run_index": best_index,
        "environment": {
            "python": platform.python_version(),
            "packages": _versions(),
        },
        "scientific_note": (
            "Synthetic recovery verifies the estimation workflow under the "
            "assumptions of the generating model. It is NOT experimental "
            "validation and does not prove identifiability."
        ),
    }
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Markdown summary
    lines = [
        f"# Recovery benchmark: {raw['run_id']}", "",
        f"- conditions: {', '.join(c.name for c in synth.conditions)}",
        f"- noise sigma: {synth.noise_sigma_V} V | seed: {synth.seed}",
        f"- cost: {fit.cost} | optimiser: {fit.method} (maxiter={fit.maxiter}, jac={fit.jac})",
        "", "| start | parameter | initial | estimate | truth | abs err |",
        "|---|---|---|---|---|---|",
    ]
    for r in runs:
        for p, (name, rec) in zip(r["parameters"], r.get("recovery", {}).items()):
            lines.append(
                f"| {r['start_index']} | {name} | {p['initial_value']:.3f} | "
                f"{rec['estimate']:.5f} | {rec['truth']:.5f} | {rec['abs_error']:.5f} |"
            )
    lines += ["", f"Best start: {best_index} (final cost {runs[best_index]['final_cost']:.6e})"]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Figures
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        names = list(synth.true_values)
        x = np.arange(len(starts))
        width = 0.35
        fig, ax = plt.subplots(figsize=(8, 4))
        for j, name in enumerate(names):
            ests = [r["recovery"][name]["estimate"] for r in runs]
            ax.bar(x + (j - 0.5) * width, ests, width, label=name.split(" electrode")[0])
            ax.axhline(synth.true_values[name], color=f"C{j}", linestyle="--", linewidth=1)
        ax.set_xticks(x, [f"start {k}" for k in range(len(starts))])
        ax.set_ylabel("estimate (dashed = truth)")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "recovery_estimates.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6, 4))
        for r in runs:
            if r["cost_convergence"]:
                ax.plot(r["cost_convergence"], label=f"start {r['start_index']}")
        ax.set_yscale("log")
        ax.set_xlabel("iteration")
        ax.set_ylabel("cost")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "cost_convergence.png", dpi=150)
        plt.close(fig)
    except Exception as exc:  # figures must never break the benchmark
        print(f"figure generation skipped: {exc}")

    print(f"\nwrote {json_path}")
    print(f"best start: {best_index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
