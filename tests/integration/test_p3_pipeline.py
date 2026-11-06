"""Integration tests: P3 full pipeline on the real Chen2020 archive (P3).

Requires the py3.12 integration environment (pybamm + pyprobe + polars +
pypdf). Library-only pieces degrade gracefully via importorskip.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ID = "chen2020_jes_167_080534"
RAW_TEXT = (
    REPO_ROOT
    / "data/raw_documents/chen2020_jes_167_080534/chen2020_jes_167_080534_fulltext.txt"
)


@pytest.fixture(scope="module")
def doc_store(tmp_path_factory):
    from pybamm_closed_loop.literature.ingest import DocumentStore

    store = DocumentStore(tmp_path_factory.mktemp("litstore"))
    store.ingest_text(DOC_ID, RAW_TEXT.read_text(), doi_or_url="10.1149/1945-7111/ab9050")
    return store


@pytest.fixture(scope="module")
def seeded_store(tmp_path_factory):
    pytest.importorskip("pybamm")
    from pybamm_closed_loop.registry.seed import seed_registry

    return seed_registry(tmp_path_factory.mktemp("registry"))


def test_real_seed_has_full_coverage_and_conflicts(seeded_store):
    assert len(seeded_store) == 96
    conflicts = sum(len(r.conflicts) for r in seeded_store.all_records())
    assert conflicts == 7  # 2 diffusivities + 2 max concentrations + 3 Bruggeman
    statuses = {r.status.value for r in seeded_store.all_records()}
    assert {"LITERATURE_DERIVED", "CALCULATED", "CALIBRATED", "ASSUMED", "UNRESOLVED"} <= statuses


def test_real_quotes_are_verbatim(seeded_store):
    text = RAW_TEXT.read_text()
    for rec in seeded_store.all_records():
        if rec.evidence and rec.evidence.source.quote:
            src = rec.evidence.source
            assert text[src.char_start : src.char_end].strip() == src.quote.strip()


def test_registry_to_pybop_declarations(seeded_store):
    from pybamm_closed_loop.registry.mapping import approved_pair, pybop_declarations

    neg, pos = approved_pair(seeded_store)
    assert neg.canonical_id.startswith("neg_") and pos.canonical_id.startswith("pos_")
    decls = pybop_declarations(seeded_store, [neg.canonical_id, pos.canonical_id])
    assert {d["canonical_id"] for d in decls} == {neg.canonical_id, pos.canonical_id}
    for d in decls:
        assert d["bounds"] and len(d["bounds"]) == 2


def test_registry_overlay_preserves_provenance(seeded_store):
    import pybamm

    from pybamm_closed_loop.registry.mapping import overlay_to_parameter_values

    pv = pybamm.ParameterValues("Chen2020")
    values = {k: pv[k] for k in pv}
    overlay = overlay_to_parameter_values(seeded_store, values)
    # seeded operative values equal the installed set -> overlay must be empty
    assert overlay == {}


def test_review_of_real_evidence_is_accepted(seeded_store, doc_store):
    from pybamm_closed_loop.validation.checks import review_candidate

    rec = seeded_store.get("cation_transference_number")
    payload = {
        "parameter_name": "Cation transference number",
        "value": rec.evidence.value,
        "unit": rec.evidence.unit,
        "definition": rec.definition,
        "material": "LiPF6 EC:EMC",
        "temperature": 298.15,
        "cell_config": "LG M50",
        "measurement_method": rec.evidence.method,
        "qualifier": "calculated",
        "context": rec.evidence.context or "",
        "source": {
            "document_id": rec.evidence.source.document_id,
            "page": None,
            "locator": rec.evidence.source.locator,
            "quote": rec.evidence.source.quote,
        },
        "reported_uncertainty": None,
    }
    report = review_candidate(payload, seeded_store, {DOC_ID: RAW_TEXT.read_text()})
    assert report.state == "ACCEPTED", report.reasons


def test_real_extraction_benchmark_provenance(doc_store, tmp_path):
    from pybamm_closed_loop.eval.benchmark import load_items, run_benchmark

    items = load_items(REPO_ROOT / "data/eval/extraction_benchmark_v1.jsonl")
    report = run_benchmark(items, doc_store)
    m = report["metrics"]
    assert m["provenance_accuracy"] == 1.0
    assert 0.0 <= m["false_extraction_rate"] <= 0.5
    assert m["parameter_identification_accuracy"] >= 0.9
    out = tmp_path / "report.json"
    out.write_text(json.dumps(report))
    assert json.loads(out.read_text())["metrics"] == m


def test_neware_sample_is_incompatible_with_lgm50():
    pytest.importorskip("polars")
    pytest.importorskip("pyprobe")
    from pybamm_closed_loop.datasets.pyprobe_link import audit_neware_sample

    cand = audit_neware_sample(REPO_ROOT / "data/external/pyprobe_sample/neware")
    assert cand.verdict.value == "INCOMPATIBLE"
    assert any("NOT validation data" in n for n in cand.notes)
    assert "README.yaml" in cand.protocol


def test_llm_client_requires_key():
    import os

    from pybamm_closed_loop.literature.extraction import OpenAICompatibleClient

    old = {k: os.environ.pop(k, None) for k in ("PYCL_LLM_API_KEY", "PYCL_LLM_MODEL")}
    try:
        with pytest.raises(RuntimeError, match="PYCL_LLM_API_KEY"):
            OpenAICompatibleClient()
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v
