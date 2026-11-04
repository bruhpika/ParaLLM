"""Unit tests for synthetic generation (requires pybop; skipped without it)."""

import numpy as np
import pytest

pybop = pytest.importorskip("pybop")

from pybamm_closed_loop.calibration.synthetic import (  # noqa: E402
    SyntheticCondition,
    SyntheticSpec,
    generate_dataset,
)


def make_spec(**overrides):
    raw = dict(
        parameter_set="Chen2020",
        model_name="SPM",
        true_values={
            "Negative electrode active material volume fraction": 0.75,
        },
        conditions=[SyntheticCondition(name="1C", steps=["Discharge at 1C for 60 s"])],
        noise_sigma_V=1e-3,
        seed=123,
    )
    raw.update(overrides)
    return SyntheticSpec(**raw)


def test_spec_rejects_event_terminated_steps():
    spec = make_spec(
        conditions=[SyntheticCondition(name="x", steps=["Discharge at 1C until 2.5 V"])]
    )
    with pytest.raises(ValueError, match="event-terminated"):
        spec.validate()


def test_spec_rejects_empty_true_values():
    with pytest.raises(ValueError):
        make_spec(true_values={}).validate()


def test_spec_rejects_unknown_parameter_name():
    spec = make_spec(true_values={"Not a real parameter": 1.0})
    with pytest.raises(KeyError):
        generate_dataset(spec, spec.conditions[0])


def test_generation_is_deterministic_for_same_seed():
    spec = make_spec()
    _, meta1 = generate_dataset(spec, spec.conditions[0])
    ds2, meta2 = generate_dataset(spec, spec.conditions[0])
    assert meta1 == meta2
    # same seed -> identical noisy data
    ds1, _ = generate_dataset(spec, spec.conditions[0])
    assert np.array_equal(
        np.asarray(ds1.data["Voltage [V]"]), np.asarray(ds2.data["Voltage [V]"])
    )


def test_generation_metadata_records_ground_truth():
    spec = make_spec()
    ds, meta = generate_dataset(spec, spec.conditions[0])
    assert meta["true_values"] == spec.true_values
    assert meta["noise_sigma_V"] == 1e-3
    assert meta["seed"] == 123
    assert meta["n_points"] > 0
    assert ds.check()
