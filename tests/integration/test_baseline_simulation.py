"""Integration tests: real PyBaMM build + short simulations (see configs/baseline_dfn.yaml).

These are software-correctness tests. Scientific performance lives in benchmarks/.
A short 120 s discharge is used so the suite stays fast; the full baseline run is
produced by scripts/run_baseline.py.
"""

import copy

import numpy as np
import pytest

from pybamm_closed_loop.pybamm_engine import (
    BaselineRunConfig,
    build_model,
    build_parameter_values,
    build_simulation,
    build_solver,
    run,
)

pytestmark = pytest.mark.integration

BASE = {
    "run_id": "test_short_run",
    "description": "short deterministic run for tests",
    "pybamm": {
        "required_version": "26.8.0.0",
        "model": {"family": "lithium_ion", "name": "DFN", "options": {}},
        "parameter_set": "Chen2020",
        "solver": {"name": "idaklu", "rtol": 1e-6, "atol": 1e-6},
    },
    "experiment": {"steps": ["Discharge at 1C for 120 s"]},
    "outputs": {
        "series": [
            "Terminal voltage [V]",
            "Current [A]",
            "Discharge capacity [A.h]",
            "Not a real variable [V]",
        ],
        "profile_variables": [
            "Electrolyte concentration [mol.m-3]",
            "Not a real profile [V]",
        ],
        "profile_time_fractions": [0.5],
    },
    "reproducibility": {
        "seed": None,
        "seed_note": "deterministic DAE solve; no stochastic component",
    },
}


def make_config(**overrides):
    raw = copy.deepcopy(BASE)
    for key, value in overrides.items():
        raw[key] = value
    return BaselineRunConfig.model_validate(raw)


@pytest.fixture(scope="module")
def short_run():
    return run(make_config())


def test_model_initialization():
    model = build_model(make_config())
    assert model.name == "Doyle-Fuller-Newman model"
    assert "Terminal voltage [V]" in model.variable_names()


def test_model_options_merge_with_defaults():
    model = build_model(make_config())
    # options_effective must be the installed defaults (config requests none explicitly)
    assert model.options["particle shape"] == "spherical"
    assert model.options["thermal"] == "isothermal"


def test_parameter_loading_matches_documented_chen2020_values():
    pv = build_parameter_values(make_config())
    # Values below are the documented Chen2020 (LG M50) parameters.
    assert pv["Electrode height [m]"] == pytest.approx(0.065)
    assert pv["Nominal cell capacity [A.h]"] == pytest.approx(5.0)
    assert pv["Initial concentration in negative electrode [mol.m-3]"] == pytest.approx(29866.0)
    assert pv["Initial concentration in positive electrode [mol.m-3]"] == pytest.approx(17038.0)
    assert pv["Lower voltage cut-off [V]"] == pytest.approx(2.5)
    assert pv["Upper voltage cut-off [V]"] == pytest.approx(4.2)


def test_unknown_parameter_set_rejected():
    from pybamm_closed_loop.pybamm_engine.engine import UnknownParameterSetError

    cfg = make_config()
    cfg.pybamm.parameter_set = "DefinitelyNotAParameterSet"
    with pytest.raises(UnknownParameterSetError):
        build_parameter_values(cfg)


def test_simulation_completes(short_run):
    summary = short_run.manifest["solution_summary"]
    assert summary["t_end_s"] > 0
    assert "event" in summary["termination"] or "success" in summary["termination"].lower() or "final time" in summary["termination"].lower()


def test_output_extraction(short_run):
    ex = short_run.extraction
    assert "Terminal voltage [V]" in ex.series
    assert "Current [A]" in ex.series
    v = ex.series["Terminal voltage [V]"]
    t = ex.series["Time [s]"]
    assert v.shape == t.shape
    assert np.all(np.isfinite(v))
    # Voltage must fall monotonically during galvanostatic discharge (up to solver noise)
    assert v[-1] < v[0]
    #1C of a 5 A.h cell is 5 A
    assert np.allclose(ex.series["Current [A]"], 5.0)


def test_unavailable_variables_reported_not_fabricated(short_run):
    ex = short_run.extraction
    assert "Not a real variable [V]" in ex.unavailable_series
    assert "Not a real variable [V]" not in ex.series
    assert "Not a real profile [V]" in ex.unavailable_profiles
    assert "Electrolyte concentration [mol.m-3]" in ex.profiles


def test_profile_extraction_shapes(short_run):
    prof = short_run.extraction.profiles["Electrolyte concentration [mol.m-3]"]
    assert prof.values.shape == (1, len(prof.coordinates))
    assert np.all(np.isfinite(prof.values))
    assert prof.coordinate_name == "x [m]"


def test_manifest_reproducibility_fields(short_run):
    manifest = short_run.manifest
    assert manifest["run_id"] == "test_short_run"
    assert manifest["pybamm"]["installed_version"] == "26.8.0.0"
    assert manifest["pybamm"]["required_version"] == "26.8.0.0"
    assert manifest["pybamm"]["parameter_set"]["name"] == "Chen2020"
    assert manifest["pybamm"]["solver"]["name"] == "idaklu"
    assert manifest["experiment"]["steps"] == ["Discharge at 1C for 120 s"]
    assert manifest["reproducibility"]["seed"] is None
    assert manifest["environment"]["packages"]["pybamm"] == "26.8.0.0"
    assert manifest["extraction"]["series_unavailable"] == ["Not a real variable [V]"]


def test_repeated_run_is_identical(short_run):
    """Deterministic solver: identical config must give identical trajectories."""
    second = run(make_config())
    v1 = short_run.extraction.series["Terminal voltage [V]"]
    v2 = second.extraction.series["Terminal voltage [V]"]
    assert v1.shape == v2.shape
    assert np.array_equal(v1, v2)

    m1 = copy.deepcopy(short_run.manifest)
    m2 = copy.deepcopy(second.manifest)
    m1.pop("timestamp_utc")
    m2.pop("timestamp_utc")
    assert m1 == m2
