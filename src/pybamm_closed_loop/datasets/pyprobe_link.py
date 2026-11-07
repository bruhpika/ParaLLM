"""Deterministic PyProBE linkage for dataset auditing (P3, Part G).

Summarises experimental observations (polars-based, cycler-agnostic) and
extracts protocol metadata through PyProBE's own README processor. No
upstream code is modified; PyProBE is used as a library exactly as shipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import AuditRequirement, CompatibilityVerdict, DatasetCandidate, assess_candidate


def summarize_observations(parquet_path: str | Path) -> dict[str, Any]:
    """Numeric summary of an observation table (raw/processed data check)."""
    import polars as pl

    df = pl.read_parquet(str(parquet_path))
    facts: dict[str, Any] = {
        "path": str(parquet_path),
        "n_rows": df.height,
        "columns": list(df.columns),
    }
    for col, alias in (
        ("Voltage [V]", "voltage_v"),
        ("Current [A]", "current_a"),
        ("Capacity [Ah]", "capacity_ah"),
        ("Time [s]", "time_s"),
    ):
        if col in df.columns:
            s = df[col]
            facts[f"{alias}_min"] = float(s.min())
            facts[f"{alias}_max"] = float(s.max())
    facts["has_temperature"] = any("temp" in c.lower() for c in df.columns)
    return facts


def pyprobe_protocol_steps(readme_path: str | Path) -> dict[str, list[str]]:
    """Extract experiment titles and step strings via PyProBE's README processor.

    Step strings are PyBaMM experiment strings (per the README convention).
    """
    import pyprobe

    model = pyprobe.readme_processor.process_readme(str(readme_path))
    out: dict[str, list[str]] = {}
    for title, block in (model.experiment_dict or {}).items():
        steps: list[str] = []
        if isinstance(block, dict):
            raw_steps = block.get("Steps", {})
            if isinstance(raw_steps, dict):
                steps = [str(v) for _, v in sorted(raw_steps.items(), key=lambda kv: str(kv[0]))]
            elif isinstance(raw_steps, list):
                steps = [str(v) for v in raw_steps]
        out[str(title)] = steps
    return out


def audit_neware_sample(
    root: str | Path = "data/external/pyprobe_sample/neware",
) -> DatasetCandidate:
    """Build the audit record for the local Neware sample (ingestion test only)."""
    root = Path(root)
    facts = summarize_observations(root / "sample_data_neware.parquet")
    try:
        protocol = pyprobe_protocol_steps(root / "README.yaml")
    except Exception as exc:  # pragma: no cover - pyprobe-dependent
        protocol = {}
        protocol_error = str(exc)
    else:
        protocol_error = None
    steps_flat = [s for steps in protocol.values() for s in steps]
    candidate = DatasetCandidate(
        dataset_id="pyprobe-sample-neware-nmc622",
        title="PyProBE Neware sample dataset (ingestion demonstration)",
        source_url="https://github.com/pybamm-team/PyProBE-Data",
        doi_or_identifier=None,
        license=None,
        chemistry=(
            "NMC622 (per the P1 ecosystem audit and upstream PyProBE sample "
            "documentation; not stated in the local README.yaml)"
        ),
        cell_format="small-format laboratory cell (Neware cycler export)",
        nominal_capacity="~0.04 A.h (observed capacity range "
        f"{facts.get('capacity_ah_min', 0):.4f}-{facts.get('capacity_ah_max', 0):.4f} Ah)",
        temperature="not recorded in the observation table (UNRESOLVED)",
        c_rates="not labelled; currents observed "
        f"{facts.get('current_a_min', 0):.4g}-{facts.get('current_a_max', 0):.4g} A",
        voltage_limits=(
            f"observed {facts.get('voltage_v_min', 0):.4f}-"
            f"{facts.get('voltage_v_max', 0):.4f} V"
        ),
        protocol="README.yaml steps (PyBaMM experiment strings): "
        + "; ".join(steps_flat[:8])
        + (" ..." if len(steps_flat) > 8 else ""),
        metadata_completeness="protocol documented in README.yaml; cell identity/temperature/licensing metadata missing",
        observations=f"raw cycler export (parquet, {facts['n_rows']} rows) + xlsx original",
        notes=[
            "Explicitly an ingestion test dataset; NOT validation data for the "
            "LG M50 demonstrator (chemistry, format and scale all differ).",
        ],
    )
    if protocol_error:
        candidate.notes.append(f"pyprobe protocol extraction error: {protocol_error}")
    candidate.requirements = [
        AuditRequirement(
            "cell identity matches LG M50 / Chen2020 scope",
            "NMC622 small-format cell, ~40 mAh",
            "unmet",
            evidence="observation table capacity range + P1 audit",
        ),
        AuditRequirement(
            "nominal capacity ~5 A.h",
            "~0.04 A.h",
            "unmet",
            evidence=f"capacity range {facts.get('capacity_ah_min')}-{facts.get('capacity_ah_max')} Ah",
        ),
        AuditRequirement(
            "temperature 298.15 K recorded",
            "no temperature column in the observation table",
            "unmet",
            evidence="column list: " + ", ".join(facts["columns"]),
        ),
        AuditRequirement(
            "voltage window 2.5-4.2 V",
            f"{facts.get('voltage_v_min')}-{facts.get('voltage_v_max')} V observed",
            "unmet",
            evidence="observation table",
        ),
        AuditRequirement(
            "0.5C/1C/2C discharge protocol",
            "4 mA CC-CV charge + 20 mA discharge pulses (README.yaml steps)",
            "unmet",
            evidence="README.yaml",
        ),
        AuditRequirement(
            "protocol metadata documented",
            "README.yaml with PyBaMM experiment strings",
            "met",
            evidence="README.yaml present alongside raw data",
        ),
        AuditRequirement(
            "raw observations available",
            f"parquet ({facts['n_rows']} rows) + xlsx",
            "met",
            evidence="data/external/pyprobe_sample/neware/",
        ),
    ]
    verdict, missing = assess_candidate(candidate)
    candidate.verdict = (
        CompatibilityVerdict.INCOMPATIBLE
        if any(r.status == "unmet" for r in candidate.requirements[:5])
        else verdict
    )
    candidate.notes.append(f"assessed missing requirements: {missing}")
    return candidate
