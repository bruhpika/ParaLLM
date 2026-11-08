"""Unit tests for P5 scoring extensions and the P5 harness (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pybamm_closed_loop.eval.benchmark_p4 import _metrics, resolve_passage
from pybamm_closed_loop.eval.benchmark_p5 import (
    _canonical_unit_p5,
    _groups_p5,
    aggregate_repeats,
    load_items_v3,
    score_item_p5,
)
from pybamm_closed_loop.literature.ingest import DocumentStore

ROOT = Path(__file__).resolve().parents[2]
STORE = DocumentStore(ROOT / "data/literature_store")
ITEMS = load_items_v3(ROOT / "data/eval/extraction_benchmark_v3.jsonl")


def _item(item_id: str):
    return next(it for it in ITEMS if it.item_id == item_id)


def _candidate(name, value, unit, quote, doc, **kw):
    base = dict(
        parameter_name=name,
        value=value,
        unit=unit,
        definition="d",
        material="UNRESOLVED",
        temperature=None,
        cell_config="UNRESOLVED",
        measurement_method="UNRESOLVED",
        qualifier="assumed",
        context="c",
        reported_uncertainty=None,
        source={"document_id": doc, "page": None, "locator": None, "quote": quote},
    )
    base.update(kw)
    return base


class TestUnitExtensions:
    def test_molarity_to_mol_per_m3(self):
        assert _canonical_unit_p5("mol.L-1") == ("mol.m-3", pytest.approx(1e3))
        assert _canonical_unit_p5("mol l-1") == ("mol.m-3", pytest.approx(1e3))

    def test_entropy_units(self):
        assert _canonical_unit_p5("J.mol-1.K-1") == ("J.mol-1.K-1", 1.0)
        assert _canonical_unit_p5("kJ.mol-1.K-1") == ("J.mol-1.K-1", pytest.approx(1e3))

    def test_charge_per_mole(self):
        assert _canonical_unit_p5("C.mol-1") == ("C.mol-1", 1.0)
        assert _canonical_unit_p5("s.A.mol-1") == ("C.mol-1", 1.0)

    def test_positive_power_scale(self):
        assert _canonical_unit_p5("10^4 A.m-2") == ("A.m-2", pytest.approx(1e4))
        assert _canonical_unit_p5("104 A.m-2") == ("A.m-2", pytest.approx(1e4))

    def test_negative_power_scale(self):
        assert _canonical_unit_p5("10-15 m2.s-1") == ("m2.s-1", pytest.approx(1e-15))

    def test_falls_back_to_p3_table(self):
        assert _canonical_unit_p5("kJ.mol-1") == ("J.mol-1", pytest.approx(1e3))
        assert _canonical_unit_p5("um") == ("m", pytest.approx(1e-6))


class TestGroupExtensions:
    def test_symmetry_factor_family(self):
        assert "symmetry_factor" in _groups_p5("symmetry factor")
        assert "symmetry_factor" in _groups_p5("charge transfer coefficient")
        assert "symmetry_factor" in _groups_p5("anodic transfer coefficient")

    def test_activation_energy(self):
        assert "activation_energy" in _groups_p5("SEI activation energy")

    def test_cell_area(self):
        assert "cell_area" in _groups_p5("cell area")
        assert "cell_area" in _groups_p5("electrode area")

    def test_unrelated(self):
        assert _groups_p5("color of the sky") == set()


class TestScoreItemP5:
    def test_full_match_with_scaled_units(self):
        item = _item("P5-D2-sei-j0-arrhenius")
        quote = resolve_passage(STORE, item.document_id, item.passage_probe)
        cands = [
            _candidate(
                "SEI exchange current density",
                14.7,
                "10^4 A.m-2",
                quote,
                item.document_id,
                temperature=333.15,
                cell_config="LFP/graphite coin cell",
            ),
            _candidate(
                "SEI activation energy",
                86.2,
                "kJ.mol-1",
                quote,
                item.document_id,
                temperature=333.15,
                cell_config="LFP/graphite coin cell",
            ),
        ]
        row = score_item_p5(item, cands, False, STORE, _raw(item))
        assert row["gold"] == 2
        assert row["matched"] == 2
        assert row["value_ok"] == 2
        assert row["unit_ok"] == 2
        assert row["conditions_ok"] == 2
        assert row["provenance_ok"] == 2
        assert row["qualifier_ok"] == 2
        assert row["false_extractions"] == 0

    def test_unrelated_unverifiable_candidate_counts_false(self):
        item = _item("P5-L1-thickness-table")
        bad = _candidate(
            "color of the sky", 42.0, "dimensionless", "not in the document",
            item.document_id,
        )
        row = score_item_p5(item, [bad], False, STORE, _raw(item))
        assert row["false_extractions"] == 1

    def test_abstention_row(self):
        item = _item("P5-L8-abstain-tortuosity-exponent")
        row = score_item_p5(item, [], True, STORE, _raw(item))
        assert row["abstained"] is True
        assert row["matched"] == 0


def _raw(item) -> str:
    return (STORE.raw_dir / f"{item.document_id}.txt").read_text()


def _rows(**overrides):
    base = dict(
        split="eval",
        tier="same-doc-heldout",
        gold=2,
        matched=2,
        value_ok=1,
        unit_ok=2,
        conditions_ok=2,
        provenance_ok=1,
        qualifier_ok=1,
        expect_abstain=False,
        abstained=False,
        false_extractions=0,
        n_extracted=3,
    )
    base.update(overrides)
    return base


class TestAggregateRepeats:
    def test_mean_and_std_across_repeats(self):
        r1 = dict(metrics=_metrics([_rows(value_ok=2)]), provenance_summary=_prov(1.0))
        r2 = dict(metrics=_metrics([_rows(value_ok=0)]), provenance_summary=_prov(0.0))
        agg = aggregate_repeats([r1, r2])
        cell = agg["all"]["value_extraction_accuracy"]
        assert cell["mean"] == pytest.approx(0.5)
        assert cell["std"] == pytest.approx(0.5)
        assert cell["n"] == 2
        assert agg["provenance"]["quote_verbatim_rate"] == pytest.approx(0.5)

    def test_single_repeat_has_zero_std(self):
        agg = aggregate_repeats(
            [dict(metrics=_metrics([_rows()]), provenance_summary=_prov(1.0))]
        )
        assert agg["all"]["unit_accuracy"]["std"] == 0.0


def _prov(v: float) -> dict:
    keys = (
        "document_match_rate",
        "quote_present_rate",
        "quote_verbatim_rate",
        "splice_rate",
        "paraphrase_warning_rate",
        "page_ok_rate",
        "locator_visible_rate",
        "conditions_ok_rate",
    )
    return {k: v for k in keys}
