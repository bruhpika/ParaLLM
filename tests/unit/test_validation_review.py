"""Unit tests: deterministic validation + review states (P3)."""

from pybamm_closed_loop.registry.model import (
    ParameterRecord,
    ParameterStatus as PS,
    ReviewState as RS,
    SourceRef,
)
from pybamm_closed_loop.registry.store import RegistryStore
from pybamm_closed_loop.validation.checks import review_candidate

ARCHIVE_TEXT = (
    "Evidence sentence: the mean particle radius is 5.22 um by SEM. "
    "End of evidence."
)


def _payload(**over):
    p = dict(
        parameter_name="positive particle radius",
        value=5.22e-6,
        unit="m",
        definition="mean particle radius",
        material="NMC 811",
        temperature=298.15,
        cell_config="LG M50 21700",
        measurement_method="SEM/ImageJ",
        qualifier="measured",
        context="SEM analysis",
        source={
            "document_id": "doc1",
            "page": None,
            "locator": "Table II",
            "quote": "the mean particle radius is 5.22 um by SEM",
        },
        reported_uncertainty=None,
    )
    p.update(over)
    return p


def _store(tmp_path):
    store = RegistryStore(tmp_path / "reg")
    store.upsert(
        ParameterRecord(
            canonical_id="pos_particle_radius",
            pybamm_names=["Positive particle radius [m]"],
            pybop_mapping=None,
            definition="r",
            value=5.22e-6,
            value_unit="m",
            normalized_value=5.22e-6,
            normalized_value_unit="m",
            status=PS.LITERATURE_DERIVED,
            source_id="doi",
            source_location="Table II",
            evidence=None,
            conditions={},
            method="SEM",
            reported_uncertainty=None,
            validation_state=RS.ACCEPTED,
            compatibility={},
        ),
        actor="t",
        note="seed",
    )
    return store


def test_clean_candidate_is_accepted(tmp_path):
    report = review_candidate(
        _payload(),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "ACCEPTED", report.reasons


def test_fabricated_quote_is_rejected(tmp_path):
    report = review_candidate(
        _payload(source={"document_id": "doc1", "quote": "this sentence does not exist anywhere"}),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "REJECTED"
    assert any("fabrication" in r for r in report.reasons)


def test_unknown_document_is_rejected(tmp_path):
    report = review_candidate(
        _payload(source={"document_id": "ghost", "quote": "x"}),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "REJECTED"


def test_conflicting_value_needs_review_and_preserves_both(tmp_path):
    report = review_candidate(
        _payload(value=1e-4),  # 20x the registry value
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "NEEDS_REVIEW"
    assert any("conflict" in r.lower() and "preserved" in r.lower() for r in report.reasons)


def test_implausible_value_is_rejected(tmp_path):
    report = review_candidate(
        _payload(value=5.22e-6, unit="dimensionless"),  # radius as dimensionless
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "REJECTED"


def test_unknown_unit_is_rejected(tmp_path):
    report = review_candidate(
        _payload(unit="parsecs per fortnight"),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "REJECTED"


def test_missing_conditions_warn_but_not_reject(tmp_path):
    report = review_candidate(
        _payload(temperature=None, cell_config="UNRESOLVED"),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    assert report.state == "NEEDS_REVIEW"


def test_fitted_qualifier_accepted_with_warning_note(tmp_path):
    report = review_candidate(
        _payload(qualifier="fitted"),
        _store(tmp_path),
        {"doc1": ARCHIVE_TEXT},
    )
    # fitted values are legitimate but must not masquerade as measurements
    assert report.state in ("ACCEPTED", "NEEDS_REVIEW")
    assert any("must NOT be recorded" in c.detail for c in report.checks)
