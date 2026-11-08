"""Agent A regression tests for the diffusivity feasibility benchmark.

The module is P2-study code that calls PyBaMM directly; these tests only
exercise configuration guards, never the numerical study itself.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("pybamm")

BENCH = Path(__file__).resolve().parents[2] / "benchmarks/identifiability/diffusivity_feasibility.py"


def load_module():
    spec = importlib.util.spec_from_file_location("diffusivity_feasibility_agentA", BENCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BASE_CONFIG = {
    "run_id": "guard_test",
    "model_name": "DFN",
    "parameter_set": "Chen2020",
    "rel_perturbation": 0.02,
    "conditions": [{"name": "1C", "steps": ["Discharge at 1C for 60 s"]}],
    "study_parameters": [
        {"name": "Negative particle diffusivity [m2.s-1]", "kind": "scalar"},
    ],
}


def test_guard_rejects_zero_rel_perturbation(tmp_path, monkeypatch, capsys):
    """rel=0 divides 0 by 0 in the finite-difference code -> NaN report -> invalid JSON."""
    mod = load_module()
    cfg = {**BASE_CONFIG, "rel_perturbation": 0.0}
    path = tmp_path / "cfg.yaml"
    path.write_text(json.dumps(cfg))
    monkeypatch.setattr(sys, "argv", ["dff", "--config", str(path), "--out", str(tmp_path)])
    with pytest.raises(ValueError, match="rel_perturbation"):
        mod.main()


def test_guard_rejects_nonfinite_rel_perturbation(tmp_path, monkeypatch):
    mod = load_module()
    cfg = {**BASE_CONFIG, "rel_perturbation": "inf"}
    path = tmp_path / "cfg.yaml"
    path.write_text(json.dumps(cfg))
    monkeypatch.setattr(sys, "argv", ["dff", "--config", str(path), "--out", str(tmp_path)])
    with pytest.raises(ValueError, match="rel_perturbation"):
        mod.main()


def test_no_out_dir_created_on_guard_failure(tmp_path, monkeypatch):
    """The guard fires before any simulation state is created."""
    mod = load_module()
    cfg = {**BASE_CONFIG, "rel_perturbation": 0.0}
    path = tmp_path / "cfg.yaml"
    path.write_text(json.dumps(cfg))
    monkeypatch.setattr(sys, "argv", ["dff", "--config", str(path), "--out", str(tmp_path)])
    with pytest.raises(ValueError):
        mod.main()
    # the guard fires before any artifact directory is created
    assert not (tmp_path / "guard_test").exists()
