"""Calibration adapters over PyBOP/PyBaMM (no custom optimizers or solvers).

Modules:
- synthetic: ground-truthed synthetic observation generation (P2 benchmarks)
- fitting: PyBOP problem construction and bounded fitting orchestration
- identifiability: diagnostics complementary to PyBOP (FIM, profiles,
  bootstrap, Sobol) plus wrappers for PyBOP's Hessian classification

Submodules are imported lazily so that the pure-numpy identifiability module
stays usable in environments without pybop installed (e.g. the P0 venv).

Provenance rule: every fitting request must carry parameter names, bounds,
initial values, noise settings and seeds; reports echo the full config.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "FitParameter",
    "FitSpec",
    "SyntheticCondition",
    "SyntheticSpec",
    "build_problem",
    "generate_datasets",
    "run_fit",
    "run_fit_with_result",
]


def __getattr__(name: str) -> Any:
    if name in ("SyntheticCondition", "SyntheticSpec", "generate_datasets"):
        from pybamm_closed_loop.calibration import synthetic

        return getattr(synthetic, name)
    if name in ("FitParameter", "FitSpec", "build_problem", "run_fit",
                "run_fit_with_result"):
        from pybamm_closed_loop.calibration import fitting

        return getattr(fitting, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
