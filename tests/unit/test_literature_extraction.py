"""Unit tests: structured extraction (P3)."""

import pytest

from pybamm_closed_loop.literature.extraction import (
    OfflineDeterministicExtractor,
    parse_llm_json,
    run_extraction,
)
from pybamm_closed_loop.literature.retrieval import RetrievedSegment

PASSAGE = (
    "The electronic conductivities were measured with a four-point probe. "
    "The values 0.18 S m-1 and 215 S m-1 were used for the positive "
    "electrode and the negative electrode respectively."
)

EMPTY_PASSAGE = "The morphologies of both electrodes were studied using SEM."


def _seg(text, doc="doc1"):
    return RetrievedSegment(
        segment_id=f"{doc}#seg0", document_id=doc, page=None, heading=None, text=text, score=1.0
    )


def test_offline_extractor_finds_numeric_evidence():
    batch = OfflineDeterministicExtractor().extract_from_segments([_seg(PASSAGE)])
    assert not batch.abstained
    values = sorted(c.payload["value"] for c in batch.valid())
    assert values == [0.18, 215.0]
    for c in batch.valid():
        assert c.payload["source"]["document_id"] == "doc1"
        assert c.payload["source"]["quote"]
        assert c.proposed_by == "deterministic"


def test_offline_extractor_abstains_without_numbers():
    batch = OfflineDeterministicExtractor().extract_from_segments([_seg(EMPTY_PASSAGE)])
    assert batch.abstained
    assert batch.valid() == []


def test_offline_extractor_scientific_notation():
    text = "the reaction rates are 3.42\u00b710-6 A m-2 for the positive electrode"
    batch = OfflineDeterministicExtractor().extract_from_segments([_seg(text)])
    vals = [c.payload["value"] for c in batch.valid()]
    assert any(abs(v - 3.42e-6) < 1e-15 for v in vals)


def test_qualifier_distinguishes_fitted_from_measured():
    fitted = "The diffusion coefficient was fitted by trial and error to 4e-15 m2 s-1."
    measured = "The particle radius was measured to be 5.22 um by SEM."
    b1 = OfflineDeterministicExtractor().extract_from_segments([_seg(fitted)])
    b2 = OfflineDeterministicExtractor().extract_from_segments([_seg(measured)])
    assert b1.valid()[0].payload["qualifier"] == "fitted"
    assert b2.valid()[0].payload["qualifier"] == "measured"


def test_parse_llm_json_tolerates_code_fences():
    out = '```json\n[{"parameter_name": "x", "value": 1.0}]\n```'
    assert parse_llm_json(out) == [{"parameter_name": "x", "value": 1.0}]
    with pytest.raises(ValueError):
        parse_llm_json("no json here")


class _FakeLLM:
    name = "llm:fake"

    def __init__(self, content):
        self._content = content

    def complete(self, system, user):
        assert "RULE: extract ONLY statements supported by the evidence" in user
        return self._content


def test_run_extraction_validates_schema_and_maps_unresolved():
    ctx_content = (
        '[{"parameter_name": "x", "value": 1.0, "unit": "m", "definition": "d",'
        ' "material": "NMC", "temperature": 298.0, "cell_config": "21700",'
        ' "measurement_method": "SEM", "qualifier": "measured", "context": "c",'
        ' "source": {"document_id": "doc1", "page": null, "locator": null, "quote": "q"},'
        ' "reported_uncertainty": null},'
        ' {"parameter_name": "UNRESOLVED", "value": "UNRESOLVED"}]'
    )
    from pybamm_closed_loop.literature.retrieval import RAGContext

    ctx = RAGContext(query="q", facets={}, segments=[_seg(PASSAGE)], retrieved_from=["doc1"])
    batch = run_extraction(_FakeLLM(ctx_content), ctx)
    assert len(batch.valid()) == 1  # UNRESOLVED entry skipped
    assert batch.valid()[0].proposed_by == "llm:fake"


def test_run_extraction_flags_unparseable_llm_output():
    from pybamm_closed_loop.literature.retrieval import RAGContext

    ctx = RAGContext(query="q", facets={}, segments=[_seg(PASSAGE)], retrieved_from=["doc1"])
    batch = run_extraction(_FakeLLM("I could not find evidence."), ctx)
    assert batch.abstained
    assert "unparseable" in batch.abstain_reason
