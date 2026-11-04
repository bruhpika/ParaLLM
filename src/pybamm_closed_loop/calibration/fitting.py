"""Bounded parameter fitting via PyBOP (adapter only - no custom optimizers).

Builds pybop.Problem / pybop.MetaProblem from datasets + a FitSpec, runs the
requested PyBOP optimiser, and returns a JSON-serialisable report that echoes
every configuration detail (scientific reproducibility rules).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pybamm
import pybop


@dataclass
class FitParameter:
    """One parameter to be estimated."""

    name: str
    initial_value: float
    bounds: tuple[float, float]

    def validate(self) -> None:
        lo, hi = self.bounds
        if not lo < hi:
            raise ValueError(f"{self.name}: bounds must satisfy lo < hi")
        if not lo <= self.initial_value <= hi:
            raise ValueError(f"{self.name}: initial_value outside bounds")


@dataclass
class FitSpec:
    """Configuration of a fitting run."""

    parameter_set: str
    model_name: str
    fit_parameters: list[FitParameter]
    cost: str = "SumSquaredError"
    method: str = "L-BFGS-B"
    maxiter: int = 100
    jac: bool = True
    sigma: float | None = None  # for GaussianLogLikelihood
    fixed_values: dict[str, float] = field(default_factory=dict)  # pinned, not fitted
    description: str = ""

    def validate(self) -> None:
        if not self.fit_parameters:
            raise ValueError("fit_parameters must not be empty")
        for p in self.fit_parameters:
            p.validate()
        if self.cost not in ("SumSquaredError", "GaussianLogLikelihood",
                             "GaussianLogLikelihoodKnownSigma"):
            raise ValueError(f"unsupported cost {self.cost!r}")
        if self.cost != "SumSquaredError" and self.sigma is None:
            raise ValueError("sigma is required for likelihood costs")
        overlap = set(self.fixed_values) & set(self.names)
        if overlap:
            raise ValueError(f"parameters both fixed and fitted: {sorted(overlap)}")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FitSpec":
        params = [
            FitParameter(
                name=p["name"],
                initial_value=float(p["initial_value"]),
                bounds=(float(p["bounds"][0]), float(p["bounds"][1])),
            )
            for p in raw.pop("fit_parameters", [])
        ]
        spec = cls(fit_parameters=params, **raw)
        spec.validate()
        return spec

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.fit_parameters]

    @property
    def all_names(self) -> list[str]:
        return self.names + sorted(self.fixed_values)

    @property
    def initial_values(self) -> list[float]:
        return [p.initial_value for p in self.fit_parameters]

    @property
    def bounds_array(self) -> np.ndarray:
        return np.array([p.bounds for p in self.fit_parameters], dtype=float)


def _build_model(model_name: str) -> pybamm.BaseModel:
    return getattr(pybamm.lithium_ion, model_name)()


def _make_cost(spec: FitSpec, dataset: pybop.Dataset):
    if spec.cost == "SumSquaredError":
        return pybop.SumSquaredError(dataset)
    if spec.cost == "GaussianLogLikelihood":
        return pybop.GaussianLogLikelihood(dataset, sigma=spec.sigma)
    return pybop.GaussianLogLikelihoodKnownSigma(dataset, sigma=spec.sigma)


def build_single_problem(dataset: pybop.Dataset, spec: FitSpec) -> pybop.Problem:
    """Build one pybop.Problem for one dataset."""
    spec.validate()
    model = _build_model(spec.model_name)
    pv = pybamm.ParameterValues(spec.parameter_set)
    for name, value in spec.fixed_values.items():
        if name not in pv.keys():
            raise KeyError(f"fixed parameter '{name}' is not a parameter of {spec.parameter_set}")
        pv.update({name: float(value)})
    for p in spec.fit_parameters:
        if p.name not in pv.keys():
            raise KeyError(f"{p.name} is not a parameter of {spec.parameter_set}")
        pv.update(
            {
                p.name: pybop.Parameter(
                    bounds=p.bounds, initial_value=p.initial_value
                )
            }
        )
    simulator = pybop.pybamm.Simulator(
        model,
        parameter_values=pv,
        protocol=dataset,
        solver=pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6),
    )
    return pybop.Problem(simulator, _make_cost(spec, dataset))


def build_problem(
    datasets: list, spec: FitSpec
) -> tuple[Any, dict[str, Any]]:
    """Build a Problem (single condition) or MetaProblem (multi-condition).

    ``datasets`` items may be (name, dataset) or (name, dataset, metadata)
    tuples as returned by synthetic.generate_datasets.

    Returns (problem, build_info).
    """
    items = [(item[0], item[1]) for item in datasets]
    problems = [build_single_problem(ds, spec) for _, ds in items]
    if len(problems) == 1:
        return problems[0], {"kind": "Problem", "conditions": [c for c, _ in items]}
    return (
        pybop.MetaProblem(*problems),
        {"kind": "MetaProblem", "conditions": [c for c, _ in items]},
    )


def run_fit_with_result(
    problem: Any,
    spec: FitSpec,
    *,
    truth: dict[str, float] | None = None,
    initial_values: list[float] | None = None,
) -> tuple[dict[str, Any], Any]:
    """Run the configured PyBOP optimiser.

    Returns (report, optimisation_result). The raw result is kept for
    diagnostics that need the live object (e.g. pybop.classify_using_hessian).
    """
    spec.validate()
    x0 = np.asarray(initial_values if initial_values is not None else spec.initial_values,
                    dtype=float)
    for p, xv in zip(spec.fit_parameters, x0):
        if not p.bounds[0] <= xv <= p.bounds[1]:
            raise ValueError(f"initial value {xv} for {p.name} outside bounds")

    # Multi-start support: update the optimiser start point via the public
    # Parameter.update_initial_value API (Parameters.set requires a Parameter
    # object; verified against pybop 26.10 source).
    for p, xv in zip(spec.fit_parameters, x0):
        problem.parameters.get(p.name).update_initial_value(float(xv))

    options = pybop.SciPyMinimizeOptions(
        method=spec.method, maxiter=spec.maxiter, jac=spec.jac
    )
    optimiser = pybop.SciPyMinimize(problem, options=options)
    t0 = time.perf_counter()
    result = optimiser.run()
    runtime = time.perf_counter() - t0

    x = np.asarray(result.x, dtype=float)
    report: dict[str, Any] = {
        "fit_spec": {
            "parameter_set": spec.parameter_set,
            "model_name": spec.model_name,
            "cost": spec.cost,
            "sigma": spec.sigma,
            "optimizer": {"method": spec.method, "maxiter": spec.maxiter, "jac": spec.jac},
            "fixed_values": dict(spec.fixed_values),
            "description": spec.description,
        },
        "parameters": [
            {
                "name": p.name,
                "initial_value": float(xv),
                "bounds": [float(p.bounds[0]), float(p.bounds[1])],
                "estimate": float(xe),
            }
            for p, xv, xe in zip(spec.fit_parameters, x0, x)
        ],
        "runtime_s": float(runtime),
        "final_cost": float(result.best_cost),
        "message": str(result.message),
        # API finding: Result.total_evaluations is a method in pybop 26.10
        "n_evaluations": (
            int(result.total_evaluations())
            if callable(getattr(result, "total_evaluations", None))
            else int(getattr(result, "total_evaluations", -1) or -1)
        ),
    }
    if truth:
        errors = {}
        for p, xe in zip(spec.fit_parameters, x):
            tv = float(truth[p.name])
            errors[p.name] = {
                "truth": tv,
                "estimate": float(xe),
                "abs_error": float(abs(xe - tv)),
                "rel_error_pct": float(abs(xe - tv) / abs(tv) * 100.0) if tv != 0 else None,
            }
        report["recovery"] = errors
    return report, result


def run_fit(
    problem: Any,
    spec: FitSpec,
    *,
    truth: dict[str, float] | None = None,
    initial_values: list[float] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper returning only the report dict."""
    report, _ = run_fit_with_result(problem, spec, truth=truth, initial_values=initial_values)
    return report
