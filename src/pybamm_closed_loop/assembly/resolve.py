"""Conflict resolution and decision making for the assembly layer.

Two conflict classes are handled differently, and the difference is recorded in
the rationale:

**same-source** — every surviving candidate comes from the same source (the
paper's own set value vs a value measured in the same paper). We adopt the
source's *operative* value, because what we parameterise is that paper's model;
the alternative is preserved as a conflict with its method. The literature
tells us *why* the source chose its value (e.g. Chen2020's Bruggeman 1.5).

**cross-source** — candidates come from different publications. They are ranked
by the rubric; if the top two are within ``review_margin`` the conflict is
genuinely ambiguous and is escalated (``REVIEW``) to the human approval gate
with the ranked alternatives shown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .rubric import Rubric, RubricOutcome
from .schema import CandidateValue, Decision, MethodClass, TargetSpecification


@dataclass
class Resolution:
    """Outcome of resolving one parameter."""

    canonical_id: str
    decision: Decision
    chosen: CandidateValue | None
    alternatives: list[CandidateValue] = field(default_factory=list)
    rejected: list[CandidateValue] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    outcomes: list[RubricOutcome] = field(default_factory=list)
    conflict: bool = False
    conflict_class: str | None = None
    review_required: bool = False
    rubric_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "decision": self.decision.value,
            "chosen": self.chosen.to_dict() if self.chosen else None,
            "alternatives": [c.to_dict() for c in self.alternatives],
            "rejected": [c.to_dict() for c in self.rejected],
            "rationale": list(self.rationale),
            "conflict": self.conflict,
            "conflict_class": self.conflict_class,
            "review_required": self.review_required,
            "rubric_version": self.rubric_version,
            "candidate_scores": [
                {
                    "value": o.candidate.value,
                    "unit": o.candidate.unit,
                    "source": o.candidate.source_id,
                    "operative": o.candidate.is_operative,
                    "total": round(o.total, 6),
                    "dimension_scores": {k: round(v, 4) for k, v in o.dimension_scores.items()},
                    "fired": o.fired,
                    "blockers": o.blockers,
                }
                for o in self.outcomes
            ],
        }


def _source_key(candidate: CandidateValue) -> str | None:
    """Identity of the *source* of a candidate (document id preferred).

    The registry mixes id spaces (a DOI for the operative value, a document id
    for its conflicts), so same-source detection must use one consistent key.
    """
    return candidate.source_document or candidate.source_id


def _distinct_values(candidates: Sequence[CandidateValue]) -> bool:
    """True when the candidates disagree numerically (or one is non-numeric)."""
    numeric = [c.canonical_value for c in candidates if c.canonical_value is not None]
    if len(candidates) != len(numeric):
        return True
    if len(numeric) < 2:
        return False
    return any(abs(v - numeric[0]) > 1e-12 * max(1.0, abs(numeric[0])) for v in numeric[1:])


def _decision_for_method(candidate: CandidateValue) -> Decision:
    """Decision implied by the method class when there is no conflict."""
    if candidate.method_class in (MethodClass.MEASURED, MethodClass.CALCULATED, MethodClass.FITTED):
        return Decision.USE
    if candidate.method_class in (MethodClass.ASSUMED, MethodClass.CALIBRATED):
        return Decision.FIX
    return Decision.FIX


def resolve_parameter(
    canonical_id: str,
    candidates: Sequence[CandidateValue],
    target: TargetSpecification,
    rubric: Rubric,
) -> Resolution:
    """Resolve one parameter's candidates into a decision with rationale."""
    if not candidates:
        return Resolution(
            canonical_id=canonical_id,
            decision=Decision.REVIEW,
            chosen=None,
            rationale=["no candidate values available for this parameter"],
            rubric_version=rubric.version,
            review_required=True,
        )

    siblings = [(c.source_id, c.canonical_value) for c in candidates]
    outcomes = [rubric.evaluate(c, target, siblings) for c in candidates]

    surviving = [o for o in outcomes if not o.blocked]
    rejected = [o for o in outcomes if o.blocked]

    rationale: list[str] = []
    for o in rejected:
        reasons = "; ".join(b["reason"] for b in o.blockers)
        rationale.append(
            f"REJECT {o.candidate.value} {o.candidate.unit or ''} "
            f"(source={o.candidate.source_id or 'unknown'}): {reasons}".strip()
        )

    if not surviving:
        return Resolution(
            canonical_id=canonical_id,
            decision=Decision.REVIEW,
            chosen=None,
            rejected=[o.candidate for o in rejected],
            rationale=rationale
            + ["no candidate survives the applicability rubric for this target"],
            outcomes=outcomes,
            rubric_version=rubric.version,
            review_required=True,
        )

    conflicting = _distinct_values([o.candidate for o in surviving])
    source_keys = {_source_key(o.candidate) for o in surviving}
    same_source = conflicting and len(source_keys) == 1

    if not conflicting:
        best = max(surviving, key=lambda o: o.total)
        decision = _decision_for_method(best.candidate)
        rationale.append(
            f"{decision.value}: single applicable candidate {best.candidate.value} "
            f"{best.candidate.unit or ''} (rubric score {best.total:.3f}, "
            f"method class {best.candidate.method_class.value})"
        )
        return Resolution(
            canonical_id=canonical_id,
            decision=decision,
            chosen=best.candidate,
            alternatives=[],
            rejected=[o.candidate for o in rejected],
            rationale=rationale,
            outcomes=outcomes,
            conflict=False,
            rubric_version=rubric.version,
        )

    ranked = sorted(surviving, key=lambda o: (-o.total, not o.candidate.is_operative))
    top, second = ranked[0], ranked[1]

    if same_source:
        operative = next((o for o in surviving if o.candidate.is_operative), None)
        chosen = operative if operative is not None else top
        conflict_class = "same_source"
        rationale.append(
            "CONFLICT (same source): the source's operative value is adopted because what "
            "is being parameterised is that source's model; the alternative value is "
            "preserved as a conflict with its method."
        )
        rationale.append(
            f"adopted {chosen.candidate.value} {chosen.candidate.unit or ''} "
            f"(source={chosen.candidate.source_id}, method class "
            f"{chosen.candidate.method_class.value}, rubric score {chosen.total:.3f})"
        )
        decision = _decision_for_method(chosen.candidate)
        alternatives = [o.candidate for o in surviving if o.candidate is not chosen.candidate]
        return Resolution(
            canonical_id=canonical_id,
            decision=decision,
            chosen=chosen.candidate,
            alternatives=alternatives,
            rejected=[o.candidate for o in rejected],
            rationale=rationale,
            outcomes=outcomes,
            conflict=True,
            conflict_class=conflict_class,
            rubric_version=rubric.version,
        )

    conflict_class = "cross_source"
    margin = top.total - second.total
    rationale.append(
        "CONFLICT (cross-source): candidates ranked by the applicability rubric"
    )
    if margin < rubric.review_margin:
        decision = Decision.REVIEW
        review_required = True
        rationale.append(
            f"REVIEW: top two candidates are within the review margin "
            f"({margin:.3f} < {rubric.review_margin:.3f}); the conflict is ambiguous and "
            f"is escalated to the human approval gate with the ranked alternatives."
        )
        return Resolution(
            canonical_id=canonical_id,
            decision=decision,
            chosen=None,
            alternatives=[o.candidate for o in surviving],
            rejected=[o.candidate for o in rejected],
            rationale=rationale,
            outcomes=outcomes,
            conflict=True,
            conflict_class=conflict_class,
            review_required=True,
            rubric_version=rubric.version,
        )

    decision = _decision_for_method(top.candidate)
    rationale.append(
        f"adopted {top.candidate.value} {top.candidate.unit or ''} "
        f"(source={top.candidate.source_id}, rubric score {top.total:.3f}; runner-up "
        f"{second.candidate.value} {second.candidate.unit or ''} from "
        f"{second.candidate.source_id} scored {second.total:.3f}, margin {margin:.3f})"
    )
    alternatives = [o.candidate for o in surviving if o.candidate is not top.candidate]
    return Resolution(
        canonical_id=canonical_id,
        decision=decision,
        chosen=top.candidate,
        alternatives=alternatives,
        rejected=[o.candidate for o in rejected],
        rationale=rationale,
        outcomes=outcomes,
        conflict=True,
        conflict_class=conflict_class,
        rubric_version=rubric.version,
    )
