"""Human approval gate for assembled parameter decisions (rule 10).

The assembly engine produces *decision support*. A parameter only enters the
approved set after a human approves the decision, and the approval records
which rubric version produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ApprovalRecord:
    """One recorded human approval (or rejection) of a decision."""

    parameter: str
    decision: str
    approved: bool
    approver: str
    rubric_version: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "decision": self.decision,
            "approved": self.approved,
            "approver": self.approver,
            "rubric_version": self.rubric_version,
            "timestamp": self.timestamp,
            "note": self.note,
        }


class ApprovalGate:
    """Collects approvals; exposes which parameters may enter the approved set."""

    def __init__(self) -> None:
        self._records: list[ApprovalRecord] = []

    @property
    def records(self) -> list[ApprovalRecord]:
        return list(self._records)

    def approve(
        self,
        parameter: str,
        decision: str,
        approver: str,
        rubric_version: str,
        note: str = "",
    ) -> ApprovalRecord:
        rec = ApprovalRecord(
            parameter=parameter,
            decision=decision,
            approved=True,
            approver=approver,
            rubric_version=rubric_version,
            note=note,
        )
        self._records.append(rec)
        return rec

    def reject(
        self,
        parameter: str,
        decision: str,
        approver: str,
        rubric_version: str,
        note: str = "",
    ) -> ApprovalRecord:
        rec = ApprovalRecord(
            parameter=parameter,
            decision=decision,
            approved=False,
            approver=approver,
            rubric_version=rubric_version,
            note=note,
        )
        self._records.append(rec)
        return rec

    def approved_parameters(self) -> set[str]:
        return {r.parameter for r in self._records if r.approved}

    def is_approved(self, parameter: str) -> bool:
        return parameter in self.approved_parameters()

    def to_dict(self) -> dict[str, Any]:
        return {"approvals": [r.to_dict() for r in self._records]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ApprovalGate":
        gate = cls()
        for item in payload.get("approvals", []):
            gate._records.append(
                ApprovalRecord(
                    parameter=item["parameter"],
                    decision=item["decision"],
                    approved=bool(item["approved"]),
                    approver=item["approver"],
                    rubric_version=item["rubric_version"],
                    timestamp=item.get("timestamp", ""),
                    note=item.get("note", ""),
                )
            )
        return gate
