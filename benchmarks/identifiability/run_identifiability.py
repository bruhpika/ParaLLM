#!/usr/bin/env python
"""Identifiability study for the volume-fraction pair (TASK 4).

    .venv-ecosystem312/bin/python benchmarks/identifiability/run_identifiability.py \
        --config configs/p2/identifiability.yaml --out results/p2

Components (each recorded independently; one failure never aborts the rest):
  A. pybop Hessian classification (2-parameter supported case)
  B. finite-difference Jacobian -> FIM, correlation, condition number
     (single- vs multi-condition comparison)
  C. coarse profile likelihood
  D. parametric bootstrap
  E. SALib Sobol indices (S1/ST vs time)
  F. short DifferentialEvolutionMCMC posterior (credible intervals, correlation)

Optimiser convergence is never used as evidence of identifiability
(scientific rule 7).
"""

from __future__ import annotations

import argparse
import copy
import json
import platform
import sys
import time
import traceback
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
from pybamm_closed_loop.calibration.identifiability import (  # noqa: E402
    finite_difference_jacobian,
    fim_diagnostics,
    hessian_classification,
    normalized_sensitivity,
    parametric_bootstrap,
    profile_likelihood,
    sobol_indices,
)
from pybamm_closed_loop.calibration.synthetic import (  # noqa: E402
    SyntheticCondition,
    SyntheticSpec,
    generate_datasets,
)


def load_recovery(path: Path) -> tuple[SyntheticSpec, FitSpec]:
    raw = yaml.safe_load(path.read_text())
    synth = SyntheticSpec(
        parameter_set=raw["parameter_set"],
        model_name=raw["model_name"],
        true_values={k: float(v) for k, v in raw["true_values"].items()},
        conditions=[SyntheticCondition(**c) for c in raw["conditions"]],
        noise_sigma_V=float(raw["noise_sigma_V"]),
        seed=int(raw["seed"]),
    )
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
    )
    return synth, fit


def make_predict(problem, names: list[str]):
    """Model prediction vector: concatenated simulated voltages at data times."""
    subs = getattr(problem, "problems", [problem])

    def predict(x: np.ndarray) -> np.ndarray:
        inputs = {n: float(v) for n, v in zip(names, np.asarray(x, dtype=float))}
        chunks = []
        for sub in subs:
            sol = sub.simulate(inputs)
            chunks.append(np.asarray(sol["Voltage [V]"].entries, dtype=float))
        return np.concatenate(chunks)

    return predict


def part(name: str, report: dict, fn):
    """Run one study part defensively and record result or error."""
    t0 = time.perf_counter()
    try:
        report[name] = fn()
        report[name]["runtime_s"] = time.perf_counter() - t0
        print(f"[{name}] OK ({report[name]['runtime_s']:.1f} s)")
    except Exception as exc:
        report[name] = {"error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc()[-1500:],
                        "runtime_s": time.perf_counter() - t0}
        print(f"[{name}] FAILED: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    out_dir = Path(args.out) / cfg["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    synth_s, fit_s = load_recovery(Path(cfg["recovery_config_single"]))
    synth_m, fit_m = load_recovery(Path(cfg["recovery_config_multi"]))
    names = fit_s.names
    bounds = fit_s.bounds_array
    truth = [synth_s.true_values[n] for n in names]

    print("generating datasets...")
    datasets_s = generate_datasets(synth_s)
    datasets_m = generate_datasets(synth_m)

    problem_s, _ = build_problem(datasets_s, fit_s)
    problem_m, _ = build_problem(datasets_m, fit_m)

    report: dict = {
        "run_id": cfg["run_id"],
        "description": cfg.get("description", ""),
        "config": cfg,
        "names": names,
        "truth": dict(zip(names, map(float, truth))),
        "environment": {
            "python": platform.python_version(),
            "packages": {p: getattr(__import__(p), "__version__", "?")
                         for p in ("pybamm", "pybop", "numpy", "scipy")},
        },
        "scientific_note": (
            "Diagnostics quantify sensitivity/correlation of this parameter "
            "pair under the generating model. Optimiser convergence alone is "
            "not evidence of identifiability."
        ),
    }

    # Evaluate point: estimates obtained by refitting the default start
    rep_s, res_s = run_fit_with_result(problem_s, fit_s, truth=synth_s.true_values)
    x_hat = np.array([p["estimate"] for p in rep_s["parameters"]])
    report["evaluation_point"] = {"x_hat": x_hat.tolist(), "single_fit": rep_s}
    print("evaluation point (single-condition refit):", x_hat)

    # --- A. Hessian classification (PyBOP, 2-parameter case) ---
    def hess_single():
        return hessian_classification(res_s)

    def hess_multi():
        _, res_m = run_fit_with_result(problem_m, fit_m, truth=synth_m.true_values)
        return hessian_classification(res_m)

    part("hessian_single", report, hess_single)
    part("hessian_multi", report, hess_multi)

    # --- B. FIM / correlation (single vs multi) ---
    def fim_block(problem):
        predict = make_predict(problem, names)
        jac = finite_difference_jacobian(predict, x_hat, rel_step=float(cfg["fd_rel_step"]),
                                         bounds=bounds)
        y0 = predict(x_hat)
        diag = fim_diagnostics(jac, sigma=synth_s.noise_sigma_V)
        y_scale = float(np.std(y0)) or 1.0
        sens = normalized_sensitivity(jac, x_hat, y_scale)
        return {
            "jacobian_shape": list(jac.shape),
            "correlation": np.asarray(diag["correlation"]).tolist(),
            "eigenvalues": np.asarray(diag["eigenvalues"]).tolist(),
            "condition_number": diag["condition_number"],
            "normalized_sensitivity_abs_mean": np.abs(sens).mean(axis=0).tolist(),
            "singular_values": np.linalg.svd(jac, compute_uv=False).tolist(),
        }

    part("fim_single", report, lambda: fim_block(problem_s))
    part("fim_multi", report, lambda: fim_block(problem_m))

    # --- C. profile likelihood (single condition) ---
    def profiles():
        out = {}
        for k, name in enumerate(names):
            other = 1 - k
            grid = np.linspace(
                x_hat[k] * (1 - float(cfg["profile_range_frac"])),
                x_hat[k] * (1 + float(cfg["profile_range_frac"])),
                int(cfg["profile_grid_points"]),
            )
            grid = np.clip(grid, bounds[k][0] + 1e-9, bounds[k][1] - 1e-9)
            free = names[other]

            def make_problem(fixed_values, _k=k, _other=other):
                fp = fit_s.fit_parameters[_other]
                spec = FitSpec(
                    parameter_set=fit_s.parameter_set,
                    model_name=fit_s.model_name,
                    fit_parameters=[
                        FitParameter(fp.name, fp.initial_value, fp.bounds)
                    ],
                    fixed_values=fixed_values,
                    maxiter=fit_s.maxiter,
                )
                pr, _ = build_problem(datasets_s, spec)
                return pr

            def run_fit_fn(problem, free_param, free_bounds, free_initial,
                           _other=other):
                fp = fit_s.fit_parameters[_other]
                spec = FitSpec(
                    parameter_set=fit_s.parameter_set,
                    model_name=fit_s.model_name,
                    fit_parameters=[FitParameter(fp.name, x_hat[_other], fp.bounds)],
                    maxiter=fit_s.maxiter,
                )
                rep = run_fit_with_result(problem, spec,
                                          initial_values=[float(x_hat[_other])])[0]
                return {"final_cost": rep["final_cost"],
                        "estimate": rep["parameters"][0]["estimate"]}

            out[name] = profile_likelihood(
                make_problem, run_fit_fn, name, grid, free,
                fit_s.fit_parameters[other].bounds, float(x_hat[other]),
            )
        return out

    part("profiles", report, profiles)

    # --- D. parametric bootstrap (single condition) ---
    def bootstrap():
        def refit(i: int):
            synth_b = copy.deepcopy(synth_s)
            synth_b.seed = synth_s.seed + int(cfg["bootstrap"]["seed_base"]) + i
            ds_b = generate_datasets(synth_b)
            pr_b, _ = build_problem(ds_b, fit_s)
            rep_b = run_fit_with_result(pr_b, fit_s, initial_values=list(x_hat))[0]
            return {
                "estimates": {p["name"]: p["estimate"] for p in rep_b["parameters"]},
                "final_cost": rep_b["final_cost"],
            }

        out = parametric_bootstrap(
            refit,
            n_boot=int(cfg["bootstrap"]["n_boot"]),
            seed=int(cfg["bootstrap"]["seed_base"]),
        )
        est = np.asarray(out["estimates"])
        out["truth"] = dict(zip(names, map(float, truth)))
        out["bias"] = (est.mean(axis=0) - np.asarray(truth)).tolist()
        out["per_parameter"] = {
            n: {"mean": float(est[:, j].mean()),
                "std": float(est[:, j].std(ddof=1)),
                "min": float(est[:, j].min()),
                "max": float(est[:, j].max()),
                "truth": float(truth[j])}
            for j, n in enumerate(names)
        }
        return out

    part("bootstrap", report, bootstrap)

    # --- E. Sobol indices (single + multi) ---
    def sobol_block(problem, label):
        predict = make_predict(problem, names)

        def model_fn(x):
            return predict(x)

        out = sobol_indices(
            model_fn,
            bounds=bounds,
            param_names=names,
            n_samples=int(cfg["sobol"]["n_samples"]),
            seed=int(cfg["sobol"]["seed"]),
        )
        out["label"] = label
        out["S1_mean"] = np.asarray(out["S1"]).mean(axis=0).tolist()
        out["ST_mean"] = np.asarray(out["ST"]).mean(axis=0).tolist()
        out["S1"] = np.asarray(out["S1"]).tolist()
        out["ST"] = np.asarray(out["ST"]).tolist()
        return out

    part("sobol_single", report, lambda: sobol_block(problem_s, "1C"))
    part("sobol_multi", report, lambda: sobol_block(problem_m, "0.5C+1C+2C"))

    # --- F. MCMC posterior (single condition) ---
    def mcmc():
        import pybop

        spec_l = FitSpec(
            parameter_set=fit_s.parameter_set,
            model_name=fit_s.model_name,
            fit_parameters=fit_s.fit_parameters,
            cost="GaussianLogLikelihood",
            sigma=synth_s.noise_sigma_V,
        )
        pr_l, _ = build_problem(datasets_s, spec_l)
        log_pdf = pybop.LogPosterior(pr_l.simulator, pr_l.cost)
        options = pybop.PintsSamplerOptions(
            n_chains=int(cfg["mcmc"]["n_chains"]),
            max_iterations=int(cfg["mcmc"]["max_iterations"]),
            warm_up_iterations=int(cfg["mcmc"]["warm_up_iterations"]),
        )
        sampler = pybop.DifferentialEvolutionMCMC(log_pdf, options=options)
        np.random.seed(int(cfg["mcmc"]["seed"]))  # PINTS samplers expose no seed
        result = sampler.run()
        summary = result.get_summary_statistics()
        samples = np.asarray(result.all_samples, dtype=float)
        return {
            "summary": {k: (v if isinstance(v, (int, float, str, type(None)))
                            else str(v)) for k, v in summary.items()},
            "posterior_mean": samples.mean(axis=0).tolist(),
            "posterior_std": samples.std(axis=0, ddof=1).tolist(),
            "posterior_corrcoef": np.corrcoef(samples.T).tolist()
            if samples.shape[0] > 1 else [],
            "ci95": np.percentile(samples, [2.5, 97.5], axis=0).T.tolist(),
            "n_samples": int(samples.shape[0]),
            "truth": dict(zip(names, map(float, truth))),
            "seed": int(cfg["mcmc"]["seed"]),
            # rhat() returns one value per parameter (array), not a scalar
            "rhat": [float(v) for v in np.atleast_1d(result.rhat())],
        }

    part("mcmc", report, mcmc)

    # ---------- write outputs ----------
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [f"# Identifiability study: {cfg['run_id']}", "",
             f"Parameters: {names}", f"Truth: {report['truth']}",
             f"Evaluation point: {x_hat.tolist()}", ""]
    for key in ("hessian_single", "hessian_multi", "fim_single", "fim_multi",
                "profiles", "bootstrap", "sobol_single", "sobol_multi", "mcmc"):
        blk = report.get(key, {})
        lines.append(f"## {key}")
        if "error" in blk:
            lines.append(f"- ERROR: {blk['error']}")
        else:
            for k2 in ("message", "condition_number", "correlation", "S1_mean",
                       "ST_mean", "per_parameter", "posterior_mean",
                       "posterior_std", "posterior_corrcoef", "ci95"):
                if k2 in blk:
                    lines.append(f"- {k2}: {blk[k2]}")
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- figures ----------
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = ["negative eps_s", "positive eps_s"]

        # profile likelihood
        if "error" not in report.get("profiles", {"error": 1}):
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            for ax, name in zip(axes, names):
                pr = report["profiles"][name]
                ax.plot(pr["grid"], pr["costs"], "o-")
                ax.axvline(report["truth"][name], color="g", linestyle="--",
                           label="truth")
                ax.axvline(x_hat[names.index(name)], color="r", linestyle=":",
                           label="estimate")
                ax.set_xlabel(name)
                ax.set_ylabel("profiled cost")
                ax.legend(fontsize=7)
                ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "profile_likelihood.png", dpi=150)
            plt.close(fig)

        # bootstrap scatter
        if "error" not in report.get("bootstrap", {"error": 1}):
            est = np.asarray(report["bootstrap"]["estimates"])
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.scatter(est[:, 0], est[:, 1], s=12, alpha=0.6, label="bootstrap")
            ax.scatter(*x_hat, color="r", marker="x", s=60, label="fit")
            ax.scatter(*truth, color="g", marker="*", s=120, label="truth")
            ax.set_xlabel(labels[0])
            ax.set_ylabel(labels[1])
            ax.legend(fontsize=7)
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "bootstrap_scatter.png", dpi=150)
            plt.close(fig)

        # sobol vs time
        for key, fname in (("sobol_single", "sobol_single.png"),
                           ("sobol_multi", "sobol_multi.png")):
            blk = report.get(key, {})
            if "error" in blk:
                continue
            s1 = np.asarray(blk["S1"])
            st = np.asarray(blk["ST"])
            fig, ax = plt.subplots(figsize=(7, 4))
            t_axis = np.linspace(0, 1, s1.shape[0])
            for j, lab in enumerate(labels):
                ax.plot(t_axis, s1[:, j], label=f"S1 {lab}")
                ax.plot(t_axis, st[:, j], linestyle="--", label=f"ST {lab}")
            ax.set_xlabel("fraction of observation window")
            ax.set_ylabel("Sobol index")
            ax.legend(fontsize=7)
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / fname, dpi=150)
            plt.close(fig)

        # mcmc histograms
        if "error" not in report.get("mcmc", {"error": 1}):
            blk = report["mcmc"]
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            # re-expect samples not stored in report; use ci95/mean markers
            for ax, name, lab in zip(axes, names, labels):
                lo, hi = blk["ci95"][names.index(name)]
                mean = blk["posterior_mean"][names.index(name)]
                std = blk["posterior_std"][names.index(name)]
                xs = np.linspace(lo - std, hi + std, 200)
                ax.plot(xs, np.exp(-0.5 * ((xs - mean) / std) ** 2))
                ax.axvline(report["truth"][name], color="g", linestyle="--")
                ax.set_title(f"{lab}: mean={mean:.4f}, 95% CI [{lo:.4f}, {hi:.4f}]",
                             fontsize=8)
                ax.set_xlabel(lab)
                ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "mcmc_posterior.png", dpi=150)
            plt.close(fig)
    except Exception as exc:
        print(f"figure generation skipped: {exc}")

    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
