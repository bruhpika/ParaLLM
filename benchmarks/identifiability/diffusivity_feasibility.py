#!/usr/bin/env python
"""Diffusivity feasibility study (TASK 5) - sensitivity/correlation ONLY.

    .venv-ecosystem312/bin/python benchmarks/identifiability/diffusivity_feasibility.py \
        --config configs/p2/diffusivity_feasibility.yaml --out results/p2

Question 1: how sensitive is the voltage to solid/electrolyte diffusivities?
Question 2: do diffusivities trade off against kinetic parameters?
Question 3: do multiple C-rates break the trade-off?

Per the milestone, NO estimation is implemented here. Findings feed
docs/PARAMETER_SELECTION.md.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pybamm
import yaml


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def build_pv(parameter_set: str, model_name: str, steps: list[str], scales: dict[str, float]):
    """ParameterValues where study parameters are multiplied by scale factors.

    Scalar parameters are scaled directly; function parameters are wrapped so
    that their output is multiplied by the factor (study-only device; the
    original reported values are never overwritten in any persistent store).
    """
    pv = pybamm.ParameterValues(parameter_set)
    for name, factor in scales.items():
        if factor == 1.0:
            continue
        value = pv[name]
        if callable(value):
            original = value

            def scaled(*args, _orig=original, _f=factor):
                return _f * _orig(*args)

            pv.update({name: scaled})
        else:
            pv.update({name: float(value) * factor})
    return pv


def simulate_voltage(pv, model_name: str, steps: list[str], t_query: np.ndarray) -> np.ndarray:
    model = getattr(pybamm.lithium_ion, model_name)()
    experiment = pybamm.Experiment(list(steps))
    sol = pybamm.Simulation(model, parameter_values=pv, experiment=experiment).solve()
    return np.asarray(sol["Terminal voltage [V]"](t=t_query), dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    rel = float(cfg["rel_perturbation"])
    if rel == 0.0 or not np.isfinite(rel):
        # rel == 0 makes (yp - ym) / (2.0 * rel) divide 0 by 0: numpy returns
        # NaN, which would silently propagate into the correlation matrix and
        # emit invalid JSON (NaN literal). A finite non-zero step is required.
        raise ValueError(
            f"rel_perturbation must be a finite non-zero step, got {rel!r}"
        )

    out_dir = Path(args.out) / cfg["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    names = [p["name"] for p in cfg["study_parameters"]]
    kinds = {p["name"]: p["kind"] for p in cfg["study_parameters"]}
    base_scales = {n: 1.0 for n in names}

    report: dict = {
        "run_id": cfg["run_id"],
        "description": cfg.get("description", ""),
        "config": cfg,
        "environment": {
            "python": platform.python_version(),
            "packages": {p: getattr(__import__(p), "__version__", "?")
                         for p in ("pybamm", "numpy")},
        },
        "scientific_note": (
            "Sensitivity/conditioning study only. Scaling of function-based "
            "parameters is a study device applied in-memory; it is not a "
            "parameter estimate and not a persistent parameter change."
        ),
        "per_condition": {},
    }

    # Baseline values for context
    pv0 = pybamm.ParameterValues(cfg["parameter_set"])
    report["baseline_values"] = {
        n: (float(pv0[n]) if not callable(pv0[n]) else f"<callable:{pv0[n].__name__}>")
        for n in names
    }

    t0 = time.perf_counter()
    concat_jac_cols: dict[str, list] = {n: [] for n in names}
    concat_y: list = []

    for cond in cfg["conditions"]:
        t_query = np.linspace(10.0, 1800.0 if "1800" in cond["steps"][0] else (
            900.0 if "900" in cond["steps"][0] else 450.0), 24)
        y0 = simulate_voltage(
            build_pv(cfg["parameter_set"], cfg["model_name"], cond["steps"], base_scales),
            cfg["model_name"], cond["steps"], t_query,
        )
        y_scale = float(np.std(y0)) or 1.0
        sens = {}
        for name in names:
            sp = dict(base_scales)
            sp[name] = 1.0 + rel
            yp = simulate_voltage(
                build_pv(cfg["parameter_set"], cfg["model_name"], cond["steps"], sp),
                cfg["model_name"], cond["steps"], t_query,
            )
            sm = dict(base_scales)
            sm[name] = 1.0 - rel
            ym = simulate_voltage(
                build_pv(cfg["parameter_set"], cfg["model_name"], cond["steps"], sm),
                cfg["model_name"], cond["steps"], t_query,
            )
            dy = (yp - ym) / (2.0 * rel)  # d y / d (scale factor) at factor = 1
            sens[name] = dy / y_scale     # normalized sensitivity to scale factor
            concat_jac_cols[name].append(sens[name])
        concat_y.append(y0)
        report["per_condition"][cond["name"]] = {
            "steps": cond["steps"],
            "t_query_s": t_query.tolist(),
            "voltage_range_V": [float(y0.min()), float(y0.max())],
            "mean_abs_normalized_sensitivity": {
                n: float(np.abs(sens[n]).mean()) for n in names
            },
            "sensitivities": {n: sens[n].tolist() for n in names},
        }
        print(f"[{cond['name']}] mean |S|:",
              {n: round(float(np.abs(sens[n]).mean()), 3) for n in names})

    # Combined multi-condition sensitivity matrix and pairwise correlations
    jac = np.column_stack([
        np.concatenate(concat_jac_cols[n]) for n in names
    ])
    corr = np.corrcoef(jac.T)
    u, s, vt = np.linalg.svd(jac, full_matrices=False)

    def submatrix_stats(idx: list[int]) -> dict:
        sub = jac[:, idx]
        sv = np.linalg.svd(sub, compute_uv=False)
        return {
            "parameters": [names[i] for i in idx],
            "singular_values": sv.tolist(),
            "condition_number": float(sv.max() / sv.min()) if sv.min() > 0 else float("inf"),
            "correlation": np.corrcoef(sub.T).tolist() if len(idx) > 1 else [[1.0]],
        }

    report["combined"] = {
        "correlation_matrix": corr.tolist(),
        "singular_values": s.tolist(),
        "subsets": {
            "solid_diffusivities": submatrix_stats([0, 1]),
            "solid_plus_electrolyte_diffusivity": submatrix_stats([0, 1, 2]),
            "kinetics_only": submatrix_stats([3, 4]),
            "diffusivities_vs_kinetics": submatrix_stats([0, 1, 3, 4]),
            "all_five": submatrix_stats(list(range(len(names)))),
        },
    }

    # Single-condition (1C only) correlation for comparison
    jac_1c = np.column_stack([
        np.asarray(report["per_condition"]["1C"]["sensitivities"][n]) for n in names
    ])
    report["combined"]["correlation_matrix_1C_only"] = np.corrcoef(jac_1c.T).tolist()
    sv_1c = np.linalg.svd(jac_1c, compute_uv=False)
    report["combined"]["singular_values_1C_only"] = sv_1c.tolist()

    report["runtime_s"] = time.perf_counter() - t0
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Figures
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
        for ax, cond in zip(axes, cfg["conditions"]):
            blk = report["per_condition"][cond["name"]]
            t = np.asarray(blk["t_query_s"])
            for name in names:
                ax.plot(t, np.abs(blk["sensitivities"][name]),
                        label=name.split(" [")[0])
            ax.set_title(cond["name"])
            ax.set_xlabel("time [s]")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("|normalized sensitivity|")
        axes[-1].legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(out_dir / "sensitivity_vs_time.png", dpi=150)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        for ax, mat, title in [
            (axes[0], report["combined"]["correlation_matrix_1C_only"], "1C only"),
            (axes[1], report["combined"]["correlation_matrix"], "0.5C+1C+2C"),
        ]:
            im = ax.imshow(np.asarray(mat), vmin=-1, vmax=1, cmap="coolwarm")
            ax.set_xticks(range(len(names)), [n.split(" [")[0] for n in names],
                          rotation=45, ha="right", fontsize=7)
            ax.set_yticks(range(len(names)), [n.split(" [")[0] for n in names],
                          fontsize=7)
            ax.set_title(f"sensitivity correlation: {title}")
            for i in range(len(names)):
                for j in range(len(names)):
                    ax.text(j, i, f"{mat[i][j]:.2f}", ha="center", va="center",
                            fontsize=6)
            fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(out_dir / "sensitivity_correlation.png", dpi=150)
        plt.close(fig)
    except Exception as exc:
        print(f"figure generation skipped: {exc}")

    print(f"combined correlation:\n{np.round(corr, 3)}")
    print(f"wrote {out_dir} (runtime {report['runtime_s']:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
