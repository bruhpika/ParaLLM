"""Synthetic observation generation with recorded ground truth.

Generates observations from a known parameter set via PyBaMM, adds controlled
noise via pybop.add_noise under an explicit numpy seed, and returns
pybop.Dataset objects ready for fitting. Ground truth is always carried
alongside the data - synthetic recovery is a method check, never experimental
validation (scientific rule 8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pybamm
import pybop

# Parameters whose value is estimated; names must match PyBaMM keys exactly.


@dataclass
class SyntheticCondition:
    """One operating condition, expressed as PyBaMM experiment steps.

    Only fixed-duration steps are allowed for fitting workflows: PyBOP removes
    voltage events, so event-terminated ('until ... V') protocols would change
    meaning between generation and fitting.
    """

    name: str
    steps: list[str]

    def validate(self) -> None:
        if not self.steps:
            raise ValueError(f"condition '{self.name}' has no steps")
        for step in self.steps:
            if " until " in step.lower():
                raise ValueError(
                    f"condition '{self.name}': event-terminated step {step!r} is "
                    "not allowed for fitting workflows (use fixed-duration steps)"
                )


@dataclass
class SyntheticSpec:
    """Configuration of a synthetic recovery experiment."""

    parameter_set: str
    model_name: str
    true_values: dict[str, float]
    conditions: list[SyntheticCondition]
    noise_sigma_V: float
    seed: int
    description: str = ""

    def validate(self) -> None:
        if not self.true_values:
            raise ValueError("true_values must not be empty")
        if not self.conditions:
            raise ValueError("at least one condition is required")
        if self.noise_sigma_V < 0:
            raise ValueError("noise_sigma_V must be >= 0")
        for cond in self.conditions:
            cond.validate()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SyntheticSpec":
        conditions = [SyntheticCondition(**c) for c in raw.pop("conditions", [])]
        spec = cls(conditions=conditions, **raw)
        spec.validate()
        return spec


def _build_model(model_name: str) -> pybamm.BaseModel:
    return getattr(pybamm.lithium_ion, model_name)()


def _true_parameter_values(spec: SyntheticSpec) -> pybamm.ParameterValues:
    """ParameterValues with ground-truth overrides applied as plain floats."""
    pv = pybamm.ParameterValues(spec.parameter_set)
    for name, value in spec.true_values.items():
        if name not in pv.keys():
            raise KeyError(
                f"true_values key '{name}' is not a parameter of {spec.parameter_set}"
            )
        pv.update({name: float(value)})
    return pv


def generate_dataset(
    spec: SyntheticSpec, condition: SyntheticCondition
) -> tuple[pybop.Dataset, dict[str, Any]]:
    """Generate one noisy observation set from the ground-truth model.

    Returns (dataset, metadata) where metadata records truth, noise and seed.
    """
    spec.validate()
    model = _build_model(spec.model_name)
    pv = _true_parameter_values(spec)
    experiment = pybamm.Experiment(list(condition.steps))
    solution = pybamm.Simulation(model, parameter_values=pv, experiment=experiment).solve()
    t = np.asarray(solution.t, dtype=float)

    np.random.seed(spec.seed)  # reproducible noise; recorded in metadata
    voltage_clean = np.asarray(solution["Terminal voltage [V]"](t), dtype=float)
    current = np.asarray(solution["Current [A]"](t), dtype=float)
    voltage_noisy = pybop.add_noise(voltage_clean, spec.noise_sigma_V)

    dataset = pybop.Dataset(
        {"Time [s]": t, "Current [A]": current, "Voltage [V]": np.asarray(voltage_noisy)}
    )
    metadata = {
        "condition": condition.name,
        "steps": list(condition.steps),
        "true_values": dict(spec.true_values),
        "noise_sigma_V": spec.noise_sigma_V,
        "seed": spec.seed,
        "n_points": int(t.size),
        "t_end_s": float(t[-1]),
        "voltage_clean_range_V": [float(voltage_clean.min()), float(voltage_clean.max())],
    }
    return dataset, metadata


def generate_datasets(
    spec: SyntheticSpec,
) -> list[tuple[str, pybop.Dataset, dict[str, Any]]]:
    """Generate one dataset per condition (same seed each: deterministic)."""
    return [
        (cond.name, *generate_dataset(spec, cond)) for cond in spec.conditions
    ]
