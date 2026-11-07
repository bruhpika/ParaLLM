"""Characterization tests, P2 recovery path (gate: .venv-ecosystem312).

Runs reduced-size PyBOP synthetic-recovery pipelines through the real
benchmark module and compares optimiser outputs against committed baselines.

Tolerances (rationale in _charconfig.py):
- parameter estimates: atol=1e-4 (parameters are O(0.1-1) volume fractions);
- final_cost: rel 1e-5;
- cost_convergence: rel 1e-4 per element, same length required;
- message / n_evaluations / start index: exact.

Skip logic matches the repo convention: these tests need pybop and are
skipped automatically in venvs without it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

yaml = pytest.importorskip("yaml")
pytest.importorskip("pybamm")
pybop = pytest.importorskip("pybop")

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parents[1] / "baselines"
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

import benchmarks.parameter_recovery.run_recovery_benchmark as bench  # noqa: E402

from tests.characterization._charconfig import CHAR_P2_MULTI, CHAR_P2_SINGLE  # noqa: E402


def _run_benchmark(raw_config: dict, tmp_path: Path) -> tuple[dict, dict]:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(raw_config), encoding="utf-8")
    out_dir = tmp_path / "out"
    old_argv = sys.argv
    sys.argv = ["prog", "--config", str(cfg_path), "--out", str(out_dir)]
    try:
        bench.main()
    finally:
        sys.argv = old_argv
    report = json.loads(
        (out_dir / raw_config["run_id"] / "report.json").read_text()
    )
    return report, out_dir / raw_config["run_id"] / "report.json"


def _assert_runs_match(expected_runs, actual_runs):
    assert len(expected_runs) == len(actual_runs)
    for e, a in zip(expected_runs, actual_runs):
        assert a["start_index"] == e["start_index"]
        for pe, pa in zip(e["parameters"], a["parameters"]):
            assert pa["name"] == pe["name"]
            assert pa["estimate"] == pytest.approx(pe["estimate"], abs=1e-4)
            assert pa["initial_value"] == pytest.approx(pe["initial_value"], abs=1e-12)
        assert a["final_cost"] == pytest.approx(e["final_cost"], rel=1e-5)
        assert a["n_evaluations"] == e["n_evaluations"]
        assert a["message"] == e["message"]
        e_cc, a_cc = e["cost_convergence"], a["cost_convergence"]
        assert len(e_cc) == len(a_cc), "cost_convergence length drifted"
        for x, y in zip(e_cc, a_cc):
            assert y == pytest.approx(x, rel=1e-4)


def test_recovery_single_matches_baseline(tmp_path):
    report, _ = _run_benchmark(CHAR_P2_SINGLE, tmp_path)
    expected = json.loads((BASE_DIR / "char_recovery_single.json").read_text())

    assert report["best_run_index"] == expected["best_run_index"]
    _assert_runs_match(expected["runs"], report["runs"])
    for e_meta, a_meta in zip(expected["generated_data"], report["generated_data"]):
        assert a_meta["condition"] == e_meta["condition"]
        assert a_meta["n_points"] == e_meta["n_points"]
        assert a_meta["t_end_s"] == pytest.approx(e_meta["t_end_s"], rel=1e-12)
        assert a_meta["seed"] == e_meta["seed"]
    assert report["build_info"] == expected["build_info"]


def test_recovery_multi_matches_baseline(tmp_path):
    report, _ = _run_benchmark(CHAR_P2_MULTI, tmp_path)
    expected = json.loads((BASE_DIR / "char_recovery_multi.json").read_text())

    assert report["best_run_index"] == expected["best_run_index"]
    _assert_runs_match(expected["runs"], report["runs"])


def test_noise_generation_is_seed_deterministic():
    """Same seed twice -> identical observation arrays (guards RNG regressions)."""
    from pybamm_closed_loop.calibration.synthetic import (
        SyntheticCondition,
        SyntheticSpec,
        generate_datasets,
    )

    def spec() -> SyntheticSpec:
        return SyntheticSpec(
            parameter_set="Chen2020",
            model_name="DFN",
            true_values={
                "Negative electrode active material volume fraction": 0.75,
                "Positive electrode active material volume fraction": 0.665,
            },
            conditions=[SyntheticCondition(name="1C", steps=["Discharge at 1C for 120 s"])],
            noise_sigma_V=0.002,
            seed=20261104,
        )

    first = generate_datasets(spec())
    second = generate_datasets(spec())
    v1 = np.asarray(first[0][1]["Voltage [V]"])
    v2 = np.asarray(second[0][1]["Voltage [V]"])
    assert (v1 == v2).all()
