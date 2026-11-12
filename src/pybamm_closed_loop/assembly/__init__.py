"""PARALLM assembly layer: applicability, conflict resolution and decisions.

The assembly layer answers the question a parameter set cannot answer on its
own: *for this cell and this protocol, which value should be used, why, what
were the alternatives, and who approved it?*

Design commitments:
- the LLM never enters the numeric decision path (decision D7);
- the rubric is hand-set and versioned; every decision records the rules that
  fired (decision D1);
- conflicts are preserved, never silently dropped;
- the human approval gate is mandatory (decision D6).
"""

from __future__ import annotations

from .dossier import dossier, to_markdown
from .gate import ApprovalGate, ApprovalRecord
from .report import AssemblyReport, assemble, candidates_from_record, infer_method_class
from .resolve import Resolution, resolve_parameter
from .rubric import DEFAULT_WEIGHTS, Dimension, Rubric, RubricOutcome, Rule
from .schema import (
    CandidateValue,
    ConditionFacts,
    Decision,
    MethodClass,
    TargetSpecification,
)

__all__ = [
    "ApprovalGate",
    "ApprovalRecord",
    "AssemblyReport",
    "CandidateValue",
    "ConditionFacts",
    "DEFAULT_WEIGHTS",
    "Decision",
    "Dimension",
    "MethodClass",
    "Resolution",
    "Rubric",
    "RubricOutcome",
    "Rule",
    "TargetSpecification",
    "assemble",
    "candidates_from_record",
    "dossier",
    "infer_method_class",
    "resolve_parameter",
    "to_markdown",
]
