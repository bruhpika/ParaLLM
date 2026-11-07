"""Canonical-id <-> PyBaMM-name <-> PyBOP mapping helpers (P3, Part G).

No upstream package is modified; all PyBOP/PyBaMM objects are created
locally from registry data and verified against the installed versions.
"""

from __future__ import annotations

from typing import Any

from .model import ParameterRecord
from .store import RegistryStore


def build_pybamm_name_index(store: RegistryStore) -> dict[str, str]:
    """Map every PyBaMM parameter name to its canonical id."""
    index: dict[str, str] = {}
    for rec in store.all_records():
        for name in rec.pybamm_names:
            index[name] = rec.canonical_id
    return index


def canonical_for_pybamm(store: RegistryStore, pybamm_name: str) -> str | None:
    """Return the canonical registry id for a PyBaMM parameter name.

    ``None`` when the name is not covered by any registry record.
    """
    return build_pybamm_name_index(store).get(pybamm_name)


def pybop_declarations(
    store: RegistryStore,
    canonical_ids: list[str] | None = None,
    include_unrecommended: bool = False,
) -> list[dict[str, Any]]:
    """Return pybop.Parameter declaration specs for selected registry records.

    Each spec: {canonical_id, pybamm_name, bounds, initial_guesses, notes}.
    Function-valued parameters are never included (a scalar pybop.Parameter
    cannot replace a function entry).
    """
    out: list[dict[str, Any]] = []
    for rec in store.all_records():
        if canonical_ids is not None and rec.canonical_id not in canonical_ids:
            continue
        m = rec.pybop_mapping or {}
        if not m.get("applicable"):
            continue
        if not m.get("recommended", True) and not include_unrecommended:
            continue
        if not rec.pybamm_names:
            continue
        if rec.compatibility.get("function_valued"):
            continue
        out.append(
            dict(
                canonical_id=rec.canonical_id,
                pybamm_name=rec.pybamm_names[0],
                bounds=m.get("bounds"),
                initial_guesses=m.get("initial_guesses"),
                notes=m.get("notes"),
            )
        )
    return out


def approved_pair(store: RegistryStore) -> tuple[ParameterRecord, ParameterRecord]:
    """Return the P2-approved estimation pair (neg, pos volume fractions)."""
    return (
        store.get("neg_electrode_active_material_volume_fraction"),
        store.get("pos_electrode_active_material_volume_fraction"),
    )


def overlay_to_parameter_values(
    store: RegistryStore,
    values: dict[str, Any],
) -> dict[str, Any]:
    """Produce a PyBaMM ParameterValues-style overlay from registry records.

    ``values`` maps PyBaMM names to current ParameterValues entries. The
    returned dict contains ONLY names whose registry record carries a scalar
    operative value that differs from ``values``; it never mutates the input
    and never fabricates values (rule 6).
    """
    overlay: dict[str, Any] = {}
    for rec in store.all_records():
        for name in rec.pybamm_names:
            if name not in values:
                continue
            current = values[name]
            if callable(current):
                continue
            if callable(rec.value):
                continue
            try:
                if float(rec.value) != float(current):
                    overlay[name] = rec.value
            except (TypeError, ValueError):
                continue
    return overlay
