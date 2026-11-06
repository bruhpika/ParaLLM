"""Unit tests: registry model + store (P3)."""

import json

from pybamm_closed_loop.registry.model import (
    ParameterRecord,
    ParameterStatus as PS,
    ReviewState as RS,
    SourceRef,
    ValueEntry,
    validate_extraction_schema,
)
from pybamm_closed_loop.registry.store import RegistryStore, ValueCandidate


def _record(cid="neg_x", value=0.5):
    return ParameterRecord(
        canonical_id=cid,
        pybamm_names=["Negative electrode active material volume fraction"],
        pybop_mapping=None,
        definition="test",
        value=value,
        value_unit="dimensionless",
        normalized_value=value,
        normalized_value_unit="fraction",
        status=PS.LITERATURE_DERIVED,
        source_id="10.x/test",
        source_location="Table I",
        evidence=ValueEntry(
            value=value,
            unit="-",
            source=SourceRef(document_id="doc1", locator="Table I"),
            kind=PS.LITERATURE_DERIVED,
        ),
        conditions={},
        method="measured",
        reported_uncertainty=None,
        validation_state=RS.ACCEPTED,
        compatibility={},
    )


def test_store_upsert_and_revision_log(tmp_path):
    store = RegistryStore(tmp_path)
    store.upsert(_record(value=0.5), actor="tester", note="first")
    store.upsert(_record(value=0.6), actor="tester", note="second")
    assert len(store) == 1
    assert store.get("neg_x").value == 0.6
    revisions = [
        json.loads(line) for line in (tmp_path / "revisions.jsonl").read_text().splitlines()
    ]
    assert len(revisions) == 1  # only the second upsert logs a previous state
    assert revisions[0]["previous"]["value"] == 0.5
    # reload from disk preserves record
    store2 = RegistryStore(tmp_path)
    assert store2.get("neg_x").value == 0.6


def test_conflicts_preserved_not_silently_selected(tmp_path):
    rec = _record()
    rec.conflicts.append(
        ValueEntry(
            value=0.9,
            unit="-",
            source=SourceRef(document_id="doc2"),
            kind=PS.LITERATURE_DERIVED,
            review_state=RS.NEEDS_REVIEW,
        )
    )
    store = RegistryStore(tmp_path)
    store.upsert(rec, actor="tester", note="conflict added")
    loaded = RegistryStore(tmp_path).get("neg_x")
    assert loaded.value == 0.5  # operative value unchanged
    assert len(loaded.conflicts) == 1  # conflict preserved
    assert loaded.conflicts[0].value == 0.9


def test_rejected_candidates_are_audited(tmp_path):
    store = RegistryStore(tmp_path)
    cand = ValueCandidate(
        canonical_id="neg_x",
        payload={"value": 5.0},
        validation_summary={"state": "REJECTED"},
        proposed_by="llm:test",
    )
    store.log_rejected(cand, "plausibility failure")
    entries = [
        json.loads(line) for line in (tmp_path / "rejected.jsonl").read_text().splitlines()
    ]
    assert entries[0]["reason"] == "plausibility failure"
    assert entries[0]["proposed_by"] == "llm:test"


def test_extraction_schema_validation():
    good = {
        "parameter_name": "positive particle radius",
        "value": 5.22e-6,
        "unit": "m",
        "definition": "mean particle radius",
        "material": "NMC 811",
        "temperature": 298.15,
        "cell_config": "LG M50 21700 half cell",
        "measurement_method": "SEM/ImageJ",
        "qualifier": "measured",
        "context": "SEM top-down analysis",
        "source": {"document_id": "doc1", "page": 3, "locator": "Table II", "quote": "..."},
        "reported_uncertainty": None,
    }
    ok, reason = validate_extraction_schema(good)
    assert ok, reason
    bad = dict(good)
    bad["qualifier"] = "probably"
    ok, reason = validate_extraction_schema(bad)
    assert not ok and "qualifier" in reason
    bad2 = dict(good)
    bad2["source"] = {"page": 2}
    ok, reason = validate_extraction_schema(bad2)
    assert not ok and "document_id" in reason
    bad3 = dict(good)
    del bad3["value"]
    ok, reason = validate_extraction_schema(bad3)
    assert not ok and "value" in reason
