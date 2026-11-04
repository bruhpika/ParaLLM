"""Unit tests for run configuration (no PyBaMM simulation involved)."""

import pytest

from pybamm_closed_loop.pybamm_engine.config import (
    BaselineRunConfig,
    VersionMismatchError,
)


MINIMAL = {
    "run_id": "test_run",
    "pybamm": {
        "required_version": "26.8.0.0",
        "model": {"family": "lithium_ion", "name": "DFN", "options": {}},
        "parameter_set": "Chen2020",
        "solver": {"name": "idaklu", "rtol": 1e-6, "atol": 1e-6},
    },
    "experiment": {"steps": ["Discharge at 1C until 2.5 V"]},
    "outputs": {
        "series": ["Terminal voltage [V]"],
        "profile_variables": [],
        "profile_time_fractions": [0.5],
    },
    "reproducibility": {"seed": None, "seed_note": "deterministic"},
}


def make_config(overrides=None):
    import copy

    raw = copy.deepcopy(MINIMAL)
    if overrides:
        for key, value in overrides.items():
            raw[key] = value
    return BaselineRunConfig.model_validate(raw)


def test_config_loads_and_defaults():
    cfg = make_config()
    assert cfg.run_id == "test_run"
    assert cfg.pybamm.solver.name == "idaklu"
    assert cfg.reproducibility.seed is None
    assert cfg.experiment.description == ""


def test_config_from_yaml_roundtrip(tmp_path):
    import yaml

    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(MINIMAL))
    cfg = BaselineRunConfig.from_yaml(path)
    assert cfg.model_dump() == make_config().model_dump()


def test_rejects_empty_experiment_steps():
    with pytest.raises(Exception):
        make_config({"experiment": {"steps": []}})


def test_rejects_unknown_solver_name():
    with pytest.raises(Exception):
        make_config(
            {
                "pybamm": {
                    **MINIMAL["pybamm"],
                    "solver": {"name": "magic", "rtol": 1e-6, "atol": 1e-6},
                }
            }
        )


def test_rejects_invalid_profile_fraction():
    with pytest.raises(Exception):
        make_config(
            {
                "outputs": {
                    "series": ["Terminal voltage [V]"],
                    "profile_variables": [],
                    "profile_time_fractions": [0.0, 1.5],
                }
            }
        )


def test_rejects_unknown_model_name():
    with pytest.raises(Exception):
        make_config(
            {
                "pybamm": {
                    **MINIMAL["pybamm"],
                    "model": {"family": "lithium_ion", "name": "NotAModel", "options": {}},
                }
            }
        )


def test_rejects_extra_fields():
    with pytest.raises(Exception):
        make_config({"bogus_field": 1})


def test_version_pin_enforced():
    cfg = make_config(
        {"pybamm": {**MINIMAL["pybamm"], "required_version": "0.0.0-not-installed"}}
    )
    with pytest.raises(VersionMismatchError):
        cfg.check_pybamm_version()


def test_version_pin_accepts_matching_version():
    cfg = make_config()
    cfg.check_pybamm_version()  # must not raise on the pinned version
