"""Reproducibility manifest: everything needed to repeat and audit a run."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Any

from pybamm_closed_loop.pybamm_engine.config import BaselineRunConfig


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in ("pybamm", "numpy", "scipy", "pandas", "casadi", "pybammsolvers", "pydantic"):
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[pkg] = "not installed"
    return versions


def parameter_snapshot(parameter_values) -> dict[str, Any]:
    """JSON-safe snapshot of a PyBaMM ParameterValues object.

    Callables are recorded by name only - the snapshot documents what was used,
    it never fabricates numerical values for function-based parameters.
    """
    snapshot: dict[str, Any] = {}
    for key in parameter_values.keys():
        value = parameter_values[key]
        if callable(value):
            snapshot[key] = f"<callable:{getattr(value, '__name__', type(value).__name__)}>"
        elif isinstance(value, (int, float, bool, str)) or value is None:
            snapshot[key] = value
        elif isinstance(value, dict):
            snapshot[key] = {str(k): (v if isinstance(v, (int, float, bool, str)) or v is None else str(v)) for k, v in value.items()}
        else:
            snapshot[key] = f"<{type(value).__name__}>"
    return snapshot


def build_manifest(
    config: BaselineRunConfig,
    *,
    parameter_values,
    model,
    solution,
    extraction_availability: dict[str, Any],
    parameter_set_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the run manifest (JSON-serialisable)."""
    import pybamm

    termination = getattr(solution, "termination", "unknown")
    t = solution.t
    manifest: dict[str, Any] = {
        "run_id": config.run_id,
        "description": config.description,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": _package_versions(),
        },
        "pybamm": {
            "installed_version": pybamm.__version__,
            "required_version": config.pybamm.required_version,
            "model_family": config.pybamm.model.family,
            "model_name": config.pybamm.model.name,
            "model_full_name": model.name,
            "options_requested": config.pybamm.model.options,
            "options_effective": dict(model.options),
            "solver": {
                "name": config.pybamm.solver.name,
                "rtol": config.pybamm.solver.rtol,
                "atol": config.pybamm.solver.atol,
                "class": type(solution.solver).__name__ if getattr(solution, "solver", None) is not None else "unknown",
            },
            "parameter_set": {
                "name": config.pybamm.parameter_set,
                **parameter_set_metadata,
                "n_entries": len(list(parameter_values.keys())),
            },
        },
        "experiment": {
            "steps": list(config.experiment.steps),
            "description": config.experiment.description,
        },
        "reproducibility": {
            "seed": config.reproducibility.seed,
            "seed_note": config.reproducibility.seed_note,
        },
        "solution_summary": {
            "termination": str(termination),
            "t_start_s": float(t[0]),
            "t_end_s": float(t[-1]),
            "n_steps": int(len(t)),
        },
        "extraction": extraction_availability,
    }
    return manifest
