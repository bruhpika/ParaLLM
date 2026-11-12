"""Schema for the PARALLM assembly layer (target specification, candidates,
decisions).

Everything here is plain data: the assembly engine never invents values, it
only ranks and explains candidate values that already exist in the registry
or the extraction store.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping

from .lexicon import CellFacts, parse_cell_facts


class Decision(str, enum.Enum):
    """Decision vocabulary for one parameter.

    ``USE``       adopt this value for the target (evidence supports it)
    ``FIX``       adopt and hold constant (do not fit it)
    ``CALIBRATE`` free parameter for estimation (needs observability -> V2.3)
    ``MEASURE``   not identifiable now; specify the experiment (V2.3)
    ``REJECT``    exclude this candidate (inapplicable / unverifiable)
    ``REVIEW``    genuinely ambiguous: escalate to the human approval gate
    """

    USE = "USE"
    FIX = "FIX"
    CALIBRATE = "CALIBRATE"
    MEASURE = "MEASURE"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


class MethodClass(str, enum.Enum):
    """How a value was obtained (registry status + method text)."""

    MEASURED = "measured"
    FITTED = "fitted"
    CALCULATED = "calculated"
    ASSUMED = "assumed"
    CALIBRATED = "calibrated"
    UNKNOWN = "unknown"


# registry ParameterStatus -> MethodClass
STATUS_TO_METHOD: dict[str, MethodClass] = {
    "USER_SUPPLIED": MethodClass.MEASURED,
    "LITERATURE_DERIVED": MethodClass.UNKNOWN,
    "CALCULATED": MethodClass.CALCULATED,
    "ASSUMED": MethodClass.ASSUMED,
    "CALIBRATED": MethodClass.CALIBRATED,
    "UNRESOLVED": MethodClass.UNKNOWN,
}


@dataclass(frozen=True)
class ConditionFacts:
    """Structured view of the conditions attached to one candidate value."""

    cell_product: str | None = None
    format: str | None = None
    chemistry_families: tuple[str, ...] = ()
    temperature_k: float | None = None
    temperature_range_k: tuple[float, float] | None = None
    soc: str | None = None
    protocol: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, conditions: Mapping[str, Any] | None, extra_text: str = "") -> "ConditionFacts":
        conditions = dict(conditions or {})
        facts: CellFacts = parse_cell_facts(
            conditions.get("cell"),
            conditions.get("chemistry"),
            conditions.get("protocol"),
            extra_text,
        )
        point, rng = _parse_temperature_value(conditions.get("temperature_k"))
        if point is None and rng is None and conditions.get("chamber"):
            point, rng = _parse_temperature_value(conditions["chamber"])
        return cls(
            cell_product=facts.cell_product,
            format=facts.format,
            chemistry_families=facts.chemistry_families,
            temperature_k=point,
            temperature_range_k=rng,
            soc=conditions.get("soc"),
            protocol=conditions.get("protocol"),
            raw=conditions,
            warnings=facts.warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_product": self.cell_product,
            "format": self.format,
            "chemistry_families": list(self.chemistry_families),
            "temperature_k": self.temperature_k,
            "temperature_range_k": list(self.temperature_range_k) if self.temperature_range_k else None,
            "soc": self.soc,
            "protocol": self.protocol,
            "warnings": list(self.warnings),
        }


def _parse_temperature_value(value: Any) -> tuple[float | None, tuple[float, float] | None]:
    """Parse a temperature field into a point or a range, in Kelvin.

    Accepts numbers, numeric strings, '25 C'/'298.15 K' style text, and ranges
    such as '303.15-333.15' or '25-60 C'. Deterministic; never guesses.
    """
    import re

    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None

    s = str(value).strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:deg\s*c|°?\s*c|celsius)", s, re.IGNORECASE)
    if m:
        lo = float(m.group(1)) + 273.15
        m2 = re.search(r"(?:to|-|\u2013)\s*(-?\d+(?:\.\d+)?)\s*(?:deg\s*c|°?\s*c|celsius)", s, re.IGNORECASE)
        if m2:
            return None, (lo, float(m2.group(1)) + 273.15)
        return lo, None
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*k\b", s, re.IGNORECASE)
    if m:
        lo = float(m.group(1))
        m2 = re.search(r"(?:to|-|\u2013)\s*(-?\d+(?:\.\d+)?)\s*k\b", s, re.IGNORECASE)
        if m2:
            return None, (lo, float(m2.group(1)))
        return lo, None
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if len(nums) == 1:
        try:
            return float(nums[0]), None
        except ValueError:
            return None, None
    if len(nums) >= 2:
        try:
            return None, (float(nums[0]), float(nums[1]))
        except ValueError:
            return None, None
    return None, None


@dataclass(frozen=True)
class TargetSpecification:
    """The cell + protocol a parameter set is being assembled for."""

    target_id: str
    cell_product: str
    chemistry_families: tuple[str, ...]
    format: str | None = None
    temperature_k: float | None = None
    temperature_range_k: tuple[float, float] | None = None
    soc: str | None = None
    model: str = "DFN"
    parameter_set: str = "Chen2020"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "cell_product": self.cell_product,
            "chemistry_families": list(self.chemistry_families),
            "format": self.format,
            "temperature_k": self.temperature_k,
            "temperature_range_k": list(self.temperature_range_k) if self.temperature_range_k else None,
            "soc": self.soc,
            "model": self.model,
            "parameter_set": self.parameter_set,
            "notes": self.notes,
        }


@dataclass
class CandidateValue:
    """One candidate value for a parameter, ready for rubric evaluation."""

    canonical_id: str
    value: Any
    unit: str | None
    canonical_value: float | None = None
    canonical_unit: str | None = None
    method_class: MethodClass = MethodClass.UNKNOWN
    method: str | None = None
    status: str | None = None
    conditions: ConditionFacts = field(default_factory=ConditionFacts)
    source_id: str | None = None
    source_document: str | None = None
    source_locator: str | None = None
    page: int | None = None
    quote: str | None = None
    quote_present: bool | None = None
    quote_verified: bool | None = None
    is_operative: bool = False
    model_applicable: bool | None = None
    model_note: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "value": self.value,
            "unit": self.unit,
            "canonical_value": self.canonical_value,
            "canonical_unit": self.canonical_unit,
            "method_class": self.method_class.value,
            "method": self.method,
            "status": self.status,
            "conditions": self.conditions.to_dict(),
            "source_id": self.source_id,
            "source_document": self.source_document,
            "source_locator": self.source_locator,
            "page": self.page,
            "quote_present": self.quote_present,
            "quote_verified": self.quote_verified,
            "is_operative": self.is_operative,
            "model_applicable": self.model_applicable,
            "notes": list(self.notes),
        }
