"""Unit tests for the V2.5 evidence layer (deterministic, no network)."""

from __future__ import annotations

from pathlib import Path

from pybamm_closed_loop.literature.evidence import (
    build_evidence_window,
    document_conditions,
    extract_conditions,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/literature_store/raw"


def _raw(doc: str) -> str:
    return (RAW / f"{doc}.txt").read_text()


class TestConditionExtraction:
    def test_temperature_celsius_to_kelvin(self):
        facts = extract_conditions("The cell was tested in a chamber at 25 °C.")
        assert facts.temperature_k == pytest_approx(298.15)
        assert facts.coverage()["temperature"] is True

    def test_temperature_kelvin(self):
        facts = extract_conditions("All measurements were performed at 298.15 K.")
        assert facts.temperature_k == pytest_approx(298.15)

    def test_soc_and_rate(self):
        facts = extract_conditions("Impedance spectra were recorded at 50% SOC at 0.1C.")
        assert facts.soc_percent == 50
        assert 0.1 in facts.c_rates

    def test_no_conditions_is_empty(self):
        facts = extract_conditions("A short sentence without conditions.")
        assert facts.coverage() == {
            "temperature": False,
            "soc": False,
            "c_rate": False,
            "cell": False,
            "chemistry": False,
            "method": False,
        }


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value)


class TestEvidenceWindow:
    def test_probe_is_kept_verbatim(self):
        raw = _raw("laue2021_jappl_electrochem_51_1253")
        window = build_evidence_window(raw, "doc", "55.25")
        assert "55.25" in window.text
        assert window.char_end > window.char_start

    def test_window_is_a_verbatim_substring(self):
        raw = _raw("laue2021_jappl_electrochem_51_1253")
        window = build_evidence_window(raw, "doc", "55.25")
        assert raw[window.char_start : window.char_end] == window.text

    def test_expansion_grows_the_window(self):
        raw = _raw("laue2021_jappl_electrochem_51_1253")
        compact = build_evidence_window(raw, "doc", "55.25", compact_chars=260, expand_chars=260)
        expanded = build_evidence_window(raw, "doc", "55.25", compact_chars=260, expand_chars=900)
        assert len(expanded.text) >= len(compact.text)

    def test_missing_probe_raises(self):
        raw = _raw("laue2021_jappl_electrochem_51_1253")
        try:
            build_evidence_window(raw, "doc", "this string is not in the document")
        except ValueError:
            return
        raise AssertionError("expected ValueError for a missing probe")


class TestDocumentConditions:
    def test_finds_setup_statements_in_real_document(self):
        raw = _raw("chen2020_jes_167_080534")
        doc_conditions = document_conditions(raw, max_sentences=8)
        coverage = doc_conditions.coverage()
        assert coverage["temperature"] is True
        assert coverage["cell"] is True
        assert coverage["chemistry"] is True

    def test_statements_are_verbatim(self):
        raw = _raw("chen2020_jes_167_080534")
        doc_conditions = document_conditions(raw, max_sentences=8)
        for sentence in doc_conditions.sentences:
            assert sentence in raw

    def test_deterministic(self):
        raw = _raw("laue2021_jappl_electrochem_51_1253")
        a = document_conditions(raw, max_sentences=6).sentences
        b = document_conditions(raw, max_sentences=6).sentences
        assert a == b
