"""Unit tests: registry seeding logic with synthetic inputs (P3).

Runs without pybamm: a synthetic ParameterValues-style dict plus a
synthetic archive text assembled from the real probe strings.
"""

import inspect

import pytest

from pybamm_closed_loop.registry import sources as S
from pybamm_closed_loop.registry.model import ParameterStatus as PS, ReviewState as RS
from pybamm_closed_loop.registry.seed import build_records, seed_registry

FUNCTION_KEYS = {
    "Negative electrode OCP [V]",
    "Positive electrode OCP [V]",
    "Negative electrode exchange-current density [A.m-2]",
    "Positive electrode exchange-current density [A.m-2]",
    "Electrolyte diffusivity [m2.s-1]",
    "Electrolyte conductivity [S.m-1]",
}


def _synthetic_text() -> str:
    probes = [
        getattr(S, n)
        for n in dir(S)
        if n.startswith("PROBE_") and isinstance(getattr(S, n), str)
    ]
    probes += [
        "we assume the reaction to be symmetric",
        "At 1C (5 A) we have that the applied current density",
    ]
    return "\n\n".join(f"Evidence sentence containing {p}. End." for p in probes)


def _synthetic_params() -> dict:
    from pybamm_closed_loop.registry.seed import SPEC

    params = {}
    for spec in SPEC.values():
        key = spec.get("pybamm")
        if not key:
            continue
        if key in FUNCTION_KEYS:
            params[key] = lambda *a, **k: 0.0
        elif "volume fraction" in key:
            params[key] = 0.75 if key.startswith("Negative") else 0.665
        elif key == "Negative particle diffusivity [m2.s-1]":
            params[key] = 3.3e-14
        elif key == "Positive particle diffusivity [m2.s-1]":
            params[key] = 4e-15
        else:
            params[key] = 1.0
    params["Initial SEI thickness [m]"] = 5e-09
    return params


@pytest.fixture(scope="module")
def records():
    return build_records(_synthetic_params(), _synthetic_text())


def test_full_coverage(records):
    ids = {r.canonical_id for r in records}
    assert "neg_electrode_active_material_volume_fraction" in ids
    assert "pos_reaction_rate" in ids
    assert "initial_sei_thickness" in ids
    assert len(records) >= 45


def test_matched_values_are_literature_derived(records):
    rec = next(r for r in records if r.canonical_id == "neg_electrode_active_material_volume_fraction")
    assert rec.status == PS.LITERATURE_DERIVED
    assert rec.validation_state == RS.ACCEPTED
    assert rec.pybop_mapping["p2_approved_pair"] is True


def test_tuned_values_are_calibrated_with_preserved_conflict(records):
    rec = next(r for r in records if r.canonical_id == "neg_particle_diffusivity")
    assert rec.status == PS.CALIBRATED
    assert rec.validation_state == RS.NEEDS_REVIEW
    assert len(rec.conflicts) == 1
    conflict = rec.conflicts[0]
    assert conflict.value == 1.74e-15
    assert conflict.kind == PS.LITERATURE_DERIVED  # measured GITT value preserved
    assert conflict.review_state == RS.NEEDS_REVIEW
    assert rec.value == 3.3e-14  # operative value untouched


def test_bruggeman_assumption_conflict_preserved(records):
    rec = next(r for r in records if r.canonical_id == "pos_bruggeman_electrolyte")
    assert rec.status == PS.ASSUMED
    assert rec.conflicts[0].value == "2.43"


def test_untraced_defaults_are_unresolved(records):
    rec = next(r for r in records if r.canonical_id == "initial_sei_thickness")
    assert rec.status == PS.UNRESOLVED
    assert rec.validation_state == RS.NEEDS_REVIEW


def test_paper_only_parameters_carry_paper_value(records):
    rec = next(r for r in records if r.canonical_id == "pos_reaction_rate")
    assert rec.pybamm_names == []
    assert rec.value == "3.42e-6"
    assert rec.normalized_value == 3.42e-6
    assert rec.normalized_value_unit == "A.m-2.(m3.mol-1)^1.5"


def test_quotes_are_verbatim_substrings(records):
    text = _synthetic_text()
    found = 0
    for rec in records:
        if rec.evidence and rec.evidence.source.quote:
            src = rec.evidence.source
            assert src.char_start is not None
            assert text[src.char_start : src.char_end].strip() == src.quote.strip()
            found += 1
    assert found > 5


def test_seed_registry_writes_store(tmp_path):
    raw = tmp_path / "archive.txt"
    raw.write_text(_synthetic_text())
    store = seed_registry(
        tmp_path / "registry",
        pybamm_params=_synthetic_params(),
        raw_text_path=raw,
    )
    assert len(store) == len(build_records(_synthetic_params(), _synthetic_text()))
    assert store.proof_of_content()
