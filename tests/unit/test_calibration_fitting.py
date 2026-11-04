"""Unit tests for the fitting adapter (requires pybop; skipped without it)."""

import pytest

pybop = pytest.importorskip("pybop")

from pybamm_closed_loop.calibration.fitting import (  # noqa: E402
    FitParameter,
    FitSpec,
    build_problem,
    run_fit,
)
from pybamm_closed_loop.calibration.synthetic import (  # noqa: E402
    SyntheticCondition,
    SyntheticSpec,
    generate_datasets,
)


def make_spec(**overrides):
    raw = dict(
        parameter_set="Chen2020",
        model_name="SPM",
        fit_parameters=[
            FitParameter(
                name="Negative electrode active material volume fraction",
                initial_value=0.65,
                bounds=(0.55, 0.9),
            ),
        ],
        cost="SumSquaredError",
        method="L-BFGS-B",
        maxiter=3,
        jac=True,
    )
    raw.update(overrides)
    return FitSpec(**raw)


def test_fitspec_rejects_initial_outside_bounds():
    with pytest.raises(ValueError, match="outside bounds"):
        make_spec(
            fit_parameters=[
                FitParameter("Negative electrode active material volume fraction",
                             initial_value=0.99, bounds=(0.55, 0.9))
            ]
        ).validate()


def test_fitspec_rejects_likelihood_without_sigma():
    with pytest.raises(ValueError, match="sigma"):
        make_spec(cost="GaussianLogLikelihood", sigma=None).validate()


def test_fitspec_rejects_unknown_cost():
    with pytest.raises(ValueError, match="unsupported cost"):
        make_spec(cost="MadeUpCost").validate()


def test_tiny_fit_runs_and_reports():
    synth = SyntheticSpec(
        parameter_set="Chen2020",
        model_name="SPM",
        true_values={"Negative electrode active material volume fraction": 0.75},
        conditions=[SyntheticCondition(name="1C", steps=["Discharge at 1C for 60 s"])],
        noise_sigma_V=1e-3,
        seed=5,
    )
    datasets = generate_datasets(synth)
    spec = make_spec()
    problem, info = build_problem(datasets, spec)
    assert info["kind"] == "Problem"
    report = run_fit(
        problem,
        spec,
        truth={"Negative electrode active material volume fraction": 0.75},
    )
    assert report["fit_spec"]["parameter_set"] == "Chen2020"
    assert report["parameters"][0]["name"].startswith("Negative electrode")
    est = report["parameters"][0]["estimate"]
    assert 0.55 <= est <= 0.9
    assert "recovery" in report
    assert report["runtime_s"] > 0


def test_multi_condition_builds_metaproblem():
    synth = SyntheticSpec(
        parameter_set="Chen2020",
        model_name="SPM",
        true_values={"Negative electrode active material volume fraction": 0.75},
        conditions=[
            SyntheticCondition(name="1C", steps=["Discharge at 1C for 60 s"]),
            SyntheticCondition(name="2C", steps=["Discharge at 2C for 30 s"]),
        ],
        noise_sigma_V=1e-3,
        seed=5,
    )
    datasets = generate_datasets(synth)
    problem, info = build_problem(datasets, make_spec())
    assert info["kind"] == "MetaProblem"
    assert info["conditions"] == ["1C", "2C"]
    assert problem.n_parameters == 1
