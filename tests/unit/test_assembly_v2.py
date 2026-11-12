"""Unit tests for the v0.2 assembly layer (rubric, resolution, dossier, gate).

No network; the rubric is deterministic, so results are reproducible.
"""

from __future__ import annotations

import pytest

from pybamm_closed_loop.assembly import (
    ApprovalGate,
    CandidateValue,
    ConditionFacts,
    Decision,
    MethodClass,
    Rubric,
    TargetSpecification,
    dossier,
    resolve_parameter,
)
from pybamm_closed_loop.assembly.dossier import DOSSIER_FIELDS

TARGET = TargetSpecification(
    target_id="lgm50",
    cell_product="LG M50",
    chemistry_families=("NMC", "graphite"),
    format="21700",
    temperature_k=298.15,
    soc="50%",
)


def _candidate(
    value,
    unit,
    *,
    method_class=MethodClass.MEASURED,
    source_id="doc-a",
    source_document="doc-a",
    conditions=None,
    quote=None,
    quote_verified=None,
    is_operative=False,
    model_applicable=True,
):
    return CandidateValue(
        canonical_id="p",
        value=value,
        unit=unit,
        canonical_value=float(value) if isinstance(value, (int, float)) else None,
        canonical_unit=unit,
        method_class=method_class,
        method="test method",
        status="LITERATURE_DERIVED",
        conditions=conditions
        or ConditionFacts(
            cell_product="LG M50",
            format="21700",
            chemistry_families=("NMC", "graphite"),
            temperature_k=298.15,
            soc="50%",
        ),
        source_id=source_id,
        source_document=source_document,
        source_locator="Table 1",
        page=7,
        quote=quote,
        quote_present=bool(quote),
        quote_verified=quote_verified,
        is_operative=is_operative,
        model_applicable=model_applicable,
    )


class TestRubric:
    def test_weights_sum_to_one(self):
        with pytest.raises(ValueError):
            Rubric("bad", weights={"chemistry": 0.5})

    def test_matching_candidate_scores_high(self):
        rubric = Rubric("rubric-v1")
        outcome = rubric.evaluate(_candidate(1.0, "dimensionless"), TARGET)
        assert outcome.total > 0.8
        assert not outcome.blocked

    def test_chemistry_family_mismatch_blocks(self):
        rubric = Rubric("rubric-v1")
        cand = _candidate(
            1.0,
            "dimensionless",
            conditions=ConditionFacts(
                cell_product="other cell",
                format="coin",
                chemistry_families=("LFP",),
                temperature_k=298.15,
            ),
        )
        outcome = rubric.evaluate(cand, TARGET)
        assert outcome.blocked
        assert any("chemistry" in b["dimension"] for b in outcome.blockers)

    def test_failed_quote_verification_blocks(self):
        rubric = Rubric("rubric-v1")
        outcome = rubric.evaluate(
            _candidate(1.0, "dimensionless", quote="x", quote_verified=False), TARGET
        )
        assert outcome.blocked
        assert any("evidence" in b["dimension"] for b in outcome.blockers)

    def test_not_declarable_in_model_blocks(self):
        rubric = Rubric("rubric-v1")
        outcome = rubric.evaluate(
            _candidate(1.0, "dimensionless", model_applicable=False), TARGET
        )
        assert outcome.blocked

    def test_rules_are_recorded_with_inputs(self):
        rubric = Rubric("rubric-v1")
        outcome = rubric.evaluate(_candidate(1.0, "dimensionless"), TARGET)
        assert outcome.fired
        assert all("reason" in f and "inputs" in f for f in outcome.fired)

    def test_temperature_mismatch_lowers_score(self):
        rubric = Rubric("rubric-v1")
        warm = _candidate(
            1.0,
            "dimensionless",
            conditions=ConditionFacts(
                cell_product="LG M50",
                format="21700",
                chemistry_families=("NMC", "graphite"),
                temperature_k=333.15,
            ),
        )
        cold = rubric.evaluate(_candidate(1.0, "dimensionless"), TARGET)
        hot = rubric.evaluate(warm, TARGET)
        assert hot.total < cold.total


class TestResolution:
    def test_single_candidate_measured_is_use(self):
        rubric = Rubric("rubric-v1")
        res = resolve_parameter("p", [_candidate(1.0, "dimensionless")], TARGET, rubric)
        assert res.decision is Decision.USE
        assert not res.conflict

    def test_single_candidate_assumed_is_fix(self):
        rubric = Rubric("rubric-v1")
        cand = _candidate(1.0, "dimensionless", method_class=MethodClass.ASSUMED)
        res = resolve_parameter("p", [cand], TARGET, rubric)
        assert res.decision is Decision.FIX

    def test_same_source_conflict_adopts_operative(self):
        rubric = Rubric("rubric-v1")
        operative = _candidate(
            1.5, "dimensionless", method_class=MethodClass.ASSUMED, is_operative=True
        )
        alternative = _candidate(
            2.4, "dimensionless", method_class=MethodClass.CALCULATED, is_operative=False
        )
        res = resolve_parameter("p", [operative, alternative], TARGET, rubric)
        assert res.conflict
        assert res.conflict_class == "same_source"
        assert res.chosen is operative
        assert len(res.alternatives) == 1
        assert "operative" in " ".join(res.rationale)

    def test_cross_source_small_margin_escalates_to_review(self):
        rubric = Rubric("rubric-v1", review_margin=0.5)
        a = _candidate(1.0, "dimensionless", source_id="doc-a", source_document="doc-a")
        b = _candidate(2.0, "dimensionless", source_id="doc-b", source_document="doc-b")
        res = resolve_parameter("p", [a, b], TARGET, rubric)
        assert res.decision is Decision.REVIEW
        assert res.review_required
        assert len(res.alternatives) == 2

    def test_cross_source_clear_winner_is_chosen(self):
        rubric = Rubric("rubric-v1", review_margin=0.01)
        a = _candidate(
            1.0,
            "dimensionless",
            source_id="doc-a",
            source_document="doc-a",
            conditions=ConditionFacts(
                cell_product="LG M50",
                format="21700",
                chemistry_families=("NMC", "graphite"),
                temperature_k=298.15,
                soc="50%",
            ),
        )
        b = _candidate(
            2.0,
            "dimensionless",
            source_id="doc-b",
            source_document="doc-b",
            conditions=ConditionFacts(
                cell_product=None,
                format=None,
                chemistry_families=(),
                temperature_k=None,
            ),
        )
        res = resolve_parameter("p", [a, b], TARGET, rubric)
        assert res.decision in (Decision.USE, Decision.FIX)
        assert res.chosen is a
        assert res.conflict_class == "cross_source"

    def test_all_blocked_escalates_to_review(self):
        rubric = Rubric("rubric-v1")
        bad = _candidate(
            1.0,
            "dimensionless",
            quote="x",
            quote_verified=False,
            conditions=ConditionFacts(chemistry_families=("LFP",)),
        )
        res = resolve_parameter("p", [bad], TARGET, rubric)
        assert res.decision is Decision.REVIEW
        assert res.rejected


class TestDossier:
    def test_all_nine_fields_present(self):
        rubric = Rubric("rubric-v1")
        cand = _candidate(1.0, "dimensionless", quote="a quote", quote_verified=True)
        res = resolve_parameter("p", [cand], TARGET, rubric)
        d = dossier(res)
        for field in DOSSIER_FIELDS:
            assert field in d
        assert d["selected"]["value"] == 1.0
        assert d["literature_value"]["as_printed"] == 1.0
        assert d["evidence"]["quote"] == "a quote"
        assert d["evidence"]["page"] == 7
        assert d["identifiability"]["status"] == "not_assessed"
        assert d["approval"]["status"] == "pending"
        assert d["recommendation"]["decision"] == res.decision.value

    def test_identifiability_and_approval_can_be_filled(self):
        rubric = Rubric("rubric-v1")
        res = resolve_parameter("p", [_candidate(1.0, "dimensionless")], TARGET, rubric)
        d = dossier(
            res,
            identifiability={"status": "unobservable", "note": "|S| = 0.02", "source": "P2"},
            approval={"status": "approved", "approver": "owner", "timestamp": "t"},
        )
        assert d["identifiability"]["status"] == "unobservable"
        assert d["approval"]["status"] == "approved"


class TestApprovalGate:
    def test_approval_roundtrip(self):
        gate = ApprovalGate()
        gate.approve("p", "USE", "owner", "rubric-v1", note="ok")
        assert gate.is_approved("p")
        restored = ApprovalGate.from_dict(gate.to_dict())
        assert restored.is_approved("p")
        assert restored.records[0].approver == "owner"

    def test_rejection_does_not_approve(self):
        gate = ApprovalGate()
        gate.reject("p", "REVIEW", "owner", "rubric-v1")
        assert not gate.is_approved("p")
