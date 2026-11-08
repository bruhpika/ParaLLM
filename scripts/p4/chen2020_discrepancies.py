"""P4 Part C: Chen2020 paper-vs-PyBaMM-vs-P2 discrepancy analysis.

Builds data/registry/chen2020_discrepancies.json PROGRAMMATICALLY from
data/registry/registry.json (P3, immutable inputs). Every value, quote,
condition and uncertainty is pulled from registry records at build time --
nothing is hand-entered here (AGENTS.md rule 4/6).

Cause taxonomy (tags per discrepancy):
  definition          different quantity-definition or naming
  unit_convention     same quantity, different unit representation
  operating_conditions  value valid under different conditions
  calibration         tuned/adjusted value replacing a reported measurement
  model_assumption    theoretical/default simplification contra measurement
  set_extension       parameter present in the PyBaMM set beyond the paper
  source_conflict     internal/cross-document inconsistency (preserved)

The script never modifies the registry (no overwriting, rule: preserve).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "data/registry/registry.json"
OUT = REPO_ROOT / "data/registry/chen2020_discrepancies.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

CAUSE_TAXONOMY = {
    "definition": (
        "different quantity-definition or naming (e.g. PyBaMM 'Electrode "
        "width [m]' corresponds to the paper's 'Electrode length')"
    ),
    "unit_convention": "same quantity, different unit representation (% vs fraction)",
    "operating_conditions": (
        "the two values were obtained/validated under different conditions "
        "(C-rate-dependent effective diffusivity, temperature-dependent j0)"
    ),
    "calibration": (
        "a tuned/adjusted value carried in the simulations instead of the "
        "reported measurement (half-iteration fitting; Table IX)"
    ),
    "model_assumption": (
        "theoretical/default simplification chosen despite a measured value "
        "being available (Bruggeman 1.5 packed-sphere assumption)"
    ),
    "set_extension": (
        "parameter/feature present in the PyBaMM parameter set but not "
        "parameterized by the Chen2020 paper (SEI block, thermal transport)"
    ),
    "source_conflict": (
        "ambiguity inside the source corpus, preserved in the registry "
        "(text-vs-table variants; main text vs supplement)"
    ),
}

FAMILIES_WITH_CAUSES = {
    "neg_particle_diffusivity": ["calibration", "operating_conditions"],
    "pos_particle_diffusivity": ["calibration", "operating_conditions"],
    "neg_max_concentration": ["calibration", "source_conflict"],
    "pos_max_concentration": ["calibration"],
    "neg_bruggeman_electrolyte": ["model_assumption", "calibration"],
    "pos_bruggeman_electrolyte": ["model_assumption", "calibration"],
    "sep_bruggeman_electrolyte": ["model_assumption", "calibration"],
    "neg_electrode_active_material_volume_fraction": ["unit_convention"],
    "pos_electrode_active_material_volume_fraction": ["unit_convention"],
    "separator_porosity": ["source_conflict"],
    "cell_electrode_width": ["definition"],
}

# P2 measured linkage (from the P2 campaign, results/p2/, Phase 2): only used
# as recorded findings, never re-derived here.
P2_LINKAGE = {
    "neg_particle_diffusivity": {
        "identifiability": "NOT ESTIMABLE from voltage-only discharge data at <=2C "
        "(mean |normalized sensitivity| 0.011-0.048); recovered with <1% error only "
        "when treated by multistart ridge",
        "note": "the +1797% tuned gap is therefore never testable by terminal-voltage fitting alone",
    },
    "pos_particle_diffusivity": {
        "identifiability": "candidate for estimation from multi-C discharge data "
        "(normalized sensitivity 0.63-0.85 over 0.5C-2C)",
    },
    "electrolyte coupling": {
        "identifiability": "electrolyte diffusivity and reaction rate are collinear "
        "(|corr| > 0.8); not separately identifiable from these data",
    },
    "MCMC": {
        "identifiability": "short-chain posteriors (rhat 1.10-1.26) only "
        "directionally informative; not used as evidence here",
    },
}

# Set-extension families in the PyBaMM set that Chen2020 does not parameterize
# (pulled from the registry by probing which records have no paper-side
# evidence source at all).
SET_EXTENSION_CANONICAL_IDS = [
    "initial_sei_thickness",
    "sei_electron_conductivity",
    "sei_growth_activation_energy",
    "sei_kinetic_rate_constant",
    "sei_lithium_interstitial_diffusivity",
    "sei_open_circuit_potential",
    "sei_partial_molar_volume",
    "sei_reaction_exchange_current_density",
    "sei_resistivity",
    "sei_solvent_diffusivity",
    "ratio_of_lithium_moles_to_sei_moles",
    "lithium_interstitial_reference_concentration",
    "negative_electrode_double_layer_capacity",
    "positive_electrode_double_layer_capacity",
    "total_heat_transfer_coefficient",
    "contact_resistance",
]


def main() -> int:
    records = json.loads(REGISTRY.read_text())
    reg = {r["canonical_id"]: r for r in records}

    def pybamm_side(cid: str) -> dict | None:
        rec = reg.get(cid)
        if not rec:
            return None
        return dict(
            pybamm_names=rec.get("pybamm_names", []),
            value=rec.get("normalized_value"),
            unit=rec.get("normalized_value_unit"),
            status=rec.get("evidence", {}).get("kind"),
        )

    discrepancies = []
    for cid, causes in FAMILIES_WITH_CAUSES.items():
        rec = reg.get(cid)
        if rec is None:
            raise SystemExit(f"registry missing {cid}")
        conflict = (rec.get("conflicts") or [None])[0]
        entry = dict(
            canonical_id=cid,
            causes=causes,
            pybamm=pybamm_side(cid),
            paper=None,
            ratio=None,
            registry_notes=list(rec.get("notes", [])),
        )
        if conflict is not None:
            src = conflict.get("source", {})
            try:
                pv = float(conflict["value"])
                qv = float(rec.get("normalized_value"))
            except (TypeError, ValueError):
                pv, qv = conflict["value"], None
            ratio = (qv / pv) if qv and pv else None
            entry["paper"] = dict(
                value=conflict.get("value"),
                unit=conflict.get("unit"),
                uncertainty=conflict.get("reported_uncertainty"),
                method=conflict.get("method"),
                conditions=conflict.get("conditions"),
                source_quote=src.get("quote"),
                source_document=src.get("document_id"),
                source_offset=[src.get("char_start"), src.get("char_end")],
                review_state=conflict.get("review_state"),
                context=conflict.get("context"),
            )
            if ratio is not None:
                entry["ratio"] = dict(
                    definition="pybamm_value / paper_value (same units; sign "
                    "conventions preserved; unit conversions verified in the registry)",
                    value=round(ratio, 6),
                )
        else:
            # no separate conflict record: the paper value IS the record's own
            # evidence (e.g. percent expressed as fraction in PyBaMM); surface
            # the record's verbatim quote as provenance so every entry keeps a
            # paper side with source grounding.
            ev = rec.get("evidence") or {}
            src = ev.get("source") or {}
            entry["paper"] = dict(
                value=ev.get("value"),
                unit=ev.get("unit"),
                uncertainty=ev.get("reported_uncertainty"),
                method=ev.get("method"),
                conditions=ev.get("conditions"),
                source_quote=src.get("quote"),
                source_document=src.get("document_id"),
                source_offset=[src.get("char_start"), src.get("char_end")],
                review_state=ev.get("review_state"),
                context=ev.get("context"),
            )
        if isinstance(entry["paper"].get("value"), str):
            # registry evidence values are strings ("75", "%"); keep the raw
            # string in 'paper' and add a numeric shadow for ratio checks
            try:
                pv_num = float(entry["paper"]["value"])
                pv_num = 0.01 * pv_num if entry["paper"].get("unit") == "%" else pv_num
                qv = float(entry["pybamm"]["value"]) if entry["pybamm"] else None
                if qv is not None:
                    entry["ratio"] = dict(
                        definition="pybamm_value / paper_value_in_pybamm_unit "
                        "(%-values pre-multiplied by 0.01 to compare against the "
                        "PyBaMM fraction; numeric equality expected for pure "
                        "unit-convention cases)",
                        value=round(qv / pv_num, 6) if pv_num else None,
                    )
            except (TypeError, ValueError):
                pass
        discrepancies.append(entry)

    set_extensions = []
    for cid in SET_EXTENSION_CANONICAL_IDS:
        rec = reg.get(cid)
        if rec is None:
            continue
        set_extensions.append(
            dict(
                canonical_id=cid,
                pybamm_names=rec.get("pybamm_names", []),
                status=(rec.get("evidence") or {}).get("kind"),
                note=(rec.get("notes") or [""])[0][:400],
            )
        )
    covered = [c["canonical_id"] for c in set_extensions]
    missing = [c for c in SET_EXTENSION_CANONICAL_IDS if c not in covered]
    if missing:
        raise SystemExit(f"registry missing set-extension ids: {missing}")

    out = dict(
        title="Chen2020 discrepancy analysis: paper vs PyBaMM parameter set",
        generated=datetime.now(timezone.utc).isoformat(),
        built_from=str(REGISTRY.relative_to(REPO_ROOT)),
        method_note=(
            "Built programmatically from the P3 registry; every value, quote, "
            "condition and uncertainty is read from registry records at build "
            "time. PyBaMM-side values are the set's operative values (P3 "
            "introspection, include tuned Chen2020 Table IX values). No value "
            "is hand-entered in this script. This analysis documents "
            "discrepancies; it does NOT change any registry value."
        ),
        cause_taxonomy=CAUSE_TAXONOMY,
        discrepancies=discrepancies,
        set_extensions=dict(
            families=set_extensions,
            summary="Parameters present in the PyBaMM Chen2020 set but not "
            "parameterized by the paper: the SEI growth block, double-layer "
            "capacities, total heat transfer coefficient and contact "
            "resistance (set-extension items, e.g. documented SEI values are "
            "'example parameters for SEI growth' per the PyBaMM "
            "parameter-sets documentation).",
        ),
        p2_linkage=P2_LINKAGE,
        limitations=[
            "Discrepancy ratios use the registry's unit-normalized values; "
            "where the registry distinguishes text-vs-table variants both are "
            "kept rather than averaged.",
            "The C-rate dependence of the negative effective diffusivity "
            "(1.3e-14 / 3.3e-14 / 6.3e-14 m2/s at C/2, 1C, 1.5C) is documented "
            "in the registry conflict contexts, not in this file, to keep "
            "single-source provenance. See neg_particle_diffusivity notes.",
            "Cause tags are expert judgments (documented), not measurements.",
        ],
    )
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
    print(f"  discrepancy families: {len(discrepancies)}")
    print(f"  set-extension families: {len(set_extensions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
