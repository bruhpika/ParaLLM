"""Datasets audit + PyProBE linkage (P3, Parts F/G)."""

from __future__ import annotations

__all__ = ["DatasetCandidate", "CompatibilityVerdict", "AuditRequirement"]


def __getattr__(name: str):
    from . import audit

    return getattr(audit, name)
