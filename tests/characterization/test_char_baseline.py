"""Characterization tests, P0 baseline path (gate: .venv, CPython 3.14).

Two gates:
1. in-process engine run (build → solve → extract) vs committed baseline;
2. full CLI entry point scripts/run_baseline.py via subprocess vs the same
   baseline (covers config YAML → CLI → engine → save_result end to end).

Tolerances: np.allclose(rtol=1e-12, atol=1e-12, equal_nan=True) with exact
shape equality; manifest scientific fields compared as ints/floats
(pytest.approx rel 1e-12). Rationale documented in _charconfig.py and
tests/baselines/generate_baselines.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parents[1] / "baselines"

pytestmark = pytest.mark.integration


def _load_npz(path: Path) -> dict:
    data = np.load(path)
    return {k: data[k] for k in data.files}


@pytest.fixture(scope="module")
def inprocess_npz():
    from pybamm_closed_loop.pybamm_engine import BaselineRunConfig, run, save_result
    from tests.characterization._charconfig import CHAR_BASELINE_DICT

    config = BaselineRunConfig.model_validate(CHAR_BASELINE_DICT)
    result = run(config)
    with __import__("tempfile").TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        save_result(result, out_dir)
        yield _load_npz(out_dir / "solution_arrays.npz")


def test_p0_series_match_baseline(inprocess_npz):
    expected = _load_npz(BASE_DIR / "char_baseline_120s.npz")
    assert set(expected) == set(inprocess_npz), "baseline key set drifted"
    for key, arr in expected.items():
        actual = inprocess_npz[key]
        assert actual.shape == arr.shape, f"{key}: shape {actual.shape} != {arr.shape}"
        assert np.allclose(
            actual, arr, rtol=1e-12, atol=1e-12, equal_nan=True
        ), f"{key}: arrays drifted beyond rtol=atol=1e-12"


def test_p0_manifest_science_fields_match_baseline():
    from pybamm_closed_loop.pybamm_engine import BaselineRunConfig, run
    from tests.characterization._charconfig import CHAR_BASELINE_DICT

    expected = json.loads((BASE_DIR / "char_baseline_manifest.json").read_text())
    config = BaselineRunConfig.model_validate(CHAR_BASELINE_DICT)
    result = run(config)
    manifest = result.manifest

    assert manifest["solution_summary"]["termination"] == expected["solution_summary"]["termination"]
    assert manifest["solution_summary"]["t_end_s"] == pytest.approx(
        expected["solution_summary"]["t_end_s"], rel=1e-12
    )
    assert manifest["solution_summary"]["n_steps"] == expected["solution_summary"]["n_steps"]
    assert manifest["extraction"] == expected["extraction"]


def test_p0_cli_end_to_end_matches_baseline(tmp_path):
    from pybamm_closed_loop.pybamm_engine import BaselineRunConfig
    from tests.characterization._charconfig import CHAR_BASELINE_DICT

    config = BaselineRunConfig.model_validate(CHAR_BASELINE_DICT)
    cfg_path = tmp_path / "char_baseline_120s.yaml"
    cfg_path.write_text(yaml.safe_dump(config.model_dump()), encoding="utf-8")

    out_dir = tmp_path / "cli_out"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_baseline.py"),
            "--config",
            str(cfg_path),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr

    expected = _load_npz(BASE_DIR / "char_baseline_120s.npz")
    actual = _load_npz(out_dir / "solution_arrays.npz")
    assert set(expected) == set(actual), "CLI npz key set differs from engine npz"
    for key, arr in expected.items():
        got = actual[key]
        assert got.shape == arr.shape, f"{key}: CLI shape {got.shape} != {arr.shape}"
        assert np.allclose(
            got, arr, rtol=1e-12, atol=1e-12, equal_nan=True
        ), f"{key}: CLI output drifted beyond rtol=atol=1e-12"
