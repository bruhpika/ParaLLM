"""Extraction evaluation benchmark (P3, Part H)."""

from __future__ import annotations

__all__ = ["BenchmarkItem", "GoldEntry", "load_items", "run_benchmark"]


def __getattr__(name: str):
    from . import benchmark

    return getattr(benchmark, name)
