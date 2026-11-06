"""Unit tests: dataset audit logic (P3)."""

from pybamm_closed_loop.datasets.audit import (
    AuditRequirement,
    CompatibilityVerdict,
    DatasetCandidate,
    assess_candidate,
)


def _req(status):
    return AuditRequirement("cell identity matches LG M50 / Chen2020 scope", "x", status)


def test_identity_mismatch_is_incompatible():
    cand = DatasetCandidate(
        dataset_id="d1", title="t", source_url=None, doi_or_identifier=None,
        license=None, chemistry="NMC622", cell_format="pouch", nominal_capacity="0.04 A.h",
        temperature=None, c_rates=None, voltage_limits=None, protocol=None,
        metadata_completeness="partial", observations="raw",
        requirements=[_req("unmet")],
    )
    verdict, missing = assess_candidate(cand)
    assert verdict == CompatibilityVerdict.INCOMPATIBLE
    assert missing


def test_all_met_is_candidate():
    cand = DatasetCandidate(
        dataset_id="d2", title="t", source_url=None, doi_or_identifier=None,
        license="CC-BY", chemistry="graphite|NMC811", cell_format="21700",
        nominal_capacity="5 A.h", temperature="298.15 K", c_rates="0.5C/1C/2C",
        voltage_limits="2.5-4.2 V", protocol="documented", metadata_completeness="full",
        observations="raw",
        requirements=[
            AuditRequirement("cell identity", "LG M50", "met"),
            AuditRequirement("capacity", "5 A.h", "met"),
        ],
    )
    verdict, missing = assess_candidate(cand)
    assert verdict == CompatibilityVerdict.CANDIDATE
    assert not missing


def test_unknown_is_unresolved():
    cand = DatasetCandidate(
        dataset_id="d3", title="t", source_url=None, doi_or_identifier=None,
        license=None, chemistry=None, cell_format=None, nominal_capacity=None,
        temperature=None, c_rates=None, voltage_limits=None, protocol=None,
        metadata_completeness="none", observations="unknown",
        requirements=[AuditRequirement("cell identity", "?", "unknown")],
    )
    verdict, _ = assess_candidate(cand)
    assert verdict == CompatibilityVerdict.UNRESOLVED


def test_partial_requirements_are_partial():
    cand = DatasetCandidate(
        dataset_id="d4", title="t", source_url=None, doi_or_identifier=None,
        license=None, chemistry="graphite|NMC811", cell_format="21700",
        nominal_capacity="5 A.h", temperature="298.15 K", c_rates="1C",
        voltage_limits="2.5-4.2 V", protocol="partial", metadata_completeness="partial",
        observations="processed",
        requirements=[
            AuditRequirement("cell identity", "LG M50", "met"),
            AuditRequirement("low-rate reference", "absent", "unknown"),
        ],
    )
    verdict, missing = assess_candidate(cand)
    assert verdict == CompatibilityVerdict.PARTIAL
    assert missing == ["low-rate reference"]
