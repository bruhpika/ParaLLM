"""Agent A regression tests for the fitting adapter (requires pybop; skipped without it)."""

import pytest

pybop = pytest.importorskip("pybop")

from pybamm_closed_loop.calibration.fitting import (  # noqa: E402
    FitParameter,
    FitSpec,
    run_fit_with_result,
)


def make_spec(n_params: int = 1) -> FitSpec:
    names = [
        "Negative electrode active material volume fraction",
        "Positive electrode active material volume fraction",
    ][:n_params]
    bounds = {"Negative electrode active material volume fraction": (0.55, 0.9),
              "Positive electrode active material volume fraction": (0.45, 0.8)}
    defaults = {"Negative electrode active material volume fraction": 0.65,
                "Positive electrode active material volume fraction": 0.55}
    return FitSpec(
        parameter_set="Chen2020",
        model_name="SPM",
        fit_parameters=[FitParameter(n, defaults[n], bounds[n]) for n in names],
        method="L-BFGS-B",
        maxiter=1,
    )


def test_run_fit_rejects_initial_values_length_mismatch():
    """A wrong-length initial_values list must fail loudly, not silently truncate."""
    spec = make_spec(n_params=2)
    # problem is not touched before the length check: a sentinel is enough
    with pytest.raises(ValueError, match="initial_values length"):
        run_fit_with_result(object(), spec, initial_values=[0.65])
    with pytest.raises(ValueError, match="initial_values length"):
        run_fit_with_result(object(), spec, initial_values=[0.65, 0.55, 0.5])
    with pytest.raises(ValueError, match="initial_values length"):
        run_fit_with_result(object(), spec, initial_values=[])


def test_run_fit_accepts_matching_initial_values():
    """Matching length passes the x0 checks; the stub records the initial value set."""
    spec = make_spec(n_params=1)

    recorded = {}

    class FakeParam:
        def update_initial_value(self, value):
            recorded["value"] = float(value)

    class FakeParameters:
        def get(self, name):
            return FakeParam()

    problem = type("P", (), {})()
    problem.parameters = FakeParameters()
    # optimiser construction with the stub problem fails inside PyBOP; the
    # assertion below proves the initial-value plumbing ran first
    with pytest.raises(Exception) as excinfo:
        run_fit_with_result(problem, spec, initial_values=[0.65])
    assert recorded == {"value": pytest.approx(0.65)}
    assert "initial_values length" not in str(excinfo.value)
