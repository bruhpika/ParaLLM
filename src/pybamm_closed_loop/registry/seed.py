"""Seed the parameter registry from the installed PyBaMM Chen2020 set (P3).

Deterministic seeding only (no LLM involvement):

1. introspect the installed ``pybamm.ParameterValues("Chen2020")``;
2. attach Chen2020-paper provenance located in the archived article text
   (verbatim quotes are extracted from the archive at seed time, never
   retyped, so every quote is a real substring with exact char offsets);
3. preserve conflicts between paper-reported (measured) values and the
   tuned/assumed values carried by PyBaMM;
4. run arithmetic consistency checks for CALCULATED records.

Statuses follow scientific rule 5: USER_SUPPLIED / LITERATURE_DERIVED /
CALCULATED / ASSUMED / CALIBRATED / UNRESOLVED.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

from . import sources as S
from .model import (
    ParameterRecord,
    ParameterStatus as PS,
    ReviewState as RS,
    SourceRef,
    ValueEntry,
)
from .store import RegistryStore
from .textnorm import ascii_fold
from .units import is_exchange_current_reaction_rate_unit, to_canonical

RAW_DOC = (
    Path("data/raw_documents") / "chen2020_jes_167_080534"
    / "chen2020_jes_167_080534_fulltext.txt"
)

PYBAMM_DEFAULT_SOURCE_ID = "pybamm-26.8.0.0:chen2020-defaults"


# --------------------------------------------------------------------------
# quote extraction from the archived article text
# --------------------------------------------------------------------------
def extract_quote(text: str, probe: str, back: int = 220, fwd: int = 260) -> dict[str, Any]:
    """Return {quote, char_start, char_end} for the probe occurrence.

    The quote is the verbatim substring of ``text`` around the probe; the
    boundaries are line breaks or sentence-ish punctuation, and offsets are
    exact character offsets into ``text``. Raises ValueError if the probe is
    absent — never fabricates a location.
    """
    folded = ascii_fold(text)
    idx = folded.find(ascii_fold(probe))
    if idx < 0:
        raise ValueError(f"probe not found in archive: {probe!r}")
    start = idx
    end = idx + len(probe)
    # expand to sentence-ish boundaries within windows
    lo = max(0, idx - back)
    hi = min(len(text), idx + len(probe) + fwd)
    for j in range(idx, lo, -1):
        if text[j] in ".!?\n" and j + 1 < idx:
            start = j + 1
            break
    else:
        start = lo
    for j in range(idx + len(probe), hi):
        if text[j] in ".!?\n":
            end = j + 1
            break
    else:
        end = hi
    quote = text[start:end].strip()
    return {"quote": quote, "char_start": start, "char_end": end}


# --------------------------------------------------------------------------
# value/unit normalisation
# --------------------------------------------------------------------------
def normalize_value(value: float | str, unit_token: str | None) -> tuple[Any, str | None]:
    """Return (normalized_value, normalized_canonical_unit) for a value.

    Raises KeyError for unknown units (rule 6: never silently map).
    """
    if value is None:
        return None, None
    if unit_token in (None, "", "-", "--", "dimensionless"):
        return value, "dimensionless"
    if is_exchange_current_reaction_rate_unit(unit_token):
        return float(value), "A.m-2.(m3.mol-1)^1.5"
    canonical, factor = to_canonical(unit_token)
    if isinstance(value, str):
        return value, canonical
    return float(value) * factor, canonical


# --------------------------------------------------------------------------
# per-parameter provenance spec
# --------------------------------------------------------------------------
# keys:
#   pybamm       exact PyBaMM key, or None for paper-only parameters
#   definition   physical definition (written for this project)
#   paper        dict with the paper-reported value provenance
#   kind         status of the operative (PyBaMM-carried) value
#   pybop        PyBOP applicability mapping or None
#   notes        extra provenance notes
#   checks       (label, computed, target, reltol) arithmetic checks


def _paper(
    value: Any,
    unit: str,
    locator: str,
    probe: str | None = None,
    method: str | None = None,
    conditions: dict[str, Any] | None = None,
    uncertainty: float | None = None,
    uncertainty_note: str | None = None,
    kind: PS = PS.LITERATURE_DERIVED,
    context: str | None = None,
) -> dict[str, Any]:
    return dict(
        value=value,
        unit=unit,
        locator=locator,
        probe=probe,
        method=method,
        conditions=conditions or {},
        uncertainty=uncertainty,
        uncertainty_note=uncertainty_note,
        kind=kind,
        context=context,
    )


COND_CELL = dict(S.EXPERIMENTAL_CONDITIONS_CHEN2020)

SPEC: dict[str, dict[str, Any]] = {
    # ---- geometry (measured at teardown) ---------------------------------
    "neg_current_collector_thickness": dict(
        pybamm="Negative current collector thickness [m]",
        definition=(
            "Thickness of the copper current collector foil of the negative "
            "electrode (one side of the jelly roll)."
        ),
        paper=_paper(
            "12e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="measured at teardown with an incremental length gauge (Heidenhain)",
            conditions=dict(cell="LG M50 21700, disassembled in Ar glovebox (<1 ppm O2/H2O), electrodes soaked in DMC and dried at 50 C under vacuum"),
            uncertainty_note="Table II reports 11.7 um for the copper foil; Table VII rounds to 12e-6 m",
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "Table II of the paper reports current collector thickness 11.7 um (copper, negative side) vs Table VII 12e-6 m (rounding).",
        ],
    ),
    "pos_current_collector_thickness": dict(
        pybamm="Positive current collector thickness [m]",
        definition=(
            "Thickness of the aluminium current collector foil of the "
            "positive electrode (one side of the jelly roll)."
        ),
        paper=_paper(
            "16e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="measured at teardown with an incremental length gauge (Heidenhain)",
            conditions=dict(cell="LG M50 21700, disassembled in Ar glovebox (<1 ppm O2/H2O), electrodes soaked in DMC and dried at 50 C under vacuum"),
            uncertainty_note="Table II reports 16.3 um for the aluminium foil; Table VII rounds to 16e-6 m",
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "Table II of the paper reports current collector thickness 16.3 um (aluminium, positive side) vs Table VII 16e-6 m (rounding).",
        ],
    ),
    "neg_electrode_thickness": dict(
        pybamm="Negative electrode thickness [m]",
        definition="Single-sided graphite-SiOx coating thickness of the negative electrode (current collector to separator).",
        paper=_paper(
            "85.2e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="measured with an incremental length gauge (Heidenhain) at different positions on the delaminated lamina",
            conditions=dict(cell="LG M50 21700, disassembled, double-sided electrode delaminated on one side"),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "pos_electrode_thickness": dict(
        pybamm="Positive electrode thickness [m]",
        definition="Single-sided NMC coating thickness of the positive electrode (current collector to separator).",
        paper=_paper(
            "75.6e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="measured with an incremental length gauge (Heidenhain) at different positions on the delaminated lamina",
            conditions=dict(cell="LG M50 21700, disassembled, double-sided electrode delaminated on one side"),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "separator_thickness": dict(
        pybamm="Separator thickness [m]",
        definition="Ceramic-coated polyolefin separator thickness between the electrodes.",
        paper=_paper(
            "12e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="measured with an incremental length gauge (Heidenhain)",
            conditions=dict(cell="LG M50 21700, disassembled"),
            uncertainty_note="paper text: 'ca. 12 um, this approximation was due to a non-uniform thickness at different parts of the separator'",
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "cell_electrode_width": dict(
        pybamm="Electrode width [m]",
        definition=(
            "Long dimension of the electrode foil along the jelly roll. "
            "CAUTION: PyBaMM's 'Electrode width' corresponds to the paper's "
            "'Electrode length' (1.58 m); PyBaMM's 'Electrode height' is the "
            "paper's 'Electrode width' (0.065 m). Verified numerically: both "
            "carry the same two values 1.58 m and 0.065 m."
        ),
        paper=_paper(
            "1.58", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="Vernier caliper and foil-layer lengths at teardown (Table II: 79/79 cm per side for the positive electrode)",
            conditions=dict(cell="LG M50 21700"),
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "Name inversion PyBaMM vs paper (verified numerically): pybamm 'Electrode width [m]' = paper 'Electrode length' = 1.58 m; pybamm 'Electrode height [m]' = paper 'Electrode width' = 0.065 m.",
        ],
    ),
    "cell_electrode_height": dict(
        pybamm="Electrode height [m]",
        definition=(
            "Short dimension of the electrode foil. CAUTION: PyBaMM's "
            "'Electrode height' is the paper's 'Electrode width' (0.065 m)."
        ),
        paper=_paper(
            "6.5e-2", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="Vernier caliper at teardown",
            conditions=dict(cell="LG M50 21700"),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "neg_particle_radius": dict(
        pybamm="Negative particle radius [m]",
        definition=(
            "Mean radius of the graphite-SiOx active-material particles of "
            "the negative electrode, treated as equivalent spheres."
        ),
        paper=_paper(
            "5.86e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="SEM top-down image particle-size analysis (ImageJ); particles assumed spherical",
            conditions=dict(cell="LG M50 21700, extracted electrodes", temperature_k=298.15),
            uncertainty_note=(
                "bi-component electrode: graphite 5.86 um and SiOx 1.2 um "
                "(discharged state) with different volume expansion; Table IV "
                "gives composite average particle size 5.394 um (0% SOC) to "
                "19.992 um (100% SOC)"
            ),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "pos_particle_radius": dict(
        pybamm="Positive particle radius [m]",
        definition="Mean radius of the NMC 811 active-material particles of the positive electrode (near-spherical).",
        paper=_paper(
            "5.22e-6", "m", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="SEM top-down image particle-size analysis (ImageJ); particles assumed spherical",
            conditions=dict(cell="LG M50 21700, extracted electrodes", temperature_k=298.15),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    # ---- porosity / active material fractions ---------------------------
    "neg_electrode_porosity": dict(
        pybamm="Negative electrode porosity",
        definition="Electrolyte (pore) volume fraction of the negative electrode (binder/conductive additive neglected).",
        paper=_paper(
            "25", "%", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_AVG_POROSITY,
            method="average of two independent estimates: density-based (23%) and FIB-SEM 3D reconstruction (27%)",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
            context="density method neglects inactive material; FIB-SEM distinguishes pores from active material by grayscale",
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "Internal spread preserved: density-based estimate 23%, FIB-SEM estimate 27%, adopted value is their average 25%.",
        ],
    ),
    "pos_electrode_porosity": dict(
        pybamm="Positive electrode porosity",
        definition="Electrolyte (pore) volume fraction of the positive electrode (binder/conductive additive neglected).",
        paper=_paper(
            "33.5", "%", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_AVG_POROSITY,
            method="average of two independent estimates: density-based (32%) and FIB-SEM 3D reconstruction (35%)",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "Internal spread preserved: density-based estimate 32%, FIB-SEM estimate 35%, adopted value is their average 33.5%.",
        ],
    ),
    "separator_porosity": dict(
        pybamm="Separator porosity",
        definition="Electrolyte (pore) volume fraction of the ceramic-coated polyolefin separator.",
        paper=_paper(
            "47", "%", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="physical/porosimetry analysis of the extracted separator (paper Table II row 'Electrolyte volume fraction')",
            conditions=dict(cell="LG M50 21700, extracted separator"),
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "neg_electrode_active_material_volume_fraction": dict(
        pybamm="Negative electrode active material volume fraction",
        definition=(
            "Fraction of the negative-electrode control volume occupied by "
            "active-material particles (graphite + SiOx). Sets the volumetric "
            "interfacial area a = 3*eps_s/R_p and the lithium storage capacity "
            "of the electrode in the DFN. In Chen2020 eps_s + porosity = 1 "
            "(no explicit binder/filler term)."
        ),
        paper=_paper(
            "75", "%", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="derived from electrode mass/loading and theoretical crystal densities (paper assumes 100% active material; binder and conductive additive omitted)",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
            uncertainty_note=(
                "paper notes the electrode likely contains 3-4% binder and "
                "conductive additive, which is omitted; the true active "
                "material volume fraction is therefore slightly lower"
            ),
        ),
        kind=PS.LITERATURE_DERIVED,
        pybop=dict(
            applicable=True,
            pybop_class="pybop.Parameter",
            bounds=[0.55, 0.90],
            initial_guesses=[[0.62, 0.55], [0.85, 0.60], [0.70, 0.75]],
            p2_approved_pair=True,
            joint_reporting_required=True,
            notes=(
                "P2 approved estimation pair with pos_electrode_active_material_"
                "volume_fraction; correlation ridge (-0.75 to -0.85 per P2) must "
                "be reported jointly (rule 7). Validated against pybop 26.10."
            ),
        ),
    ),
    "pos_electrode_active_material_volume_fraction": dict(
        pybamm="Positive electrode active material volume fraction",
        definition=(
            "Fraction of the positive-electrode control volume occupied by "
            "NMC 811 active-material particles. Sets the volumetric "
            "interfacial area a = 3*eps_s/R_p and the lithium storage capacity "
            "of the electrode in the DFN. In Chen2020 eps_s + porosity = 1."
        ),
        paper=_paper(
            "66.5", "%", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="derived from electrode mass/loading and theoretical crystal densities (paper assumes 100% active material; binder and conductive additive omitted)",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
            uncertainty_note=(
                "paper notes binder/carbon content was assumed minimal for an "
                "energy cell and is omitted from the volume balance"
            ),
        ),
        kind=PS.LITERATURE_DERIVED,
        pybop=dict(
            applicable=True,
            pybop_class="pybop.Parameter",
            bounds=[0.45, 0.80],
            initial_guesses=[[0.62, 0.55], [0.85, 0.60], [0.70, 0.75]],
            p2_approved_pair=True,
            joint_reporting_required=True,
            notes=(
                "P2 approved estimation pair with neg_electrode_active_material_"
                "volume_fraction; correlation ridge must be reported jointly."
            ),
        ),
    ),
    # ---- Bruggeman exponents -------------------------------------------
    "pos_bruggeman_electrolyte": dict(
        pybamm="Positive electrode Bruggeman coefficient (electrolyte)",
        definition="Bruggeman tortuosity exponent linking electrolyte conductivity/diffusivity to the pore volume fraction in the positive electrode.",
        paper=_paper(
            "2.43", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_BRUGG_THEORY,
            method="calculated from FIB-SEM tortuosity (Taufactor/Simpleware) via the Bruggeman relation",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
        ),
        kind=PS.ASSUMED,
        notes=[
            "PyBaMM carries 1.5 (theoretical packed-sphere value), not the measured 2.43: the paper states Table VII values give unphysical electrolyte depletion and sets 1.5 instead. Conflict preserved in conflicts[].",
        ],
    ),
    "sep_bruggeman_electrolyte": dict(
        pybamm="Separator Bruggeman coefficient (electrolyte)",
        definition="Bruggeman tortuosity exponent for electrolyte transport in the ceramic-coated separator.",
        paper=_paper(
            "2.57", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_BRUGG_THEORY,
            method="calculated from FIB-SEM tortuosity via the Bruggeman relation",
            conditions=dict(cell="LG M50 21700, extracted separator"),
        ),
        kind=PS.ASSUMED,
        notes=["PyBaMM carries 1.5 (theoretical), not the measured 2.57; conflict preserved."],
    ),
    "neg_bruggeman_electrolyte": dict(
        pybamm="Negative electrode Bruggeman coefficient (electrolyte)",
        definition="Bruggeman tortuosity exponent for electrolyte transport in the negative electrode.",
        paper=_paper(
            "2.91", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_BRUGG_THEORY,
            method="calculated from FIB-SEM tortuosity (Table II lists 2.92/2.90 for the two sides; Table VII averages to 2.91)",
            conditions=dict(cell="LG M50 21700, extracted electrodes"),
        ),
        kind=PS.ASSUMED,
        notes=["PyBaMM carries 1.5 (theoretical), not the measured 2.91; conflict preserved."],
    ),
    "neg_bruggeman_electrode": dict(
        pybamm="Negative electrode Bruggeman coefficient (electrode)",
        definition="Bruggeman exponent for solid-phase transport in the negative electrode.",
        paper=None,
        kind=PS.ASSUMED,
        notes=[
            "Not covered by the Chen2020 paper (solid-phase tortuosity not measured); PyBaMM default 0 (no solid-phase tortuosity correction).",
        ],
    ),
    "pos_bruggeman_electrode": dict(
        pybamm="Positive electrode Bruggeman coefficient (electrode)",
        definition="Bruggeman exponent for solid-phase transport in the positive electrode.",
        paper=None,
        kind=PS.ASSUMED,
        notes=[
            "Not covered by the Chen2020 paper (solid-phase tortuosity not measured); PyBaMM default 0 (no solid-phase tortuosity correction).",
        ],
    ),
    # ---- transport / kinetics ------------------------------------------
    "neg_particle_diffusivity": dict(
        pybamm="Negative particle diffusivity [m2.s-1]",
        definition=(
            "Effective solid-phase lithium diffusivity of the graphite-SiOx "
            "negative electrode used by the DFN. The paper's GITT measurement "
            "gives an apparent diffusivity (with large uncertainty); the model "
            "value is a tuned effective constant (1C condition)."
        ),
        paper=_paper(
            1.74e-15, "m2 s-1", S.LOC_TABLE_V + "; " + S.CAP_TABLE_V,
            probe=S.PROBE_SAND_METHOD,
            method="Sand-equation fit to the voltage transient during GITT current pulses (C/10, 2.5 min pulses); average over the full SOC range; last ten points of each pulse used",
            conditions=dict(
                cell="graphite-SiOx half cell (Li counter), from LG M50",
                temperature_k=298.15,
                voltage_v="0.005-1.0",
                current="0.58 mA (0.1C)",
                pulse_min=2.5,
            ),
            uncertainty=4.10e-15,
            uncertainty_note="reported as 1.74 +/- 4.10 (1e-15 m2 s-1) in Table V",
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.CALIBRATED,
        notes=[
            "PyBaMM carries 3.3e-14 m2/s: the paper's tuned 1C value (variation +1797% vs GITT measurement). For C/2 and 1.5C the paper tuned 1.3e-14 and 6.3e-14 m2/s respectively - effective diffusivity is C-rate dependent in the paper's own validation.",
            "Paper verdict (P2 TASK 5 reproduced): negative particle diffusivity is not estimable from voltage-only observations at <=2C (mean |normalized sensitivity| 0.011-0.048).",
        ],
        pybop=dict(
            applicable=True,
            pybop_class="pybop.Parameter",
            bounds=None,
            recommended=False,
            notes=(
                "Technically pybop-declarable, but P2 TASK 5 shows it is "
                "effectively unobservable from voltage-only data at <=2C; "
                "do not estimate without new observables (GITT/high-rate pulses)."
            ),
        ),
    ),
    "pos_particle_diffusivity": dict(
        pybamm="Positive particle diffusivity [m2.s-1]",
        definition=(
            "Effective solid-phase lithium diffusivity of the NMC 811 "
            "positive electrode used by the DFN; tuned effective constant "
            "(1C condition) in the PyBaMM set, measured apparent diffusivity "
            "in the paper."
        ),
        paper=_paper(
            1.48e-15, "m2 s-1", S.LOC_TABLE_V + "; " + S.CAP_TABLE_V,
            probe=S.PROBE_SAND_METHOD,
            method="Sand-equation fit to the voltage transient during GITT current pulses (C/10, 2.5 min pulses); average over the full SOC range",
            conditions=dict(
                cell="NMC half cell (Li counter), from LG M50",
                temperature_k=298.15,
                voltage_v="3.66-4.25",
                current="0.73 mA (0.1C)",
                pulse_min=2.5,
            ),
            uncertainty=1.05e-15,
            uncertainty_note="reported as 1.48 +/- 1.05 (1e-15 m2 s-1) in Table V",
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.CALIBRATED,
        notes=[
            "PyBaMM carries 4e-15 m2/s: the paper's tuned 1C value (variation +170% vs GITT measurement).",
            "P2 identifies positive particle diffusivity as a candidate for later estimation (sensitivity 0.63-0.85 over 0.5C-2C).",
        ],
        pybop=dict(
            applicable=True,
            pybop_class="pybop.Parameter",
            bounds=None,
            recommended=True,
            notes="P2 candidate for later estimation with multi-C data; estimate jointly only with awareness of the volume-fraction ridge.",
        ),
    ),
    "neg_electrode_conductivity": dict(
        pybamm="Negative electrode conductivity [S.m-1]",
        definition="Effective electronic conductivity of the graphite-SiOx negative electrode coating (lamina).",
        paper=_paper(
            215, "S m-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_POS_CONDUCTIVITY_AVG,
            method="four-point probe on delaminated electrode lamina (Ossila); conductivity = 1/resistivity; averages of the measured range used",
            conditions=dict(cell="LG M50 21700, extracted electrodes; lamina delaminated with adhesive tape", temperature_k=298.15),
            uncertainty_note="measured range 180-250 S/m (variability from delamination and microstructure); average 215 used",
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "pos_electrode_conductivity": dict(
        pybamm="Positive electrode conductivity [S.m-1]",
        definition="Effective electronic conductivity of the NMC 811 positive electrode coating (lamina).",
        paper=_paper(
            0.18, "S m-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_POS_CONDUCTIVITY_AVG,
            method="four-point probe on delaminated electrode lamina (Ossila); conductivity = 1/resistivity; averages of the measured range used",
            conditions=dict(cell="LG M50 21700, extracted electrodes; lamina delaminated with adhesive tape", temperature_k=298.15),
            uncertainty_note="measured range 0.174-0.186 S/m; average 0.18 used",
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "neg_max_concentration": dict(
        pybamm="Maximum concentration in negative electrode [mol.m-3]",
        definition="Maximum lithium concentration in the graphite-SiOx active material (capacity-normalised; includes the unused-lithium convention of the paper).",
        paper=_paper(
            29583, "mol m-3", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_NEG_CMAX_TEXT,
            method="calculated from electrode specific capacity per unit area, coating thickness and active material volume fraction (paper Eqs. 5-7)",
            conditions=dict(cell="LG M50 21700, half-cell capacity 5.0 mAh cm-2 measured at C/50"),
            kind=PS.CALCULATED,
            context="paper body text states 29603 mol m-3 (slight rounding variant of the Table VII value 29583); both preserved",
        ),
        kind=PS.CALIBRATED,
        notes=[
            "PyBaMM carries 33133 mol/m3: the paper's tuned value (variation +12% vs calculated 29583).",
            "Text variant 29603 mol/m3 (paper body) vs Table VII 29583 mol/m3 preserved in evidence context.",
        ],
    ),
    "pos_max_concentration": dict(
        pybamm="Maximum concentration in positive electrode [mol.m-3]",
        definition="Maximum lithium concentration in the NMC 811 active material (capacity-normalised).",
        paper=_paper(
            51765, "mol m-3", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_POS_CMAX_TEXT,
            method="calculated from coating mass per unit area, molecular mass of lithiated active material, thickness and active material volume fraction (paper Eq. 5); cross-checked against crystal density 4.95 g/cm3 (theoretical 51545 mol m-3)",
            conditions=dict(cell="LG M50 21700, extracted electrodes; assumed composition Li0.833Ni0.80Mn0.08Co0.08Al0.04O2 (MW 94.87 g/mol in paper; 96.03 g/mol used in Eq. 5 for the lithiated material)"),
            kind=PS.CALCULATED,
        ),
        kind=PS.CALIBRATED,
        notes=["PyBaMM carries 63104 mol/m3: the paper's tuned value (variation +22% vs calculated 51765)."],
    ),
    # ---- stoichiometry-derived initial conditions -----------------------
    "neg_initial_concentration": dict(
        pybamm="Initial concentration in negative electrode [mol.m-3]",
        definition="Initial lithium concentration in the negative active material at 100% SOC (fully charged cell), = stoichiometry(100% SOC) x maximum concentration.",
        paper=_paper(
            "0.9014", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_STOICH_NEG,
            method="least-squares fitting of full-cell negative-electrode OCV features to map half-cell OCV to stoichiometry (paper assumes full lithiation at low voltage and zero lithium on delithiation)",
            conditions=dict(cell="LG M50 21700; half-cell and three-electrode GITT-OCV"),
            kind=PS.LITERATURE_DERIVED,
            context="stoichiometry at 100% SOC (neg) = 0.9014; at 0% SOC = 0.0279 (Table VII)",
        ),
        kind=PS.CALCULATED,
        checks=[
            ("0.9014 x 33133 == 29866", 0.9014 * 33133, 29866.0, 1e-4),
        ],
    ),
    "pos_initial_concentration": dict(
        pybamm="Initial concentration in positive electrode [mol.m-3]",
        definition="Initial lithium concentration in the positive active material at 100% SOC (fully charged cell), = tuned stoichiometry(100% SOC) x maximum concentration.",
        paper=_paper(
            "0.2661", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_II,
            method="stoichiometry mapping from half-cell/three-electrode GITT-OCV; the 100% SOC positive stoichiometry was one of the eight tuned parameters",
            conditions=dict(cell="LG M50 21700; half-cell and three-electrode GITT-OCV"),
            kind=PS.LITERATURE_DERIVED,
            context="measured stoichiometry 0.2661 (Table VII); tuned simulation value 0.27 (tuned-vs-measured table, variation 1.47%)",
        ),
        kind=PS.CALCULATED,
        checks=[
            ("0.27 x 63104 == 17038", 0.27 * 63104, 17038.0, 1e-4),
        ],
        notes=[
            "PyBaMM initial concentration 17038 = tuned stoichiometry 0.27 x tuned max concentration 63104 (code-verified); using the paper's measured stoichiometry 0.2661 gives 16792, which does not match - the operative value encodes the tuned (CALIBRATED) chain.",
        ],
    ),
    # ---- thermodynamics -------------------------------------------------
    "neg_electrode_ocp": dict(
        pybamm="Negative electrode OCP [V]",
        definition="Open-circuit potential of the graphite-SiOx negative electrode vs Li/Li+ as a function of stoichiometry (interpolated data function in PyBaMM).",
        paper=_paper(
            "see Fig. 12 or 8", "V", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_ISOTHERMAL,
            method="GITT-OCV (half-cell and three-electrode; relaxation limit dE/dt < 0.1 mV/h); PyBaMM carries an interpolated fit of the measured curve",
            conditions=dict(cell="graphite-SiOx half cell and three-electrode full cell", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "PyBaMM docstring (verified): 'LG M50 Graphite open-circuit potential as a function of stoichiometry, fit taken from [Chen2020].'",
            "Paper notes GITT-OCV shows lithiation/delithiation hysteresis; the PyBaMM function is a single (unbranched) fit.",
            "Paper Table VII references the OCV as 'see Fig. 12 or 8/9' (numbered tables/figures in the paper); numeric curve data live in PyBaMM's data files.",
        ],
    ),
    "pos_electrode_ocp": dict(
        pybamm="Positive electrode OCP [V]",
        definition="Open-circuit potential of the NMC 811 positive electrode vs Li/Li+ as a function of stoichiometry (interpolated data function in PyBaMM).",
        paper=_paper(
            "see Fig. 12 or 8", "V", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="GITT-OCV (half-cell and three-electrode; relaxation limit dE/dt < 0.1 mV/h); PyBaMM carries an interpolated fit of the measured curve",
            conditions=dict(cell="NMC half cell and three-electrode full cell", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=["PyBaMM docstring (verified): 'LG M50 NMC open-circuit potential as a function of stoichiometry, fit taken from [Chen2020].'"],
    ),
    "neg_entropic_change": dict(
        pybamm="Negative electrode OCP entropic change [V.K-1]",
        definition="Temperature coefficient of the negative-electrode OCP (entropic coefficient).",
        paper=None,
        kind=PS.ASSUMED,
        notes=["Not covered by the Chen2020 paper; set to 0 in the isothermal model (unused under isothermal validation)."],
    ),
    "pos_entropic_change": dict(
        pybamm="Positive electrode OCP entropic change [V.K-1]",
        definition="Temperature coefficient of the positive-electrode OCP (entropic coefficient).",
        paper=None,
        kind=PS.ASSUMED,
        notes=["Not covered by the Chen2020 paper; set to 0 in the isothermal model (unused under isothermal validation)."],
    ),
    # ---- kinetics -------------------------------------------------------
    "neg_exchange_current_density": dict(
        pybamm="Negative electrode exchange-current density [A.m-2]",
        definition=(
            "Butler-Volmer exchange-current density of the graphite-SiOx "
            "electrode as a function of electrolyte and surface concentration "
            "(concentration-dependent function in PyBaMM)."
        ),
        paper=_paper(
            "6.48e-7", "A m-2 (m3 mol-1)1.5", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_REACTION_RATES,
            method=(
                "derived from EIS charge-transfer resistance at 50% SOC "
                "(potentiostatic EIS, 10 mV amplitude, 10 mHz-500 kHz, "
                "equivalent-circuit fit) converted to a symmetric reaction-rate "
                "constant; j0 at 50% SOC rises from 2.95e-2 (25 C) to "
                "1.30e-1 mA cm-2 (60 C)"
            ),
            conditions=dict(
                cell="graphite-SiOx half cell (Li counter), from LG M50",
                temperature_k=298.15,
                soc="50%",
                surface_area_cm2=59.09,
            ),
            uncertainty_note="j0 measured at 50% SOC, 25-60 C (Table VI); reaction rate quoted at room temperature, no uncertainty reported",
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "PyBaMM implements j0 as a concentration-dependent function (symmetric Butler-Volmer); the scalar reaction-rate constant 6.48e-7 A m-2 (m3 mol-1)^1.5 of Table VII is embedded in the function body (see compatibility.reaction_rate_embedded).",
            "Docstring solvent wording ('EC:DMC') differs from the paper's electrolyte (EC:EMC 3:7 + 1% VC, R&D 281); definition-compatibility flag raised, numeric function unaffected.",
            "Activation energy 35.0 kJ/mol (Table VII) is NOT used by the isothermal model; recorded separately as paper-only parameter neg_activation_energy.",
        ],
    ),
    "pos_exchange_current_density": dict(
        pybamm="Positive electrode exchange-current density [A.m-2]",
        definition=(
            "Butler-Volmer exchange-current density of the NMC 811 electrode "
            "as a function of electrolyte and surface concentration "
            "(concentration-dependent function in PyBaMM)."
        ),
        paper=_paper(
            "3.42e-6", "A m-2 (m3 mol-1)1.5", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_REACTION_RATES,
            method=(
                "derived from EIS charge-transfer resistance at 50% SOC "
                "(potentiostatic EIS, 10 mV amplitude, 10 mHz-500 kHz, "
                "equivalent-circuit fit) converted to a symmetric reaction-rate "
                "constant; j0 at 50% SOC rises from 2.80e-1 (25 C) to "
                "6.02e-1 mA cm-2 (60 C)"
            ),
            conditions=dict(
                cell="NMC half cell (Li counter), from LG M50",
                temperature_k=298.15,
                soc="50%",
                surface_area_cm2=50.83,
            ),
            uncertainty_note="j0 measured at 50% SOC, 25-60 C (Table VI); reaction rate quoted at room temperature, no uncertainty reported",
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "PyBaMM implements j0 as a concentration-dependent function; the scalar reaction-rate constant 3.42e-6 A m-2 (m3 mol-1)^1.5 of Table VII is embedded in the function body (see compatibility.reaction_rate_embedded).",
            "Docstring solvent wording ('EC:DMC') differs from the paper's electrolyte (EC:EMC 3:7 + 1% VC); definition-compatibility flag raised.",
        ],
    ),
    "neg_charge_transfer_coefficient": dict(
        pybamm="Negative electrode charge transfer coefficient",
        definition="Symmetry factor (alpha) of the Butler-Volmer kinetics in the negative electrode.",
        paper=_paper(
            None, "-", S.LOC_TABLE_VII,
            probe="we assume the reaction to be symmetric",
            method="model assumption (symmetric Butler-Volmer, alpha = 0.5)",
            kind=PS.ASSUMED,
        ),
        kind=PS.ASSUMED,
    ),
    "pos_charge_transfer_coefficient": dict(
        pybamm="Positive electrode charge transfer coefficient",
        definition="Symmetry factor (alpha) of the Butler-Volmer kinetics in the positive electrode.",
        paper=_paper(
            None, "-", S.LOC_TABLE_VII,
            probe="we assume the reaction to be symmetric",
            method="model assumption (symmetric Butler-Volmer, alpha = 0.5)",
            kind=PS.ASSUMED,
        ),
        kind=PS.ASSUMED,
    ),
    # ---- electrolyte ----------------------------------------------------
    "electrolyte_diffusivity": dict(
        pybamm="Electrolyte diffusivity [m2.s-1]",
        definition="Concentration-dependent diffusion coefficient of Li+ in the electrolyte (fitted expression, not a scalar).",
        paper=_paper(
            "see 23", "m2 s-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="fitted expression from Nyman et al. 2008 (electrolyte R&D 281: 1 mol dm-3 LiPF6 in EC:EMC 3:7); the exact electrolyte of the commercial cell is unknown",
            conditions=dict(electrolyte="1 mol dm-3 LiPF6 in EC:EMC (3:7 V/V), 1 wt% VC", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
            context="paper Table VII references the fitted expression (equation number 23 in the paper) rather than a scalar value",
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=[
            "PyBaMM docstring (verified) cites: " + S.PYBAMM_DOCSTRING_NYMAN2008_CITATION,
            "Nyman2008 DOI not recorded in PyBaMM; treat as UNRESOLVED identifier until retrieved from a source.",
        ],
    ),
    "electrolyte_conductivity": dict(
        pybamm="Electrolyte conductivity [S.m-1]",
        definition="Concentration-dependent ionic conductivity of the electrolyte (fitted expression, not a scalar).",
        paper=_paper(
            "see 24", "S m-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="fitted expression from Nyman et al. 2008 (electrolyte R&D 281)",
            conditions=dict(electrolyte="1 mol dm-3 LiPF6 in EC:EMC (3:7 V/V), 1 wt% VC", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
            context="paper Table VII references the fitted expression (equation number 24 in the paper)",
        ),
        kind=PS.LITERATURE_DERIVED,
        notes=["PyBaMM docstring (verified) cites Nyman et al. 2008; same electrolyte as electrolyte_diffusivity."],
    ),
    "cation_transference_number": dict(
        pybamm="Cation transference number",
        definition="Li+ transference number in the electrolyte; evaluated from the Nyman et al. 2008 fitted expression at the initial concentration (1 mol dm-3) and held constant in the model.",
        paper=_paper(
            "0.2594", "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_TRANSFERENCE,
            method="Nyman et al. 2008 fitted expression (their Eq. 25) evaluated at 1 mol dm-3; simplified to a constant",
            conditions=dict(electrolyte="1 mol dm-3 LiPF6 in EC:EMC (3:7 V/V), 1 wt% VC", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "thermodynamic_factor": dict(
        pybamm="Thermodynamic factor",
        definition="Electrolyte thermodynamic (activity) factor; set to 1 by the ideal-electrolyte assumption of the model.",
        paper=_paper(
            None, "-", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_IDEAL_ELECTROLYTE,
            method="model assumption (ideal electrolyte; Nyman et al. activity-coefficient values deliberately not used)",
            kind=PS.ASSUMED,
        ),
        kind=PS.ASSUMED,
    ),
    "initial_electrolyte_concentration": dict(
        pybamm="Initial concentration in electrolyte [mol.m-3]",
        definition="Initial bulk Li+ concentration in the electrolyte (1 mol dm-3 LiPF6).",
        paper=_paper(
            1000, "mol m-3", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            method="experimental electrolyte composition (R&D 281); the exact commercial electrolyte is unknown",
            conditions=dict(electrolyte="1 mol dm-3 LiPF6 in EC:EMC (3:7 V/V), 1 wt% VC"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    # ---- cell-level -----------------------------------------------------
    "nominal_cell_capacity": dict(
        pybamm="Nominal cell capacity [A.h]",
        definition="Nominal (rated) capacity of the LG M50 cell between 2.5 and 4.2 V.",
        paper=_paper(
            5.0, "A.h", S.LOC_ECHEM + "; " + S.CAP_TABLE_II,
            probe=S.PROBE_CITED_CAPACITY,
            method="cited from the manufacturer data sheet; normalized to 4.87 mAh cm-2 using the positive electrode plating area 1027 cm2",
            conditions=dict(cell="LG M50 21700, new cell", voltage_window_v="2.5-4.2"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "current_function": dict(
        pybamm="Current function [A]",
        definition="Applied current at 1C for the cell (= rated capacity x 1 h^-1 = 5 A).",
        paper=_paper(
            None, "A", S.LOC_TABLE_VII,
            probe="At 1C (5 A)",
            method="calculated: 1C current = rated capacity 5 Ah / 1 h",
            conditions=dict(cell="LG M50 21700"),
            kind=PS.CALCULATED,
        ),
        kind=PS.CALCULATED,
        checks=[("5 Ah x 1 h^-1 == 5 A", 5.0, 5.0, 0.0)],
    ),
    "lower_voltage_cutoff": dict(
        pybamm="Lower voltage cut-off [V]",
        definition="Lower terminal-voltage limit used in cycling/simulation (0% SOC reference per manufacturer).",
        paper=_paper(
            2.5, "V", S.LOC_ECHEM,
            probe=S.PROBE_VALID_RATES,
            method="manufacturer SOC reference (2.5 V at C/50 = 0% SOC) and validation protocol voltage window",
            conditions=dict(cell="LG M50 21700", protocol="CC discharge / CC-CV charge"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "upper_voltage_cutoff": dict(
        pybamm="Upper voltage cut-off [V]",
        definition="Upper terminal-voltage limit used in cycling/simulation (100% SOC reference per manufacturer).",
        paper=_paper(
            4.2, "V", S.LOC_ECHEM,
            probe=S.PROBE_VALID_RATES,
            method="manufacturer voltage window and validation protocol",
            conditions=dict(cell="LG M50 21700", protocol="CC-CV charge to 4.2 V"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "ocv_at_0pct_soc": dict(
        pybamm="Open-circuit voltage at 0% SOC [V]",
        definition="Terminal open-circuit voltage at 0% SOC (manufacturer reference).",
        paper=_paper(
            2.5, "V", S.LOC_ECHEM,
            probe=S.PROBE_CITED_CAPACITY,
            method="manufacturer SOC definition (2.5 V at C/50 = 0% SOC)",
            conditions=dict(cell="LG M50 21700"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "ocv_at_100pct_soc": dict(
        pybamm="Open-circuit voltage at 100% SOC [V]",
        definition="Terminal open-circuit voltage at 100% SOC (manufacturer reference).",
        paper=_paper(
            4.2, "V", S.LOC_ECHEM,
            method="manufacturer SOC definition",
            conditions=dict(cell="LG M50 21700"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
    ),
    "reference_temperature": dict(
        pybamm="Reference temperature [K]",
        definition="Reference temperature of the isothermal model (constant cell temperature).",
        paper=_paper(
            298.15, "K", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_ISOTHERMAL,
            method="model assumption (isothermal); validation experiments performed in a chamber at 25 C",
            conditions=dict(cell="LG M50 21700, three cells for validation", chamber="25 C"),
            kind=PS.ASSUMED,
        ),
        kind=PS.ASSUMED,
    ),
    "ambient_temperature": dict(
        pybamm="Ambient temperature [K]",
        definition="Ambient (chamber) temperature during validation experiments; equals the isothermal cell temperature.",
        paper=_paper(
            298.15, "K", S.LOC_ECHEM,
            probe=S.PROBE_VALID_CHAMBER,
            method="experimental condition (chamber set at 25 C)",
            conditions=dict(cell="LG M50 21700, three cells", chamber="25 C"),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.ASSUMED,
        notes=["PyBaMM carries 298.15 K; chamber setting 25 C (paper) agrees within rounding (25 C = 298.15 K exactly by definition)."],
    ),
    "initial_temperature": dict(
        pybamm="Initial temperature [K]",
        definition="Initial cell temperature for simulations (isothermal, so equals the constant cell temperature).",
        paper=_paper(
            298.15, "K", S.LOC_TABLE_VII,
            probe=S.PROBE_ISOTHERMAL,
            method="model assumption (isothermal)",
            kind=PS.ASSUMED,
        ),
        kind=PS.ASSUMED,
    ),
    # ---- paper-only parameters ------------------------------------------
    "neg_reaction_rate": dict(
        pybamm=None,
        definition="Symmetric Butler-Volmer reaction-rate constant of the graphite-SiOx electrode (Table VII row 'Reaction rate'); embedded in the PyBaMM j0 function, not exposed as a scalar key.",
        paper=_paper(
            "6.48e-7", "A m-2 (m3 mol-1)1.5", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_REACTION_RATES,
            method="derived from EIS exchange current at 50% SOC and room temperature (see neg_exchange_current_density)",
            conditions=dict(cell="graphite-SiOx half cell (Li counter)", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        compatibility_note="not a PyBaMM Chen2020 key; value is embedded in the PyBaMM exchange-current function body",
    ),
    "pos_reaction_rate": dict(
        pybamm=None,
        definition="Symmetric Butler-Volmer reaction-rate constant of the NMC 811 electrode (Table VII row 'Reaction rate'); embedded in the PyBaMM j0 function, not exposed as a scalar key.",
        paper=_paper(
            "3.42e-6", "A m-2 (m3 mol-1)1.5", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VII,
            probe=S.PROBE_REACTION_RATES,
            method="derived from EIS exchange current at 50% SOC and room temperature (see pos_exchange_current_density)",
            conditions=dict(cell="NMC half cell (Li counter)", temperature_k=298.15),
            kind=PS.LITERATURE_DERIVED,
        ),
        kind=PS.LITERATURE_DERIVED,
        compatibility_note="not a PyBaMM Chen2020 key; value is embedded in the PyBaMM exchange-current function body",
    ),
    "neg_activation_energy": dict(
        pybamm=None,
        definition="Activation energy of the negative-electrode charge-transfer reaction (Table VII row 'Activation energy'); not used by the isothermal model.",
        paper=_paper(
            35.0e3, "J mol-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VI,
            method="Arrhenius fit of EIS-derived exchange currents at 30-60 C (paper Fig. 16); paper states it is 'not utilized in the model supplied here'",
            conditions=dict(cell="graphite-SiOx half cell (Li counter)", temperature_k="303.15-333.15"),
            kind=PS.CALCULATED,
        ),
        kind=PS.CALCULATED,
        compatibility_note="no PyBaMM Chen2020 key exists (isothermal model); needed for temperature-dependent extensions",
    ),
    "pos_activation_energy": dict(
        pybamm=None,
        definition="Activation energy of the positive-electrode charge-transfer reaction (Table VII row 'Activation energy'); not used by the isothermal model.",
        paper=_paper(
            17.8e3, "J mol-1", S.LOC_TABLE_VII + "; " + S.CAP_TABLE_VI,
            method="Arrhenius fit of EIS-derived exchange currents at 30-60 C (paper Fig. 16)",
            conditions=dict(cell="NMC half cell (Li counter)", temperature_k="303.15-333.15"),
            kind=PS.CALCULATED,
        ),
        kind=PS.CALCULATED,
        compatibility_note="no PyBaMM Chen2020 key exists (isothermal model); needed for temperature-dependent extensions",
    ),
}


# --------------------------------------------------------------------------
# family defaults for keys not covered by SPEC
# --------------------------------------------------------------------------
UNRESOLVED_FAMILIES: dict[str, dict[str, Any]] = {
    "sei": dict(
        match=lambda k: k.startswith("SEI ")
        or k in (
            "Ratio of lithium moles to SEI moles",
            "Bulk solvent concentration [mol.m-3]",
            "Lithium interstitial reference concentration [mol.m-3]",
            "Initial SEI thickness [m]",
            "EC initial concentration in electrolyte [mol.m-3]",
            "EC diffusivity [m2.s-1]",
        ),
        definition=lambda k: f"SEI/degradation sub-model parameter '{k}' shipped with the PyBaMM Chen2020 set.",
        note=(
            "Not part of the Chen2020 paper's 37-parameter P2D set; shipped as "
            "PyBaMM 26.8.0.0 defaults for the DFN SEI options. Original "
            "literature provenance UNRESOLVED; trace before any calibration use."
        ),
    ),
    "lam": dict(
        match=lambda k: k.endswith("reaction-driven LAM factor [m3.mol-1]"),
        definition=lambda k: f"Loss-of-active-material sub-model parameter '{k}'.",
        note=(
            "Not part of the Chen2020 paper's P2D set; PyBaMM default 0 "
            "(no reaction-driven LAM in the isothermal beginning-of-life model)."
        ),
        status=PS.ASSUMED,
    ),
    "thermal_materials": dict(
        match=lambda k: k.endswith("[kg.m-3]")
        or k.endswith("[J.kg-1.K-1]")
        or k.endswith("[W.m-1.K-1]")
        or k.endswith("[S.m-1]")
        and "current collector" in k
        or k == "Cell thermal expansion coefficient [m.K-1]",
        definition=lambda k: f"Thermal/material property '{k}' used by the extended (thermal) PyBaMM models.",
        note=(
            "Not reported in the Chen2020 paper's parameter tables; PyBaMM "
            "default material values (Cu/Al current collectors and electrode/"
            "separator thermal properties). Provenance UNRESOLVED (candidate "
            "standard-material/handbook values); verify before calibration use."
        ),
    ),
    "double_layer": dict(
        match=lambda k: "double-layer capacity" in k,
        definition=lambda k: f"Double-layer capacitance '{k}' at the electrode/electrolyte interface.",
        note=(
            "Not covered by the Chen2020 paper; PyBaMM default 0.2 F/m2. "
            "Provenance UNRESOLVED; unused by the paper's validation timescales."
        ),
    ),
    "thermal_config": dict(
        match=lambda k: k == "Total heat transfer coefficient [W.m-2.K-1]",
        definition=lambda k: "Total heat-transfer coefficient of the cell surface (thermal model).",
        note=(
            "Not covered by the Chen2020 paper (isothermal model); PyBaMM "
            "default 10 W m-2 K-1. Provenance UNRESOLVED; unused under isothermal "
            "validation."
        ),
    ),
    "config": dict(
        match=lambda k: k
        in (
            "Contact resistance [Ohm]",
            "Number of electrodes connected in parallel to make a cell",
            "Number of cells connected in series to make a battery",
        ),
        definition=lambda k: f"Cell-configuration parameter '{k}'.",
        note=(
            "Model/geometry configuration default (no contact resistance; "
            "single cell). ASSUMED."
        ),
        status=PS.ASSUMED,
    ),
}


# --------------------------------------------------------------------------
# record construction
# --------------------------------------------------------------------------
def _paper_entry(cid: str, spec: dict, text: str) -> ValueEntry | None:
    p = spec.get("paper")
    if not p:
        return None
    if p.get("probe"):
        loc = extract_quote(text, p["probe"])
        quote, c0, c1 = loc["quote"], loc["char_start"], loc["char_end"]
    else:
        quote, c0, c1 = None, None, None
    src = SourceRef(
        document_id=S.CHEN2020_DOC_ID,
        title=S.CHEN2020_TITLE,
        doi_or_url=S.CHEN2020_DOI,
        locator=p["locator"],
        char_start=c0,
        char_end=c1,
        quote=quote,
    )
    return ValueEntry(
        value=p["value"],
        unit=p["unit"],
        source=src,
        kind=p["kind"],
        reported_uncertainty=p.get("uncertainty"),
        uncertainty_note=p.get("uncertainty_note"),
        conditions=p.get("conditions", {}),
        method=p.get("method"),
        context=p.get("context"),
        review_state=RS.ACCEPTED
        if p["kind"] != PS.UNRESOLVED
        else RS.NEEDS_REVIEW,
    )


def _run_checks(checks: list[tuple]) -> list[str]:
    out = []
    for label, computed, target, reltol in checks:
        ok = abs(computed - target) <= reltol * max(1.0, abs(target))
        out.append(
            f"check {label}: computed={computed:.6g} target={target:.6g} "
            f"{'PASS' if ok else 'FAIL'} (reltol={reltol:g})"
        )
    return out


def _conflict_entry(
    paper_value: Any,
    paper_unit: str | None,
    spec: dict[str, Any],
    text: str,
    extra_note: str | None = None,
) -> ValueEntry:
    p = spec["paper"]
    if p.get("probe"):
        loc = extract_quote(text, p["probe"])
        quote, c0, c1 = loc["quote"], loc["char_start"], loc["char_end"]
    else:
        quote, c0, c1 = None, None, None
    src = SourceRef(
        document_id=S.CHEN2020_DOC_ID,
        title=S.CHEN2020_TITLE,
        doi_or_url=S.CHEN2020_DOI,
        locator=p["locator"],
        char_start=c0,
        char_end=c1,
        quote=quote,
    )
    ctx = p.get("context")
    if extra_note:
        ctx = (ctx + " | " if ctx else "") + extra_note
    return ValueEntry(
        value=paper_value,
        unit=paper_unit,
        source=src,
        kind=p["kind"],
        reported_uncertainty=p.get("uncertainty"),
        uncertainty_note=p.get("uncertainty_note"),
        conditions=p.get("conditions", {}),
        method=p.get("method"),
        context=ctx,
        review_state=RS.NEEDS_REVIEW,
    )


def build_records(pybamm_params: dict[str, Any], text: str) -> list[ParameterRecord]:
    """Build all ParameterRecords deterministically from PyBaMM values + archive."""
    records: list[ParameterRecord] = []
    covered: set[str] = set()
    for cid, spec in SPEC.items():
        key = spec.get("pybamm")
        if key:
            value = pybamm_params[key]
        else:
            value = (spec.get("paper") or {}).get("value")
        covered.add(key) if key else None
        is_fn = callable(value)
        if is_fn:
            value_repr = getattr(value, "__name__", repr(value))
            value_unit = None
            norm_value, norm_unit = value_repr, "function"
        else:
            value_repr = value
            suffix = S_pybamm_unit(key) if key else ""
            if not key and spec.get("paper"):
                value_unit = spec["paper"].get("unit") or "dimensionless"
                norm_value, norm_unit = normalize_value(
                    value_repr, spec["paper"].get("unit")
                )
            else:
                value_unit = suffix or "dimensionless"
                norm_value, norm_unit = normalize_value(value_repr, suffix or None)
        pe = _paper_entry(cid, spec, text)
        notes = list(spec.get("notes", []))
        compat: dict[str, Any] = {}
        if spec.get("compatibility_note"):
            compat["note"] = spec["compatibility_note"]
        if key and is_fn:
            compat["function_valued"] = True
            compat["pybamm_function"] = value_repr
        if "j0" in cid or "exchange_current" in cid:
            compat.update(_check_reaction_rate_embedded(value, cid))
        for line in _run_checks(spec.get("checks", [])):
            notes.append(line)
            if "FAIL" in line:
                compat["consistency_check_failed"] = True
        conflicts: list[ValueEntry] = []
        if pe and spec["kind"] == PS.CALIBRATED:
            # operative value is the tuned/PyBaMM value; preserve the paper value
            conflicts.append(
                _conflict_entry(
                    pe.value,
                    pe.unit,
                    spec,
                    text,
                    extra_note=(
                        f"PyBaMM/Chen2020-tuned value carried in the set: "
                        f"{value_repr!r} {value_unit or ''}"
                    ),
                )
            )
            src_id = S.CHEN2020_DOI
            src_loc = (
                S.LOC_TUNED_TABLE
                + " (tuned value); conflict carries the measured value"
            )
        elif pe and spec["kind"] == PS.ASSUMED and cid.startswith(
            ("pos_bruggeman", "neg_bruggeman", "sep_bruggeman")
        ):
            conflicts.append(
                _conflict_entry(
                    pe.value,
                    pe.unit,
                    spec,
                    text,
                    extra_note="PyBaMM carries the theoretical value 1.5 instead of the measured value",
                )
            )
            src_id = S.CHEN2020_DOI
            src_loc = (
                S.LOC_TABLE_VII
                + " (measured exponent preserved as conflict); operative value "
                "is the theoretical packed-sphere assumption 1.5"
            )
        elif pe:
            src_id = S.CHEN2020_DOI
            src_loc = pe.source.locator
        else:
            src_id = PYBAMM_DEFAULT_SOURCE_ID if key else S.CHEN2020_DOI
            src_loc = (
                f"pybamm 26.8.0.0 ParameterValues('Chen2020')['{key}']"
                if key
                else S.LOC_TABLE_VII
            )
        val_state = (
            RS.NEEDS_REVIEW
            if conflicts or spec["kind"] in (PS.UNRESOLVED, PS.CALIBRATED)
            else RS.ACCEPTED
        )
        if pe is None and spec.get("kind") == PS.ASSUMED:
            val_state = RS.NEEDS_REVIEW
        records.append(
            ParameterRecord(
                canonical_id=cid,
                pybamm_names=[key] if key else [],
                pybop_mapping=spec.get("pybop"),
                definition=spec["definition"],
                value=value_repr,
                value_unit=value_unit,
                normalized_value=norm_value,
                normalized_value_unit=norm_unit,
                status=spec["kind"],
                source_id=src_id,
                source_location=src_loc,
                evidence=pe,
                conditions=(pe.conditions if pe else COND_CELL) or {},
                method=pe.method if pe else None,
                reported_uncertainty=(pe.reported_uncertainty if pe else None),
                validation_state=val_state,
                compatibility=compat,
                conflicts=conflicts,
                notes=notes,
            )
        )
    # family defaults for uncovered keys
    for key, value in pybamm_params.items():
        if key in covered or key == "citations":
            continue
        fam = None
        for name, f in UNRESOLVED_FAMILIES.items():
            try:
                if f["match"](key):
                    fam = (name, f)
                    break
            except Exception:
                continue
        if fam is None:
            fam = ("untraced", dict(
                definition=lambda k: f"Parameter '{k}' shipped with the PyBaMM Chen2020 set.",
                note="Provenance UNRESOLVED (no location in the retrieved corpus).",
            ))
        _, f = fam
        status = f.get("status", PS.UNRESOLVED)
        suffix = S_pybamm_unit(key)
        norm_value, norm_unit = normalize_value(value, suffix or None)
        records.append(
            ParameterRecord(
                canonical_id=_slug(key),
                pybamm_names=[key],
                pybop_mapping=dict(
                    applicable=True,
                    pybop_class="pybop.Parameter",
                    notes="scalar-valued; pybop-declarable but not selected for estimation",
                )
                if not callable(value)
                else dict(
                    applicable=False,
                    notes="function-valued parameter; not declarable as a scalar pybop.Parameter",
                ),
                definition=f["definition"](key),
                value=value if not callable(value) else getattr(value, "__name__", repr(value)),
                value_unit=suffix or "dimensionless",
                normalized_value=norm_value,
                normalized_value_unit=norm_unit,
                status=status,
                source_id=PYBAMM_DEFAULT_SOURCE_ID,
                source_location=f"pybamm 26.8.0.0 ParameterValues('Chen2020')['{key}']",
                evidence=None,
                conditions=dict(COND_CELL),
                method=None,
                reported_uncertainty=None,
                validation_state=RS.NEEDS_REVIEW,
                compatibility={"note": f["note"]},
                conflicts=[],
                notes=[],
            )
        )
    return records


def S_pybamm_unit(pybamm_key: str) -> str:
    """Return the bracketed unit suffix of a PyBaMM parameter key.

    Thin lazy-import wrapper around :func:`registry.units.pybamm_unit_suffix`;
    kept as a named indirection used by the record builders above.
    """
    from .units import pybamm_unit_suffix

    return pybamm_unit_suffix(pybamm_key)


def _check_reaction_rate_embedded(fn: Any, cid: str) -> dict[str, Any]:
    """Inspect the PyBaMM j0 function source for the paper's reaction-rate constant."""
    target = "3.42" if "pos" in cid else "6.48"
    out: dict[str, Any] = {}
    try:
        src = inspect.getsource(fn)
    except Exception:  # pragma: no cover - depends on import style
        out["reaction_rate_embedded"] = "unknown (source unavailable)"
        out["reaction_rate_probe"] = target
        return out
    out["reaction_rate_probe"] = target
    out["reaction_rate_embedded"] = target in src
    return out


def _slug(pybamm_key: str) -> str:
    s = pybamm_key.lower()
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def seed_registry(
    root: str | Path = "data/registry",
    pybamm_params: dict[str, Any] | None = None,
    raw_text_path: str | Path = RAW_DOC,
) -> RegistryStore:
    """Deterministically seed a registry store (P3 entry point).

    Introspects the installed ``pybamm.ParameterValues("Chen2020")`` unless
    pass-through ``pybamm_params`` is given, extracts verbatim evidence
    quotes from the archived article text at ``raw_text_path``, and upserts
    every built record under a fixed actor/note. Returns the populated
    :class:`RegistryStore`. Raises on any probe miss (no silent defaults).
    """
    if pybamm_params is None:
        import pybamm

        pv = pybamm.ParameterValues("Chen2020")
        pybamm_params = {k: pv[k] for k in pv}
    text = Path(raw_text_path).read_text()
    records = build_records(pybamm_params, text)
    store = RegistryStore(root)
    for rec in records:
        store.upsert(rec, actor="seed:pybamm-introspection+chen2020-archive", note="initial P3 seeding")
    return store


if __name__ == "__main__":  # pragma: no cover
    st = seed_registry()
    print(f"seeded {len(st)} records into {st.root}")
    print("content hash:", st.proof_of_content()[:16])
