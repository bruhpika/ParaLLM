"""Assembly report: turn the parameter registry into decisions for a target.

``assemble`` is the entry point of the assembly layer: it takes the registry
records (each with an operative value and preserved conflicts), a target cell
specification and a rubric, and returns per-parameter dossiers plus a
set-level summary.

Nothing here writes to the registry: the assembly layer proposes, the human
approval gate disposes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .dossier import dossier, to_markdown
from .gate import ApprovalGate
from .resolve import Resolution, resolve_parameter
from .rubric import Rubric
from .schema import (
    STATUS_TO_METHOD,
    CandidateValue,
    ConditionFacts,
    Decision,
    MethodClass,
    TargetSpecification,
)

_METHOD_KEYWORDS: tuple[tuple[MethodClass, tuple[str, ...]], ...] = (
    (MethodClass.MEASURED, ("measured", "measurement", "instrument", "vernier", "sem ", "fib", "tga", "eis")),
    (MethodClass.FITTED, ("fit", "regression", "least squares", "inverse")),
    (MethodClass.CALCULATED, ("calculated", "computed", "derived from", "equation")),
    (MethodClass.ASSUMED, ("assumed", "default", "theoretical", "typical")),
)


def infer_method_class(status: str | None, method: str | None) -> MethodClass:
    """Map (registry status, method text) to a method class.

    The registry status is authoritative when it carries the meaning
    (ASSUMED/CALCULATED/CALIBRATED); LITERATURE_DERIVED values are classified
    from the method text, and stay UNKNOWN when the text is not decisive.
    """
    if status:
        mapped = STATUS_TO_METHOD.get(status)
        if mapped is not None and mapped is not MethodClass.UNKNOWN:
            return mapped
    text = (method or "").lower()
    for cls, keys in _METHOD_KEYWORDS:
        if any(k in text for k in keys):
            return cls
    return MethodClass.UNKNOWN


def _callable_value(record: Mapping[str, Any]) -> bool:
    value = record.get("value")
    return callable(value) or (isinstance(value, str) and "<function" in value)


def candidates_from_record(record: Mapping[str, Any]) -> list[CandidateValue]:
    """Build the candidate list for one registry record (operative + conflicts)."""
    canonical_id = record.get("canonical_id", "")
    conditions = record.get("conditions") or {}
    evidence = record.get("evidence") or {}
    source = evidence.get("source") or {}
    mapping = record.get("pybop_mapping") or {}

    operative = CandidateValue(
        canonical_id=canonical_id,
        value=record.get("value"),
        unit=record.get("value_unit"),
        canonical_value=record.get("normalized_value"),
        canonical_unit=record.get("normalized_value_unit"),
        method_class=infer_method_class(record.get("status"), record.get("method")),
        method=record.get("method"),
        status=record.get("status"),
        conditions=ConditionFacts.from_mapping(conditions),
        source_id=record.get("source_id"),
        source_document=source.get("document_id") or record.get("source_id"),
        source_locator=source.get("locator"),
        page=source.get("page") if isinstance(source.get("page"), int) else None,
        quote=source.get("quote"),
        quote_present=bool(source.get("quote")),
        quote_verified=None,
        is_operative=True,
        model_applicable=mapping.get("applicable"),
        model_note=mapping.get("notes"),
    )
    if _callable_value(record):
        operative.model_applicable = False
        operative.model_note = "function-valued parameter; not declarable as a scalar"

    out = [operative]
    for conflict in record.get("conflicts") or []:
        csource = conflict.get("source") or {}
        out.append(
            CandidateValue(
                canonical_id=canonical_id,
                value=conflict.get("value"),
                unit=conflict.get("unit"),
                canonical_value=conflict.get("normalized_value"),
                canonical_unit=conflict.get("normalized_value_unit"),
                method_class=infer_method_class(conflict.get("kind"), conflict.get("method")),
                method=conflict.get("method"),
                status=conflict.get("kind"),
                conditions=ConditionFacts.from_mapping(conflict.get("conditions") or {}),
                source_id=csource.get("document_id") or record.get("source_id"),
                source_document=csource.get("document_id") or record.get("source_id"),
                source_locator=csource.get("locator"),
                page=csource.get("page") if isinstance(csource.get("page"), int) else None,
                quote=csource.get("quote"),
                quote_present=bool(csource.get("quote")),
                quote_verified=None,
                is_operative=False,
                model_applicable=mapping.get("applicable"),
            )
        )
    return out


@dataclass
class AssemblyReport:
    """Set-level result of an assembly run."""

    target: TargetSpecification
    rubric_version: str
    dossiers: list[dict[str, Any]] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)

    # -- summary ---------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for d in self.dossiers:
            counts[d["decision"]] = counts.get(d["decision"], 0) + 1
        conflicts = [d for d in self.dossiers if d["conflict"]]
        return {
            "target": self.target.to_dict(),
            "rubric_version": self.rubric_version,
            "n_parameters": len(self.dossiers),
            "decisions": dict(sorted(counts.items())),
            "n_conflicts": len(conflicts),
            "same_source_conflicts": sum(
                1 for d in conflicts if d["conflict_class"] == "same_source"
            ),
            "cross_source_conflicts": sum(
                1 for d in conflicts if d["conflict_class"] == "cross_source"
            ),
            "n_review_required": sum(1 for d in self.dossiers if d["review_required"]),
            "n_preserved_alternatives": sum(len(d["alternatives"]) for d in self.dossiers),
            "n_rejected_candidates": sum(len(d["rejected"]) for d in self.dossiers),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "parameters": self.dossiers,
        }

    def to_markdown(self) -> str:
        return to_markdown(self.dossiers, title=f"PARALLM parameter assembly — {self.target.target_id}")

    # -- export ----------------------------------------------------------
    def pybamm_export(self, gate: ApprovalGate | None = None) -> dict[str, Any]:
        """Approved parameters as a PyBaMM-style {name: value} mapping.

        Only parameters with a recorded human approval are exported; the
        approval record is the audit trail (rule 10).
        """
        out: dict[str, Any] = {}
        for d in self.dossiers:
            if gate is not None and not gate.is_approved(d["parameter"]):
                continue
            if d["decision"] not in (Decision.USE.value, Decision.FIX.value):
                continue
            value = (d.get("selected") or {}).get("value")
            if value is None:
                continue
            out[d["parameter"]] = value
        return out


def assemble(
    records: Iterable[Mapping[str, Any]],
    target: TargetSpecification,
    rubric: Rubric,
) -> AssemblyReport:
    """Assemble decisions for every parameter in ``records``."""
    report = AssemblyReport(target=target, rubric_version=rubric.version)
    for record in records:
        canonical_id = record.get("canonical_id", "")
        candidates = candidates_from_record(record)
        resolution = resolve_parameter(canonical_id, candidates, target, rubric)
        report.resolutions.append(resolution)
        report.dossiers.append(dossier(resolution))
    return report
