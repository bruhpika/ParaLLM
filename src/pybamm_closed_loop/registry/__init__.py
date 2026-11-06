"""Parameter registry and provenance layer (P3).

Heavy imports (pybamm) happen lazily so environments without pybamm can
still import the data model and units helpers.
"""

from __future__ import annotations

__all__ = [
    "ParameterRecord",
    "ParameterStatus",
    "ReviewState",
    "SourceRef",
    "ValueEntry",
    "RegistryStore",
    "ValueCandidate",
]


def __getattr__(name: str):
    if name in ("ParameterRecord", "ParameterStatus", "ReviewState", "SourceRef", "ValueEntry"):
        from . import model

        return getattr(model, name)
    if name in ("RegistryStore", "ValueCandidate"):
        from . import store

        return getattr(store, name)
    raise AttributeError(name)
