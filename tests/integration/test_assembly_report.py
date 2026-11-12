"""Integration test: assemble the real registry into dossiers (v0.2).

Uses the committed parameter registry (96 records, 7 preserved conflicts) and
the committed literature store. Deterministic; no network.
"""

from __future__ import annotations

import json
from pathlib import Path

from pybamm_closed_loop.assembly import (
    ApprovalGate,
    Rubric,
    TargetSpecification,
    assemble,
)
from pybamm_closed_loop.assembly.dossier import DOSSIER_FIELDS

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/registry/registry.json"

TARGET = TargetSpecification(
    target_id="lgm50_chen2020_dfn",
    cell_product="LG M50",
    chemistry_families=("NMC", "graphite"),
    format="21700",
    temperature_k=298.15,
    soc="50%",
)


def _records() -> list[dict]:
    return json.loads(REGISTRY.read_text())


def _report():
    return assemble(_records(), TARGET, Rubric("rubric-v1"))


class TestAssemblyOverRealRegistry:
    def test_every_record_produces_a_dossier(self):
        records = _records()
        report = _report()
        assert len(report.dossiers) == len(records)

    def test_all_nine_fields_present_in_every_dossier(self):
        report = _report()
        for d in report.dossiers:
            for field in DOSSIER_FIELDS:
                assert field in d, f"{d['parameter']} missing {field}"

    def test_same_source_conflicts_adopt_the_operative_value(self):
        report = _report()
        conflicts = [d for d in report.dossiers if d["conflict"]]
        assert len(conflicts) == 7
        for d in conflicts:
            assert d["conflict_class"] == "same_source"
            assert d["selected"]["value"] is not None
            assert len(d["alternatives"]) == 1  # the alternative is preserved

    def test_bruggeman_conflict_keeps_the_measured_value_visible(self):
        report = _report()
        d = next(x for x in report.dossiers if x["parameter"] == "neg_bruggeman_electrolyte")
        assert d["selected"]["value"] == 1.5
        assert any(str(a["value"]) == "2.91" for a in d["alternatives"])

    def test_no_unapproved_parameter_is_exported(self):
        report = _report()
        gate = ApprovalGate()
        exported = report.pybamm_export(gate)
        assert exported == {}
        gate.approve("neg_bruggeman_electrolyte", "FIX", "owner", "rubric-v1")
        exported = report.pybamm_export(gate)
        assert exported == {"neg_bruggeman_electrolyte": 1.5}

    def test_summary_is_consistent(self):
        summary = _report().summary()
        assert summary["n_parameters"] == 96
        assert summary["n_conflicts"] == 7
        assert summary["same_source_conflicts"] == 7
        assert sum(summary["decisions"].values()) == 96

    def test_markdown_renders(self):
        text = _report().to_markdown()
        assert "PARALLM parameter assembly" in text
        assert "neg_bruggeman_electrolyte" in text
