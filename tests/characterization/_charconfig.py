"""Shared reduced-size configurations for characterization tests.

Every literal here is duplicated in ``tests/baselines/generate_baselines.py``
(imported from there) so the generator and the tests run byte-identical
pipelines. Characterization baselines live in ``tests/baselines/`` and were
generated from the pre-audit code; they are the numerics gate for the audit
sprint: a change that drifts past these tolerances must never merge silently.

Tolerances (rationale):
- npz arrays: np.allclose(rtol=1e-12, atol=1e-12, equal_nan=True) plus exact
  shape equality. The engine was verified bit-identical across repeated runs
  on one machine; 1e-12 still catches any accidental threshold/seed/loop
  change while surviving trivial retracing noise.
- optimiser outputs: estimates atol=1e-4 (parameters are O(0.1-1) volume
  fractions), final_cost rtol=1e-5, element count/ids exactly equal.
  L-BFGS-B downgrade/termination messages and evaluation counts are compared
  exactly (same machine, same venv).
"""

from __future__ import annotations

import copy

CHAR_P2_SINGLE: dict = {
    "run_id": "char_recovery_single",
    "description": "characterization: reduced single-condition recovery probe",
    "model_name": "DFN",
    "parameter_set": "Chen2020",
    "true_values": {
        "Negative electrode active material volume fraction": 0.75,
        "Positive electrode active material volume fraction": 0.665,
    },
    "fit_parameters": [
        {
            "name": "Negative electrode active material volume fraction",
            "initial_value": 0.62,
            "bounds": [0.55, 0.90],
        },
        {
            "name": "Positive electrode active material volume fraction",
            "initial_value": 0.55,
            "bounds": [0.45, 0.80],
        },
    ],
    "multi_start": [[0.62, 0.55]],
    "conditions": [{"name": "1C", "steps": ["Discharge at 1C for 300 s"]}],
    "noise_sigma_V": 0.002,
    "seed": 20261104,
    "cost": "SumSquaredError",
    "optimizer": {"method": "L-BFGS-B", "maxiter": 10, "jac": True},
}

CHAR_P2_MULTI: dict = {
    "run_id": "char_recovery_multi",
    "description": "characterization: reduced multi-condition MetaProblem probe",
    "model_name": "DFN",
    "parameter_set": "Chen2020",
    "true_values": {
        "Negative electrode active material volume fraction": 0.75,
        "Positive electrode active material volume fraction": 0.665,
    },
    "fit_parameters": CHAR_P2_SINGLE["fit_parameters"],
    "multi_start": [[0.62, 0.55], [0.70, 0.75]],
    "conditions": [
        {"name": "0.5C", "steps": ["Discharge at 0.5C for 600 s"]},
        {"name": "1C", "steps": ["Discharge at 1C for 300 s"]},
    ],
    "noise_sigma_V": 0.002,
    "seed": 20261104,
    "cost": "SumSquaredError",
    "optimizer": {"method": "L-BFGS-B", "maxiter": 8, "jac": True},
}

CHAR_BASELINE_DICT: dict = {
    "run_id": "char_baseline_120s",
    "description": "characterization: short deterministic DFN run (audit sprint)",
    "pybamm": {
        "required_version": "26.8.0.0",
        "model": {"family": "lithium_ion", "name": "DFN", "options": {}},
        "parameter_set": "Chen2020",
        "solver": {"name": "idaklu", "rtol": 1e-6, "atol": 1e-6},
    },
    "experiment": {"steps": ["Discharge at 1C for 120 s"]},
    "outputs": {
        "series": [
            "Time [s]",
            "Terminal voltage [V]",
            "Current [A]",
            "Discharge capacity [A.h]",
        ],
        "profile_variables": [
            "Electrolyte concentration [mol.m-3]",
            "Negative particle concentration [mol.m-3]",
        ],
        "profile_time_fractions": [0.5],
    },
    "reproducibility": {
        "seed": None,
        "seed_note": "deterministic DAE solve; no stochastic component",
    },
}


def deep_copy(raw: dict) -> dict:
    return copy.deepcopy(raw)
