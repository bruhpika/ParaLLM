"""Deterministic scientific validation of parameter extractions (P3, Part E).

Every check is a pure function over the extracted payload + registry +
document store; nothing here depends on the LLM's judgement (rule 10).
Three review states are supported: ACCEPTED / NEEDS_REVIEW / REJECTED.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..registry import units as units_mod
from ..registry.store import RegistryStore
from ..registry.textnorm import ascii_fold

# plausible ranges per canonical-id substring, in canonical units
PLAUSIBILITY_RANGES: dict[str, tuple[float, float, str]] = {
    "volume_fraction": (0.0, 1.0, "fraction"),
    "porosity": (0.0, 1.0, "fraction"),
    "particle_diffusivity": (1e-17, 1e-9, "m2.s-1"),
    "diffusivity": (1e-17, 1e-9, "m2.s-1"),
    "max_concentration": (1e3, 1e5, "mol.m-3"),
    "maximum_concentration": (1e3, 1e5, "mol.m-3"),
    "initial_concentration": (1e2, 1e5, "mol.m-3"),
    "particle_radius": (1e-8, 1e-3, "m"),
    "thickness": (1e-7, 1e-2, "m"),
    "conductivity": (1e-4, 1e9, "S.m-1"),
    "temperature": (150.0, 450.0, "K"),
    "capacity": (1e-3, 1e3, "A.h"),
    "voltage": (0.0, 6.0, "V"),
    "ocp": (0.0, 6.0, "V"),
    "exchange_current": (1e-3, 1e7, "A.m-2"),
    "reaction_rate": (1e-12, 1e2, "A.m-2.(m3.mol-1)^1.5"),
    "transference": (0.0, 1.0, "dimensionless"),
    "bruggeman": (0.0, 6.0, "dimensionless"),
    "activation_energy": (1e2, 1e6, "J.mol-1"),
}

TEMP_RANGE_CHEN2020_K = (273.15, 333.15)


@dataclass
class CheckResult:
    name: str
    level: str  # "ok" | "warn" | "fail"
    detail: str


@dataclass
class ReviewReport:
    checks: list[CheckResult] = field(default_factory=list)
    state: str = "NEEDS_REVIEW"
    reasons: list[str] = field(default_factory=list)

    def add(self, name: str, level: str, detail: str) -> None:
        self.checks.append(CheckResult(name, level, detail))
        if level == "fail":
            self.reasons.append(f"{name}: {detail}")
        elif level == "warn":
            self.reasons.append(f"{name}: {detail}")

    def finalize(self) -> "ReviewReport":
        levels = {c.level for c in self.checks}
        if "fail" in levels:
            self.state = "REJECTED"
        elif "warn" in levels:
            self.state = "NEEDS_REVIEW"
        else:
            self.state = "ACCEPTED"
        return self


# --------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------
def check_value_unit(payload: dict[str, Any]) -> tuple[str, str, float]:
    """Validate value/unit and return (canonical_unit, canonical_value, factor).

    Raises ValueError on unparseable values; KeyError on unknown units.
    """
    value = payload["value"]
    unit = payload.get("unit") or "dimensionless"
    if isinstance(value, str):
        value = float(value)
    if units_mod.is_exchange_current_reaction_rate_unit(unit):
        return "A.m-2.(m3.mol-1)^1.5", float(value), 1.0
    canonical, factor = units_mod.to_canonical(unit)
    return canonical, float(value) * factor, factor


def _plausibility_family(param_name: str, canonical_id: str | None) -> str | None:
    probe = (canonical_id or param_name or "").lower().replace(" ", "_")
    for key in PLAUSIBILITY_RANGES:
        if key in probe:
            return key
    return None


def check_plausibility(
    payload: dict[str, Any], canonical_id: str | None
) -> tuple[str, str]:
    family = _plausibility_family(payload.get("parameter_name", ""), canonical_id)
    if family is None:
        return "warn", "no plausibility range defined for this parameter family"
    lo, hi, expected_unit = PLAUSIBILITY_RANGES[family]
    try:
        canonical_unit, canonical_value, _ = check_value_unit(payload)
    except (ValueError, KeyError) as exc:
        return "fail", f"value/unit unparseable: {exc}"
    if canonical_unit != expected_unit and not (
        expected_unit == "dimensionless" and canonical_unit in ("dimensionless", "fraction")
    ):
        return (
            "fail",
            f"unit mismatch for {family}: got {canonical_unit}, expected {expected_unit}",
        )
    if not (lo <= canonical_value <= hi):
        return (
            "fail",
            f"value {canonical_value:g} {canonical_unit} outside plausible range "
            f"[{lo:g}, {hi:g}] for {family}",
        )
    return "ok", f"value plausible for {family} ({lo:g}..{hi:g} {expected_unit})"


def check_conditions(payload: dict[str, Any]) -> tuple[str, str]:
    problems = []
    temp = payload.get("temperature")
    if temp is None:
        problems.append("temperature missing")
    else:
        t = float(temp)
        if not (TEMP_RANGE_CHEN2020_K[0] <= t <= TEMP_RANGE_CHEN2020_K[1]):
            problems.append(
                f"temperature {t:g} K outside Chen2020 experimental range "
                f"{TEMP_RANGE_CHEN2020_K[0]:g}-{TEMP_RANGE_CHEN2020_K[1]:g} K"
            )
    cfg = payload.get("cell_config")
    if not cfg or cfg == "UNRESOLVED":
        problems.append("cell configuration missing")
    if not problems:
        return "ok", "conditions complete"
    level = "fail" if any("outside" in p for p in problems) else "warn"
    return level, "; ".join(problems)


def check_definition(payload: dict[str, Any]) -> tuple[str, str]:
    d = payload.get("definition")
    if not d or d == "UNRESOLVED":
        return "warn", "physical definition not resolved"
    return "ok", "definition present"


def check_provenance(
    payload: dict[str, Any], doc_texts: dict[str, str]
) -> tuple[str, str]:
    """Verify the extraction's source exists and its quote is real.

    This is the fabrication guard: a quote that cannot be found in the
    archived source document is a fatal finding.
    """
    src = payload.get("source")
    if not isinstance(src, dict):
        return "fail", "source missing"
    doc_id = src.get("document_id")
    if not doc_id:
        return "fail", "source.document_id missing"
    if doc_id not in doc_texts:
        return "fail", f"source document {doc_id!r} not in the document store"
    quote = src.get("quote")
    if quote:
        if ascii_fold(quote).strip() not in ascii_fold(doc_texts[doc_id]):
            return "fail", "quote not found in archived source (possible fabrication)"
    else:
        return "warn", "no verbatim quote recorded with the extraction"
    return "ok", "quote verified against the archived source"


def check_qualifier(payload: dict[str, Any]) -> tuple[str, str]:
    q = payload.get("qualifier")
    if q == "fitted":
        return (
            "ok",
            "fitted/calibrated quantity - must NOT be recorded as a direct "
            "experimental measurement",
        )
    if q in ("measured", "calculated", "assumed"):
        return "ok", f"qualifier {q}"
    return "warn", "qualifier unknown: measurement/estimation method unresolved"


def detect_conflict(
    payload: dict[str, Any],
    store: RegistryStore,
    rel_tol: float = 0.05,
) -> tuple[str, str]:
    """Compare an extraction against the registry's operative value.

    Disagreement is a warning that preserves both values (never a silent
    overwrite): the registry keeps conflicting literature values.
    """
    name = payload.get("parameter_name", "")
    match = None
    for rec in store.all_records():
        if rec.pybamm_names and any(
            name.lower() in pn.lower() or pn.lower() in name.lower()
            for pn in rec.pybamm_names
        ):
            match = rec
            break
    if match is None:
        return "warn", "extraction does not map to any registry parameter"
    try:
        _, val, _ = check_value_unit(payload)
    except (ValueError, KeyError) as exc:
        return "fail", f"extraction value/unit unparseable: {exc}"
    cur = match.value
    if callable(cur) or not isinstance(cur, (int, float)):
        return "ok", f"maps to function-valued record {match.canonical_id}"
    if cur == 0:
        rel = abs(val)
    else:
        rel = abs(val - float(cur)) / abs(float(cur))
    if rel > rel_tol:
        return (
            "warn",
            f"value conflicts with registry record {match.canonical_id} "
            f"(registry {cur:g} vs extracted {val:g}, rel diff {rel:.2%}); "
            "both preserved",
        )
    return "ok", f"consistent with registry record {match.canonical_id}"


def check_pybamm_mapping(
    payload: dict[str, Any],
    store: RegistryStore,
    installed_names: list[str] | None = None,
) -> tuple[str, str]:
    name = payload.get("parameter_name", "")
    for rec in store.all_records():
        if rec.pybamm_names and any(
            name.lower() in pn.lower() or pn.lower() in name.lower()
            for pn in rec.pybamm_names
        ):
            if installed_names is not None:
                missing = [n for n in rec.pybamm_names if n not in installed_names]
                if missing:
                    return "fail", f"registry pybamm name not in installed set: {missing}"
            return "ok", f"mapped to {rec.canonical_id} ({rec.pybamm_names[0]})"
    return "warn", "no PyBaMM mapping for this parameter name"


# --------------------------------------------------------------------------
# review driver
# --------------------------------------------------------------------------
def review_candidate(
    payload: dict[str, Any],
    store: RegistryStore,
    doc_texts: dict[str, str],
    installed_names: list[str] | None = None,
    schema_ok: bool = True,
    schema_reason: str = "ok",
) -> ReviewReport:
    report = ReviewReport()
    if not schema_ok:
        report.add("schema", "fail", f"structured output invalid: {schema_reason}")
        return report.finalize()
    report.add("schema", "ok", "structured output valid")
    for fn, args in (
        (check_definition, (payload,)),
        (check_conditions, (payload,)),
        (check_qualifier, (payload,)),
        (check_provenance, (payload, doc_texts)),
    ):
        level, detail = fn(*args)
        report.add(fn.__name__, level, detail)
    try:
        canonical_unit, canonical_value, _ = check_value_unit(payload)
        report.add(
            "unit_conversion",
            "ok",
            f"converted to {canonical_value:g} {canonical_unit}",
        )
    except (ValueError, KeyError) as exc:
        report.add("unit_conversion", "fail", str(exc))
        return report.finalize()
    level, detail = check_plausibility(payload, None)
    report.add("physical_plausibility", level, detail)
    level, detail = detect_conflict(payload, store)
    report.add("conflicting_evidence", level, detail)
    level, detail = check_pybamm_mapping(payload, store, installed_names)
    report.add("pybamm_mapping", level, detail)
    return report.finalize()
