"""Deterministic scientific validation layer (P3, Part E)."""

from __future__ import annotations

__all__ = ["ReviewReport", "CheckResult", "review_candidate"]


def __getattr__(name: str):
    from . import checks

    return getattr(checks, name)
