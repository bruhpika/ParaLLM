"""Unit tests for output extraction logic using a stub solution (no PyBaMM)."""

import numpy as np
import pytest

from pybamm_closed_loop.pybamm_engine.outputs import extract_all, extract_series


class StubVar:
    def __init__(self, entries):
        self.entries = np.asarray(entries, dtype=float)


class StubSolution:
    """Minimal stand-in exposing the parts of a PyBaMM solution that we use."""

    def __init__(self, t, variables):
        self.t = np.asarray(t, dtype=float)
        self._variables = variables

    def __getitem__(self, name):
        if name not in self._variables:
            raise KeyError(name)
        return StubVar(self._variables[name])


@pytest.fixture
def stub_solution():
    t = np.linspace(0.0, 100.0, 11)
    return StubSolution(
        t,
        {
            "Terminal voltage [V]": 4.0 - 0.001 * t,
            "Current [A]": np.full_like(t, 5.0),
        },
    )


def test_extract_series_found_and_missing(stub_solution):
    found, missing = extract_series(
        stub_solution, ["Terminal voltage [V]", "Current [A]", "Does not exist [V]"]
    )
    assert "Time [s]" in found
    assert "Terminal voltage [V]" in found
    assert "Current [A]" in found
    assert missing == ["Does not exist [V]"]
    assert found["Terminal voltage [V]"].shape == found["Time [s]"].shape


def test_extract_series_skips_wrong_shape(stub_solution):
    stub_solution._variables["Bad shape"] = np.zeros(3)
    found, missing = extract_series(stub_solution, ["Bad shape"])
    assert "Bad shape" not in found
    assert missing == ["Bad shape"]


def test_extract_all_reports_unavailable_profiles(stub_solution):
    result = extract_all(
        stub_solution,
        series_names=["Terminal voltage [V]"],
        profile_names=["Electrolyte concentration [mol.m-3]"],
        fractions=[0.5],
    )
    assert result.unavailable_profiles == ["Electrolyte concentration [mol.m-3]"]
    assert result.profiles == {}
    report = result.availability_report
    assert report["series_unavailable"] == []
    assert report["profiles_unavailable"] == ["Electrolyte concentration [mol.m-3]"]


def test_extraction_never_fabricates_values(stub_solution):
    """Missing variables must be reported, never synthesised."""
    result = extract_all(stub_solution, ["Missing [V]"], ["Missing profile [V]"], [0.5])
    assert result.series == {"Time [s]": stub_solution.t}
    assert result.unavailable_series == ["Missing [V]"]
    assert result.unavailable_profiles == ["Missing profile [V]"]
