"""JSON-backed parameter registry store (P3).

Append-first provenance store: every mutation produces a revision entry, so
raw provenance is never lost. Values enter only via ``upsert`` called by
deterministic code paths; the LLM can only propose ``ValueCandidate``
objects which must pass deterministic validation before upsert (rule 10).
"""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import ParameterRecord, ReviewState, ValueEntry, sha256_text


@dataclass
class ValueCandidate:
    """Proposal coming from an extraction pipeline (LLM-assisted or not)."""

    canonical_id: str
    payload: dict[str, Any]
    validation_summary: dict[str, Any]
    proposed_by: str  # "llm:<provider>[:<model>]" or "deterministic" or "user"

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "payload": self.payload,
            "validation_summary": self.validation_summary,
            "proposed_by": self.proposed_by,
        }


ERROR = -1


class RegistryStore:
    """File-backed parameter registry.

    Layout:
      <root>/registry.json          current records
      <root>/revisions.jsonl        append-only provenance of every change
      <root>/rejected.jsonl         proposals rejected by validation/review
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.registry_path = self.root / "registry.json"
        self.revisions_path = self.root / "revisions.jsonl"
        self.rejected_path = self.root / "rejected.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, ParameterRecord] = {}
        if self.registry_path.exists():
            for rec in json.loads(self.registry_path.read_text()):
                self._records[rec["canonical_id"]] = _record_from_dict(rec)

    # -- basic access -------------------------------------------------
    def __contains__(self, canonical_id: str) -> bool:
        return canonical_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def keys(self) -> list[str]:
        return sorted(self._records)

    def get(self, canonical_id: str) -> ParameterRecord:
        return self._records[canonical_id]

    def all_records(self) -> list[ParameterRecord]:
        return [self._records[k] for k in sorted(self._records)]

    def conflicts(self) -> dict[str, list[ValueEntry]]:
        return {
            k: self._records[k].conflicts for k in sorted(self._records)
        }

    # -- mutation (versioned) -----------------------------------------
    def upsert(self, record: ParameterRecord, actor: str, note: str) -> None:
        prev = self._records.get(record.canonical_id)
        if prev is not None:
            self._append_revision(previous=prev.to_dict(), actor=actor, note=note)
        self._records[record.canonical_id] = copy.deepcopy(record)
        self._flush()

    def _append_revision(
        self,
        previous: dict[str, Any] | None,
        actor: str,
        note: str,
    ) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "note": note,
        }
        if previous is not None:
            entry["previous"] = previous
        with self.revisions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def log_rejected(self, candidate: ValueCandidate, reason: str) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            **candidate.to_dict(),
        }
        with self.rejected_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def _flush(self) -> None:
        tmp = self.registry_path.with_suffix(".tmp")
        payload = [self._records[k].to_dict() for k in sorted(self._records)]
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
        shutil.move(str(tmp), str(self.registry_path))

    # -- helper -------------------------------------------------------
    def proof_of_content(self) -> str:
        """Content hash of the current registry for reproducibility records."""
        payload = [self._records[k].to_dict() for k in sorted(self._records)]
        return sha256_text(json.dumps(payload, sort_keys=True))


def _record_from_dict(d: dict[str, Any]) -> ParameterRecord:
    from .model import ParameterStatus

    rec = ParameterRecord(
        canonical_id=d["canonical_id"],
        pybamm_names=list(d["pybamm_names"]),
        pybop_mapping=d["pybop_mapping"],
        definition=d["definition"],
        value=d["value"],
        value_unit=d["value_unit"],
        normalized_value=d["normalized_value"],
        normalized_value_unit=d["normalized_value_unit"],
        status=ParameterStatus(d["status"]),
        source_id=d["source_id"],
        source_location=d["source_location"],
        evidence=None,
        conditions=d["conditions"],
        method=d["method"],
        reported_uncertainty=d["reported_uncertainty"],
        validation_state=ReviewState(d["validation_state"]),
        compatibility=d["compatibility"],
        conflicts=[],
        notes=list(d.get("notes", [])),
    )
    if d.get("evidence"):
        rec.evidence = _value_from_dict(d["evidence"])
    rec.conflicts = [_value_from_dict(c) for c in d.get("conflicts", [])]
    return rec


def _value_from_dict(d: dict[str, Any]) -> ValueEntry:
    from .model import ParameterStatus, SourceRef

    src = SourceRef(
        document_id=d["source"]["document_id"],
        title=d["source"].get("title"),
        doi_or_url=d["source"].get("doi_or_url"),
        locator=d["source"].get("locator"),
        page=d["source"].get("page"),
        char_start=d["source"].get("char_start"),
        char_end=d["source"].get("char_end"),
        quote=d["source"].get("quote"),
    )
    return ValueEntry(
        value=d["value"],
        unit=d["unit"],
        source=src,
        kind=ParameterStatus(d["kind"]),
        reported_uncertainty=d.get("reported_uncertainty"),
        uncertainty_note=d.get("uncertainty_note"),
        conditions=d.get("conditions", {}),
        method=d.get("method"),
        context=d.get("context"),
        review_state=ReviewState(d.get("review_state", "NEEDS_REVIEW")),
        review_reason=d.get("review_reason"),
    )
