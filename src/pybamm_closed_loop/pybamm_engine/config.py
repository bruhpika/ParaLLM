"""Typed configuration models for reproducible PyBaMM baseline runs.

Configuration is the single source of truth for a simulation run: model,
parameter set, solver settings, experiment and requested outputs. Everything
needed to reproduce a run is serialised into the run manifest.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VersionMismatchError(RuntimeError):
    """Raised when the installed PyBaMM version differs from the pinned one."""


class ModelConfig(BaseModel):
    """PyBaMM model selection. Only verified names are accepted."""

    model_config = ConfigDict(extra="forbid")

    family: Literal["lithium_ion"] = "lithium_ion"
    name: Literal["DFN", "SPMe", "SPM"] = "DFN"
    options: dict[str, str] = Field(default_factory=dict)


class SolverConfig(BaseModel):
    """Numerical solver settings. ``idaklu`` is the recommended solver in PyBaMM 26.8."""

    model_config = ConfigDict(extra="forbid")

    name: Literal["idaklu", "casadi", "scipy"] = "idaklu"
    rtol: float = 1e-6
    atol: float = 1e-6


class PyBaMMConfig(BaseModel):
    """Pinned PyBaMM environment and model configuration."""

    model_config = ConfigDict(extra="forbid")

    required_version: str
    model: ModelConfig = Field(default_factory=ModelConfig)
    parameter_set: str
    solver: SolverConfig = Field(default_factory=SolverConfig)


class ExperimentConfig(BaseModel):
    """Operating condition, expressed with PyBaMM experiment step strings.

    Step strings are parsed by PyBaMM itself; this project never re-implements
    their syntax. They are validated at simulation build time.
    """

    model_config = ConfigDict(extra="forbid")

    steps: list[str]
    description: str = ""

    @field_validator("steps")
    @classmethod
    def _steps_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("experiment.steps must contain at least one step")
        if any(not s.strip() for s in v):
            raise ValueError("experiment.steps must not contain empty strings")
        return v


class OutputsConfig(BaseModel):
    """Requested output variables. Unavailable variables are reported, never invented."""

    model_config = ConfigDict(extra="forbid")

    series: list[str]
    profile_variables: list[str] = Field(default_factory=list)
    profile_time_fractions: list[float] = Field(default_factory=lambda: [0.1, 0.5, 0.9])

    @field_validator("profile_time_fractions")
    @classmethod
    def _fractions_in_range(cls, v: list[float]) -> list[float]:
        for f in v:
            if not 0.0 < f < 1.0:
                raise ValueError(
                    "profile_time_fractions must lie strictly between 0 and 1"
                )
        return v


class ReproducibilityConfig(BaseModel):
    """Randomness control. P0 has none; the field exists so later phases inherit it."""

    model_config = ConfigDict(extra="forbid")

    seed: int | None = None
    seed_note: str = ""


class BaselineRunConfig(BaseModel):
    """Complete configuration of one baseline run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    description: str = ""
    pybamm: PyBaMMConfig
    experiment: ExperimentConfig
    outputs: OutputsConfig
    reproducibility: ReproducibilityConfig = Field(default_factory=ReproducibilityConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BaselineRunConfig":
        with open(path, "r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        return cls.model_validate(raw)

    def check_pybamm_version(self) -> None:
        """Fail loudly on PyBaMM version drift (names and options change between versions)."""
        import pybamm

        if pybamm.__version__ != self.pybamm.required_version:
            raise VersionMismatchError(
                f"config pins pybamm=={self.pybamm.required_version} but "
                f"{pybamm.__version__} is installed"
            )
