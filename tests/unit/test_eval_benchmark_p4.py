"""Unit tests for the P4 evaluation harness (benchmark_p4).

No network access: LLM clients are stubs. Deterministic; no seeds needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pybamm_closed_loop.eval.benchmark_p4 import (
    BenchmarkItemP4,
    GoldEntryP4,
    RetryClient,
    _canonical_unit,
    _groups,
    _quote_verified,
    _scale_factor,
    load_items_v2,
    rescore_arm_from_raw,
    score_item,
)


def _item(**kw) -> BenchmarkItemP4:
    base = dict(
        item_id="T",
        document_id="doc",
        passage_probe="probe",
        facets={"parameter_names": ["x"], "materials": [], "cell_chemistry": [],
                "cell_format": [], "conditions": {}, "techniques": []},
    )
    base.update(kw)
    return BenchmarkItemP4(**base)


class TestGroups:
    def test_underscore_folding_matches_p3_synonyms(self):
        assert "porosity" in _groups("electrolyte_volume_fraction")

    def test_scorer_local_max_concentration_group(self):
        assert "max_concentration" in _groups("maximum lithium concentration in the positive electrode")
        assert "max_concentration" in _groups("maximum concentration")
        assert "max_concentration" in _groups("max_concentration")

    def test_unrelated_name_has_no_groups(self):
        assert _groups("color of the sky") == set()


class TestUnitCanonicalization:
    def test_plain(self):
        assert _canonical_unit("m2 s-1")[0] == "m2.s-1"
        assert _canonical_unit("S m-1")[0] == "S.m-1"

    def test_scientific_notation_factor(self):
        rest, factor = _scale_factor("1e-15 m2 s-1")
        assert rest == "m2 s-1"
        assert factor == pytest.approx(1e-15)

    def test_paper_caption_scale_factor(self):
        rest, factor = _scale_factor("10-15 m2 s-1")
        assert rest == "m2 s-1"
        assert factor == pytest.approx(1e-15)

    def test_plain_decimal_never_factors(self):
        # "0.5 mol dm-3" is a unit with a preceding value; benchmark protocol
        # forbids silently consuming it (rule 6)
        rest, factor = _scale_factor("0.5 mol dm-3")
        assert factor == 1.0

    def test_caret_typography_for_reaction_rate(self):
        canon, _ = _canonical_unit("A m^-2 (m^3 mol^-1)^1.5")
        assert canon == "A.m-2.(m3.mol-1)^1.5"

    def test_space_typography_for_reaction_rate(self):
        canon, _ = _canonical_unit("A m-2 (m3 mol-1)1.5")
        assert canon == "A.m-2.(m3.mol-1)^1.5"

    def test_unknown_unit_raises(self):
        with pytest.raises(KeyError):
            _canonical_unit("blorp per second")


class TestQuoteVerification:
    RAW = "line one\ncites values 0.2594 for t+.\nline two"

    def _cand(self, quote, doc="doc"):
        return {"source": {"document_id": doc, "quote": quote}}

    def test_line_breaks_are_typography(self):
        assert _quote_verified(self._cand("cites values 0.2594 for t+."), "doc", self.RAW)
        assert _quote_verified(self._cand("cites\nvalues 0.2594\nfor t+."), "doc", self.RAW)

    def test_reordered_or_spliced_quotes_fail(self):
        assert not _quote_verified(
            self._cand("values 0.2594 cites"), "doc", self.RAW
        )

    def test_wrong_document_fails(self):
        assert not _quote_verified(self._cand("t+"), "other", self.RAW)

    def test_empty_quote_fails(self):
        assert not _quote_verified({"source": {"document_id": "doc"}}, "doc", self.RAW)


def _full_schema(**overrides) -> dict:
    payload = dict(
        parameter_name="nominal cell capacity",
        value=5.0,
        unit="Ah",
        definition="rated capacity",
        material="LGM50",
        temperature=None,
        cell_config=None,
        measurement_method="UNRESOLVED",
        qualifier="measured",
        context="text",
        source={"document_id": "doc", "quote": "5 Ah"},
        reported_uncertainty=None,
    )
    payload.update(overrides)
    return payload


class TestScoreItem:
    def _probed(self, tmp_path: Path) -> tuple[BenchmarkItemP4, str]:
        (tmp_path / "doc.txt").write_text("rcvlcd: the rated capacity is 5 Ah (2.5-4.2 V).\nAnother 4.87 mAh cm-2.")
        item = _item(
            gold=[GoldEntryP4(parameter_name="nominal cell capacity", value=5.0, unit="A.h")],
        )
        return item, (tmp_path / "doc.txt").read_text()

    def test_direct_match(self, tmp_path):
        item, raw = self._probed(tmp_path)
        cand = dict(
            parameter_name="nominal cell capacity", value=5.0, unit="Ah",
            temperature=None, cell_config="UNRESOLVED",
            source={"document_id": "doc", "quote": "rated capacity is 5 Ah"},
        )
        row = score_item(item, [cand], False, raw)
        assert row["matched"] == 1
        assert row["value_ok"] == 1
        assert row["unit_ok"] == 1
        assert row["provenance_ok"] == 1
        assert row["false_extractions"] == 0

    def test_excess_supported_vs_false_unsupported(self, tmp_path):
        item, raw = self._probed(tmp_path)
        excess = _full_schema(
            parameter_name="separator foil color",
            value=4.87,
            unit="mA.h cm-2",
            context="Another 4.87 mAh cm-2.",
            source={"document_id": "doc", "quote": "Another 4.87 mAh cm-2."},
        )
        hallucinated = _full_schema(
            parameter_name="separator foil color",
            value=1.11,
            unit="mA.h cm-2",
            context="Another 1.11 mAh cm-2.",
            source={"document_id": "doc", "quote": "Another 1.11 mAh cm-2."},
        )
        row = score_item(item, [excess, hallucinated], False, raw)
        assert row["matched"] == 0
        assert row["excess_extractions"] == 1
        assert row["false_extractions"] == 1

    def test_canonical_scale_value_match(self, tmp_path):
        # diffusivity printed with a scale-leading unit ("1e-15 m2 s-1")
        (tmp_path / "d.txt").write_text("table: 1.48 x 10^-15 m2/s (NMC).")
        item = _item(
            gold=[
                GoldEntryP4(
                    parameter_name="positive particle diffusivity",
                    value=1.48e-15,
                    unit="m2 s-1",
                )
            ],
        )
        cand = dict(
            parameter_name="positive particle diffusivity", value=1.48,
            unit="1e-15 m2 s-1", temperature=None, cell_config="25 C",
            source={"document_id": "d", "quote": "table: 1.48 x 10^-15 m2/s"},
        )
        row = score_item(item, [cand], False, (tmp_path / "d.txt").read_text())
        # scale-leading unit "1e-15 m2 s-1" with value 1.48 equals 1.48e-15 m2/s
        # and canonicalizes to plain m2.s-1; matches the plain-unit gold
        assert row["value_ok"] == 1
        assert row["unit_ok"] == 1


class TestRetryClient:
    class Flaky:
        def __init__(self, script):
            self.script = script
            self.calls = 0
            self.name = "llm:stub"
            self.base_url = "https://example.invalid/v1"
            self.model = "m"

        def complete(self, system, user):
            outcome = self.script[min(self.calls, len(self.script) - 1)]
            self.calls += 1
            if isinstance(outcome, BaseException) and not isinstance(outcome, ValueError):
                raise outcome
            if isinstance(outcome, ValueError):
                raise outcome
            return outcome

    def test_retries_transient_then_succeeds(self, monkeypatch):
        monkeypatch.setattr(
            "pybamm_closed_loop.eval.benchmark_p4.time.sleep", lambda *_: None
        )
        flaky = self.Flaky([ConnectionError("x"), "OK"])
        assert RetryClient(flaky).complete("sys", "usr") == "OK"
        assert flaky.calls == 2

    def test_exhausts_retries_then_raises(self, monkeypatch):
        monkeypatch.setattr(
            "pybamm_closed_loop.eval.benchmark_p4.time.sleep", lambda *_: None
        )
        flaky = self.Flaky([ConnectionError("x")] * 3)
        with pytest.raises(ConnectionError):
            RetryClient(flaky).complete("sys", "usr")

    def test_value_error_is_not_retried(self):
        flaky = self.Flaky([ValueError("bad model output")])
        with pytest.raises(ValueError):
            RetryClient(flaky).complete("sys", "usr")
        assert flaky.calls == 1


class TestLoadItemsV2:
    FIXTURE = Path(__file__).resolve().parents[2] / "data/eval/extraction_benchmark_v2.jsonl"

    def test_fixture_loads_with_audit_fields(self):
        items = load_items_v2(self.FIXTURE)
        assert len(items) >= 15
        splits = {it.split for it in items}
        assert splits == {"dev", "eval"}
        tiers = {it.tier for it in items}
        assert tiers == {"same-doc-dev", "same-doc-heldout", "cross-document", "other-cell-family"}
        # every non-abstain item carries at least one qualifier or alt
        for it in items:
            for g in it.gold:
                assert g.qualifier in {"measured", "assumed", "calculated", "fitted"}

    def test_dev_items_are_exactly_the_p3_six_families(self):
        items = [it for it in load_items_v2(self.FIXTURE) if it.split == "dev"]
        assert len(items) == 6


class TestRescoreFromRaw:
    class _StubStore:
        def __init__(self, raw_dir: Path):
            self.raw_dir = raw_dir

    def test_rescore_parses_frozen_raw_and_scores(self, tmp_path):
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        (raw_dir / "doc.txt").write_text("rcvlcd body 5 Ah capacity here.")
        item = _item(
            gold=[GoldEntryP4(parameter_name="nominal cell capacity", value=5.0, unit="A.h")],
        )
        raw_str = json.dumps(
            [
                _full_schema(
                    source={"document_id": "doc", "quote": "5 Ah capacity here."}
                )
            ]
        )
        report = rescore_arm_from_raw(
            [item], self._StubStore(raw_dir), [dict(item_id="T", provider="llm:stub", raw=raw_str)], "llm_stub"
        )
        row = report["per_item"][0]
        assert row["matched"] == 1
        assert report["raw_outputs"][0]["raw"].startswith("[")
        assert report["metrics"]["all"]["parameter_identification_accuracy"] == 1.0

    def test_rescore_rejects_missing_raw(self, tmp_path):
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        with pytest.raises(ValueError):
            rescore_arm_from_raw(
                [_item()], self._StubStore(raw_dir), [], "llm_stub"
            )
