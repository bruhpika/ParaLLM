"""Unit tests for P5 provenance verification (no network, archived docs)."""

from __future__ import annotations

from pathlib import Path

from pybamm_closed_loop.eval.benchmark_p4 import resolve_passage
from pybamm_closed_loop.eval.provenance_p5 import summarize, verify_candidate
from pybamm_closed_loop.literature.ingest import DocumentStore

STORE_DIR = Path(__file__).resolve().parents[2] / "data/literature_store"
DOC = "laue2021_jappl_electrochem_51_1253"
PROBE = "55.25"


def _candidate(quote: str, **source_overrides) -> dict:
    source = {
        "document_id": DOC,
        "page": None,
        "locator": None,
        "quote": quote,
    }
    source.update(source_overrides)
    return {
        "parameter_name": "negative electrode thickness",
        "value": 55.25,
        "unit": "um",
        "temperature": None,
        "cell_config": "UNRESOLVED",
        "source": source,
    }


class TestVerifyCandidate:
    def setup_method(self):
        self.store = DocumentStore(STORE_DIR)
        self.quote = resolve_passage(self.store, DOC, PROBE)

    def test_verbatim_quote_from_archive(self):
        report = verify_candidate(_candidate(self.quote), self.store, DOC)
        assert report.document_match is True
        assert report.quote_verbatim is True
        assert report.quote_present is True
        assert report.splice_suspected is False
        assert report.paraphrase_warning is False
        assert report.quote_position is not None

    def test_page_matches_segment_page(self):
        base = verify_candidate(_candidate(self.quote), self.store, DOC)
        assert base.page_actual is not None
        good = verify_candidate(
            _candidate(self.quote, page=base.page_actual), self.store, DOC
        )
        assert good.page_ok is True
        bad = verify_candidate(
            _candidate(self.quote, page=base.page_actual + 1), self.store, DOC
        )
        assert bad.page_ok is False

    def test_page_unchecked_when_quote_unverifiable(self):
        report = verify_candidate(
            _candidate("this sentence does not exist", page=3), self.store, DOC
        )
        assert report.quote_verbatim is False
        assert report.page_ok is None

    def test_document_mismatch_flagged(self):
        report = verify_candidate(
            _candidate(self.quote, document_id="some_other_document"),
            self.store,
            DOC,
        )
        assert report.document_match is False
        # quote still verifies against the item's archive text
        assert report.quote_verbatim is True

    def test_ellipsis_splice_flagged(self):
        half = len(self.quote) // 2
        spliced = f"{self.quote[:half]} ... {self.quote[half:]}"
        report = verify_candidate(_candidate(spliced), self.store, DOC)
        assert report.splice_suspected is True
        assert report.quote_verbatim is False

    def test_paraphrase_near_miss_flagged(self):
        words = self.quote.split()
        words.insert(max(1, len(words) // 2), "additionally")
        report = verify_candidate(_candidate(" ".join(words)), self.store, DOC)
        assert report.quote_verbatim is False
        assert report.paraphrase_warning is True
        assert report.best_contiguous_fraction >= 0.8

    def test_locator_visible_near_quote(self):
        report = verify_candidate(
            _candidate("Table 3", locator="Table 3"), self.store, DOC
        )
        assert report.locator_visible is True

    def test_conditions_rule(self):
        cand = _candidate(self.quote)
        assert verify_candidate(cand, self.store, DOC).conditions_ok is False
        cand["temperature"] = 298.15
        cand["cell_config"] = "NMC111/graphite coin cell"
        assert verify_candidate(cand, self.store, DOC).conditions_ok is True


class TestSummarize:
    def test_rates(self):
        store = DocumentStore(STORE_DIR)
        quote = resolve_passage(store, DOC, PROBE)
        reports = [
            verify_candidate(_candidate(quote), store, DOC),
            verify_candidate(_candidate("missing text", document_id="x"), store, DOC),
        ]
        summary = summarize(reports)
        assert summary["n_candidates"] == 2
        assert summary["document_match_rate"] == 0.5
        assert summary["quote_verbatim_rate"] == 0.5

    def test_empty(self):
        summary = summarize([])
        assert summary["n_candidates"] == 0
