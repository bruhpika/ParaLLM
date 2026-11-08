"""Parameter registry data model (P3).

Provenance-first records for every parameter the closed loop touches.
The LLM never writes these records directly (scientific rule 10): values
enter only through deterministic seeding, validated extraction results, or
explicit user approval; the store preserves revisions so nothing is lost.
"""

from __future__ import annotations

import enum
import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


class ParameterStatus(str, enum.Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    LITERATURE_DERIVED = "LITERATURE_DERIVED"
    CALCULATED = "CALCULATED"
    ASSUMED = "ASSUMED"
    CALIBRATED = "CALIBRATED"
    UNRESOLVED = "UNRESOLVED"


class ReviewState(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


@dataclass
class SourceRef:
    """Location of the evidence for an extraction or record.

    ``locator`` must be an actual anchor (section heading, table caption,
    figure caption, page number from a real page structure). It must never
    be invented; when no anchor is known it stays ``UNRESOLVED``.
    """

    document_id: str
    title: str | None = None
    doi_or_url: str | None = None
    locator: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    quote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValueEntry:
    """One literature/paper/PyBaMM value attached to a canonical parameter.

    Multiple entries with different values are preserved as conflicts; the
    registry never silently selects one.
    """

    value: Any
    unit: str | None
    source: SourceRef
    kind: ParameterStatus
    reported_uncertainty: float | None = None
    uncertainty_note: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    method: str | None = None
    context: str | None = None
    review_state: ReviewState = ReviewState.NEEDS_REVIEW
    review_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["review_state"] = self.review_state.value
        d["source"] = self.source.to_dict()
        return d


@dataclass
class ParameterRecord:
    """Full provenance record for one canonical parameter (Part A, items 1-15)."""

    canonical_id: str
    pybamm_names: list[str]
    pybop_mapping: dict[str, Any] | None
    definition: str
    value: Any
    value_unit: str | None
    normalized_value: Any
    normalized_value_unit: str | None
    status: ParameterStatus
    source_id: str | None
    source_location: str | None
    evidence: ValueEntry | None
    conditions: dict[str, Any]
    method: str | None
    reported_uncertainty: float | None
    validation_state: ReviewState
    compatibility: dict[str, Any]
    conflicts: list[ValueEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["validation_state"] = self.validation_state.value
        d["evidence"] = self.evidence.to_dict() if self.evidence else None
        d["conflicts"] = [c.to_dict() for c in self.conflicts]
        return d


def sha256_text(text: str) -> str:
    """Return the SHA-256 hex digest of ``text`` (UTF-8 encoded).

    Used for content-keyed provenance identifiers; never carries secrets.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _schema_ok(obj: Any, spec: dict[str, type | tuple]) -> bool:
    """Minimal hand-rolled validator for JSON-able structured output."""
    if not isinstance(obj, dict):
        return False
    for key, types in spec.items():
        if key not in obj:
            if isinstance(types, tuple) and type(None) in types:
                continue
            return False
        if obj[key] is None:
            if isinstance(types, tuple) and type(None) in types:
                continue
            return False
        if not isinstance(obj[key], types):
            if isinstance(obj[key], str) and types is float:
                try:
                    float(obj[key])
                except ValueError:
                    return False
                continue
            return False
    # Extra keys are currently accepted; the computed flag was always
    # discarded (``True or extra``), so the dead variable was removed.
    # Rejecting unknown keys would be a behavioral change - flagged for
    # scientific review instead.
    return True


_EXTRACTION_SPEC: dict[str, Any] = {
    "parameter_name": str,
    "value": float,
    "unit": str,
    "definition": str,
    "material": str,
    "temperature": (float, type(None)),
    "cell_config": str,
    "measurement_method": str,
    "qualifier": str,
    "context": str,
    "source": SourceRef,
    "reported_uncertainty": (float, type(None)),
}

VALID_QUALIFIERS = ("measured", "fitted", "calculated", "assumed", "unknown")


def validate_extraction_schema(payload: Any) -> tuple[bool, str]:
    """Validate an LLM/offline extraction payload against the extraction schema.

    Returns (ok, reason). Never mutates the payload.
    """
    if not isinstance(payload, dict):
        return False, "payload is not an object"
    missing = [k for k in _EXTRACTION_SPEC if k not in payload]
    if missing:
        return False, f"missing required keys: {missing}"
    if not isinstance(payload["value"], (int, float)) or isinstance(
        payload["value"], bool
    ):
        if isinstance(payload["value"], str):
            try:
                float(payload["value"])
            except ValueError:
                return False, "value is not numeric"
        else:
            return False, "value is not numeric"
    if payload["qualifier"] not in VALID_QUALIFIERS:
        return False, f"qualifier must be one of {VALID_QUALIFIERS}"
    src = payload.get("source")
    if not isinstance(src, dict) or not src.get("document_id"):
        return False, "source must carry a document_id"
    return True, "ok"
