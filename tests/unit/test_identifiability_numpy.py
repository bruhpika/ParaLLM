"""Unit tests for identifiability math (pure numpy - run in every environment)."""

import numpy as np
import pytest

from pybamm_closed_loop.calibration.identifiability import (
    finite_difference_jacobian,
    fim_diagnostics,
    normalized_sensitivity,
    parametric_bootstrap,
    profile_likelihood,
)


def test_jacobian_of_linear_model():
    a = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])

    def predict(x):
        return a @ x

    jac = finite_difference_jacobian(predict, np.array([0.3, -0.2]))
    assert jac.shape == (3, 2)
    assert np.allclose(jac, a, rtol=1e-6)


def test_jacobian_respects_bounds():
    def predict(x):
        return np.array([x[0] ** 2])

    bounds = np.array([[0.0, 0.1]])
    jac = finite_difference_jacobian(predict, np.array([0.099]), bounds=bounds)
    assert np.isfinite(jac).all()


def test_normalized_sensitivity_scaling():
    jac = np.array([[2.0, 0.0], [0.0, 4.0]])
    s = normalized_sensitivity(jac, np.array([10.0, 0.5]), y_scale=2.0)
    assert s.shape == (2, 2)
    assert s[0, 0] == pytest.approx(10.0)  # (10/2)*2
    assert s[1, 1] == pytest.approx(1.0)   # (0.5/2)*4


def test_fim_diagnostics_detects_correlation():
    # Two nearly-parallel (but not exactly proportional) sensitivity columns
    t = np.linspace(0, 1, 50)
    jac = np.column_stack([t, t * 1.0001 + 1e-6])
    out = fim_diagnostics(jac, sigma=1e-3)
    assert out["fim"].shape == (2, 2)
    assert abs(out["correlation"][0, 1]) > 0.99
    assert out["condition_number"] > 1e3


def test_fim_diagnostics_rank_deficient_is_infinite():
    jac = np.column_stack([np.linspace(0, 1, 50), 2.0 * np.linspace(0, 1, 50)])
    out = fim_diagnostics(jac, sigma=1e-3)
    assert out["condition_number"] == float("inf")


def test_fim_diagnostics_orthogonal_columns_low_correlation():
    jac = np.column_stack([np.ones(50), np.linspace(-1, 1, 50)])
    out = fim_diagnostics(jac, sigma=1e-3)
    assert abs(out["correlation"][0, 1]) < 0.2


def test_profile_likelihood_calls_refit_per_grid_point():
    calls = []

    def make_problem(fixed_values):
        calls.append(dict(fixed_values))
        return object()

    def run_fit_fn(problem, free_param, free_bounds, free_initial):
        val = calls[-1]["p1"]
        return {"final_cost": (val - 0.5) ** 2, "estimate": 0.25}

    out = profile_likelihood(
        make_problem, run_fit_fn, "p1", np.array([0.4, 0.5, 0.6]), "p2", (0.0, 1.0), 0.25
    )
    assert len(calls) == 3
    assert out["costs"][1] == pytest.approx(0.0)
    assert out["fixed_param"] == "p1"


def test_parametric_bootstrap_collects_estimates():
    def refit(i):
        return {"estimates": {"a": 1.0 + 0.01 * i, "b": 2.0}, "final_cost": 0.0}

    out = parametric_bootstrap(refit, n_boot=5, seed=7)
    assert out["names"] == ["a", "b"]
    assert len(out["estimates"]) == 5
    assert out["mean"][1] == pytest.approx(2.0)
    assert out["bootstrap_seed"] == 7
