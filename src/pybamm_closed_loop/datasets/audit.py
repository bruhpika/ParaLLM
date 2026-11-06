"""Experimental dataset audit records (P3, Part F).

Datasets are audited against the LG M50 requirements of
docs/EXPERIMENTAL_DATA_REQUIREMENTS.md; NO dataset is selected here. The
Neware sample is an ingestion test only and is explicitly incompatible with
the LG M50 demonstrator.
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from typing import Any


class CompatibilityVerdict(str, enum.Enum):
    CANDIDATE = "CANDIDATE"  # plausible, full audit pending
    PARTIAL = "PARTIAL"  # some requirements unmet/unverified
    INCOMPATIBLE = "INCOMPATIBLE"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class AuditRequirement:
    requirement: str
    observed: str
    status: str  # "met" | "unmet" | "unknown"
    evidence: str | None = None


@dataclass
class DatasetCandidate:
    dataset_id: str
    title: str
    source_url: str | None
    doi_or_identifier: str | None
    license: str | None
    chemistry: str | None
    cell_format: str | None
    nominal_capacity: str | None
    temperature: str | None
    c_rates: str | None
    voltage_limits: str | None
    protocol: str | None
    metadata_completeness: str
    observations: str  # raw / processed / summary-only / unknown
    requirements: list[AuditRequirement] = field(default_factory=list)
    verdict: CompatibilityVerdict = CompatibilityVerdict.UNRESOLVED
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


def assess_candidate(
    candidate: DatasetCandidate,
) -> tuple[CompatibilityVerdict, list[str]]:
    """Deterministic verdict from requirement rows (never from LLM output)."""
    statuses = [r.status for r in candidate.requirements]
    missing = [r.requirement for r in candidate.requirements if r.status != "met"]
    if any(r.status == "unmet" for r in candidate.requirements if "identity" in r.requirement.lower() or "capacity" in r.requirement.lower()):
        return CompatibilityVerdict.INCOMPATIBLE, missing
    if not statuses:
        return CompatibilityVerdict.UNRESOLVED, missing
    if all(s == "met" for s in statuses):
        return CompatibilityVerdict.CANDIDATE, []
    if all(s == "unknown" for s in statuses):
        return CompatibilityVerdict.UNRESOLVED, missing
    return CompatibilityVerdict.PARTIAL, missing
