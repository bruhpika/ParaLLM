"""Verified provenance anchors for the Chen2020 (LG M50) parameter set (P3).

This module holds structure + typed table contents extracted from the
actually retrieved article; verbatim *quotes* are NOT retyped here. They
are located in the archived raw document (ASCII probes below) at seed time,
so every quote in the registry is guaranteed to be a real substring of the
archived text with exact char offsets (no fabricated locations).

Archived (immutable): data/raw_documents/chen2020_jes_167_080534/
"""

CHEN2020_DOC_ID = "chen2020_jes_167_080534"
CHEN2020_URL = "https://iopscience.iop.org/article/10.1149/1945-7111/ab9050"
CHEN2020_DOI = "10.1149/1945-7111/ab9050"
CHEN2020_TITLE = (
    "Development of Experimental Techniques for Parameterization of "
    "Multi-scale Lithium-ion Battery Models"
)
CHEN2020_LICENSE = "CC BY-NC-ND 4.0"
CHEN2020_RETRIEVED = "2026-11-04"

CAP_TABLE_II = (
    "Table II. Geometrical measurements for the negative electrode and "
    "positive electrode from a disassembled LGM50."
)
CAP_TABLE_III = (
    "Table III. Active material components for positive electrode ascertained "
    "from ICP-OES and SEM-EDS."
)
CAP_TABLE_V = (
    "Table V. Diffusion coefficients calculated for positive electrode and "
    "negative electrode."
)
CAP_TABLE_VI = (
    "Table VI. Charge transfer resistance and exchange current densities of "
    "NMC and graphite-SiOx electrodes at different temperature."
)
CAP_TABLE_VII = "Table VII. Parameter set for the Newman P2D model."

_ANCHOR_NOTE = (
    "The article-page HTML-to-text conversion retained table labels for "
    "Tables II, III, IV, V, VI and VII but not for the two validation tables "
    "near the end of the paper (captions below); those are cited by exact "
    "caption text and section. Printed table numbers should be confirmed "
    "against the published PDF before external publication."
)
ANCHOR_NOTE_UNNUMBERED_TABLES = _ANCHOR_NOTE

LOC_TABLE_II = "Table II (label retained in retrieved text)"
LOC_TABLE_V = "Table V (label retained in retrieved text)"
LOC_TABLE_VI = "Table VI (label retained in retrieved text)"
LOC_TABLE_VII = "Table VII (label retained in retrieved text)"
CAP_RMSE_PREFIX = "Root-mean-squared error and peak error for the output voltage"
CAP_TUNED_PREFIX = (
    "Comparison between the experimentally determined and the tuned "
    "parameter values for 1C discharge experimental data."
)
LOC_RMSE_TABLE = (
    'section "P2D model simulations"; table by exact caption '
    f'"{CAP_RMSE_PREFIX} ..." (label not retained by HTML-to-text conversion)'
)
LOC_TUNED_TABLE = (
    'section "P2D model simulations"; table by exact caption '
    '"Comparison between the experimentally determined and the tuned '
    'parameter values for 1C discharge experimental data." '
    "(label not retained by HTML-to-text conversion)"
)
SEC_PHYS = 'section "Physical properties and parameterization"'
SEC_CHEM = 'section "Chemical properties and parameterization"'
SEC_ECHEM = 'section "Electrochemical properties and parameterization"'
SEC_SIM = 'section "P2D model simulations"'
LOC_ECHEM = SEC_ECHEM

# ASCII probes: distinctive folded substrings used to extract verbatim
# evidence sentences (with offsets) from the archived text at seed time.
PROBE_TUNE_EIGHT = "eight parameters that we adjusted"
PROBE_BRUGG_THEORY = "set to the theoretical value of 1.5 for packed spheres"
PROBE_BRUGG_UNPHYSICAL = "provides unphysical simulation results"
PROBE_REACTION_RATES = "reaction rates are 3.42"
PROBE_TRANSFERENCE = "yields t+= 0.2594"
PROBE_IDEAL_ELECTROLYTE = "we assumed an ideal electrolyte"
PROBE_AVG_POROSITY = "take the average between them as our parameter values"
PROBE_STOICH_NEG = "minimum and maximum lithium stoichiometry"
PROBE_RATED_CAPACITY = "rated capacity of the LGM50 cell"
PROBE_ISOTHERMAL = "This model is isothermal"
PROBE_DATA_AVAILABILITY = "available in the Python Battery Mathematical Modelling"
PROBE_SAND_METHOD = "The diffusion coefficients calculated for NMC and graphite-SiOx electrodes are shown in Table V"
PROBE_FOUR_POINT = "The electronic conductivities of the electrodes were measured with a four-point probe"
PROBE_POS_CMAX_TEXT = "maximum concentration in the positive electrode active material is 51765"
PROBE_NEG_CMAX_TEXT = "maximum lithium concentration in the negative electrode active material of 29603"
PROBE_POS_CONDUCTIVITY_AVG = (
    "values 0.18 S m-1 and 215 S m-1 were used for the positive electrode"
)
PROBE_EXPANSION_FACTOR = (
    "we have applied a linear expansion factor to the diffusion coefficient"
)
PROBE_HALFSURFACE_AREAS = (
    "Surface areas used for calculating j0 are 50.83 cm2 for positive electrode"
)
PROBE_VALID_CHAMBER = "three different cells were cycled in a chamber set at 25"
PROBE_VALID_RATES = "(C/2, 1C and 1.5C) between 2.5 V and 4.2 V"
PROBE_EIS_CONFIG = (
    "we performed EIS measurement in potentiostatic mode with a voltage "
    "amplitude of 10 mV"
)
PROBE_GITT_LIMITS = (
    "current pulses of C/10 were applied to the cells for 2.5 min, followed "
    "by a rest period"
)
PROBE_CITED_CAPACITY = "is cited to be 5 Ah"

# Exact table-VII rows as retrieved (paper value per column pos|sep|neg);
# printed units preserved verbatim.
TABLE_VII_ROWS: dict[str, dict[str, str | None]] = {
    "current_collector_thickness": {"unit": "m", "pos": "16e-6", "sep": None, "neg": "12e-6"},
    "electrode_thickness": {"unit": "m", "pos": "75.6e-6", "sep": "12e-6", "neg": "85.2e-6"},
    "electrode_length": {"unit": "m", "pos": "1.58", "sep": None, "neg": None},
    "electrode_width": {"unit": "m", "pos": "6.5e-2", "sep": None, "neg": None},
    "mean_particle_radius": {"unit": "m", "pos": "5.22e-6", "sep": None, "neg": "5.86e-6"},
    "electrolyte_volume_fraction": {"unit": "%", "pos": "33.5", "sep": "47", "neg": "25"},
    "active_material_volume_fraction": {"unit": "%", "pos": "66.5", "sep": None, "neg": "75"},
    "bruggeman_exponent": {"unit": "-", "pos": "2.43", "sep": "2.57", "neg": "2.91"},
    "solid_phase_lithium_diffusivity": {"unit": "m2 s-1", "pos": "1.48e-15", "sep": None, "neg": "1.74e-15"},
    "solid_phase_electronic_conductivity": {"unit": "S m-1", "pos": "0.18", "sep": None, "neg": "215"},
    "maximum_concentration": {"unit": "mol m-3", "pos": "51765", "sep": None, "neg": "29583"},
    "stoichiometry_at_0pct_soc": {"unit": "-", "pos": "0.9084", "sep": None, "neg": "0.0279"},
    "stoichiometry_at_100pct_soc": {"unit": "-", "pos": "0.2661", "sep": None, "neg": "0.9014"},
    "electrolyte_ionic_diffusivity": {"unit": "m2 s-1", "pos": None, "sep": None, "neg": None},
    "electrolyte_ionic_conductivity": {"unit": "S m-1", "pos": None, "sep": None, "neg": None},
    "transference_number": {"unit": "-", "pos": None, "sep": "0.2594", "neg": None},
    "initial_electrolyte_concentration": {"unit": "mol m-3", "pos": None, "sep": "1000", "neg": None},
    "open_circuit_voltages": {"unit": "V", "pos": "see Fig. 12 or 8", "sep": None, "neg": "see Fig. 12 or 9"},
    "activation_energy": {"unit": "J mol-1", "pos": "17.8e3", "sep": None, "neg": "35.0e3"},
    "reaction_rate": {"unit": "A m-2 (m3 mol-1)1.5", "pos": "3.42e-6", "sep": None, "neg": "6.48e-7"},
}

# Table V as retrieved (diffusion coefficients with printed uncertainties).
TABLE_V_DIFFUSIVITY = {
    "pos": {
        "value": 1.48e-15,
        "uncertainty": 1.05e-15,
        "voltage_v": "3.66-4.25",
        "current_mA": "0.73 (0.1C)",
        "pulse_min": 2.5,
        "radius_um": 5.22,
        "method": (
            "Sand-equation fit to the voltage transient during the GITT "
            "current pulse; average over the full SOC range"
        ),
    },
    "neg": {
        "value": 1.74e-15,
        "uncertainty": 4.10e-15,
        "voltage_v": "0.005-1.0",
        "current_mA": "0.58 (0.1C)",
        "pulse_min": 2.5,
        "radius_um": 5.86,
        "method": (
            "Sand-equation fit to the voltage transient during the GITT "
            "current pulse; average over the full SOC range; last ten points "
            "of the pulse used for the fit"
        ),
    },
}

# Table VI as retrieved (EIS at 50% SOC, PEIS, 10 mV amplitude);
# temperatures degC; Rct in Ohm; j0 in mA/cm^2.
TABLE_VI_KINETICS = {
    "pos": {
        "temp_C": [25, 30, 40, 50, 60],
        "Rct_Ohm": [1.80, 1.48, 1.17, 1.01, 0.94],
        "j0_mA_cm2": [2.80e-1, 3.48e-1, 4.53e-1, 5.44e-1, 6.02e-1],
        "surface_area_cm2": 50.83,
    },
    "neg": {
        "temp_C": [25, 30, 40, 50, 60],
        "Rct_Ohm": [14.72, 12.51, 7.93, 5.66, 3.74],
        "j0_mA_cm2": [2.95e-2, 3.54e-2, 5.76e-2, 8.32e-2, 1.30e-1],
        "surface_area_cm2": 59.09,
    },
    "method": (
        "potentiostatic EIS at 50% SOC of half cells, temperature series "
        "30-60 C (row 25C from the room-temperature initial series); "
        "equivalent-circuit fit; exchange current from charge-transfer "
        "resistance"
    ),
}

# Tuned-vs-measured table (1C), caption prefix CAP_TUNED_PREFIX.
TUNED_VS_MEASURED_1C = {
    "pos_diffusivity": {"measured": 1.48e-15, "tuned": 4e-15, "variation_pct": 170},
    "neg_diffusivity": {"measured": 1.74e-15, "tuned": 3.3e-14, "variation_pct": 1797},
    "pos_max_concentration": {"measured": 51765, "tuned": 63104, "variation_pct": 22},
    "neg_max_concentration": {"measured": 29583, "tuned": 33133, "variation_pct": 12},
    "pos_100pct_soc_stoichiometry": {"measured": 0.2661, "tuned": 0.27, "variation_pct": 1.47},
    "bruggeman_pos_sep_neg": {"measured": "2.43/2.57/2.91", "tuned": "1.5", "variation_pct": "38/42/48"},
    "neg_diffusivity_c2": {"tuned": 1.3e-14},
    "neg_diffusivity_1p5c": {"tuned": 6.3e-14},
}

RMSE_VALIDATION_1C = {
    "C/2": {"rmse_mV": 46, "peak_error_mV": 302},
    "1C": {"rmse_mV": 41, "peak_error_mV": 271},
    "1.5C": {"rmse_mV": 36, "peak_error_mV": 272},
}

# Paper-only parameter rows not present as Chen2020 PyBaMM keys:
PAPER_ONLY_PARAMETERS = ["activation_energy", "reaction_rate"]

EXPERIMENTAL_CONDITIONS_CHEN2020 = {
    "cell": "LG M50 21700 cylindrical cell (70.00 mm x 21.00 mm, 68.38 g with can)",
    "temperature_k": 298.15,
    "model_assumption": "isothermal, T = 298.15 K constant",
    "voltage_window_v": "2.5-4.2",
    "electrolyte_note": (
        "exact electrolyte of the commercial cell unknown; experiments used "
        "1 mol dm-3 LiPF6 in EC:EMC (3:7 V/V) with 1 wt% VC (Soulbrain "
        "R&D 281), the same electrolyte studied by Nyman et al. 2008"
    ),
    "chemistry": (
        "NMC 811 positive (assumed composition Li0.833Ni0.80Mn0.08Co0.08"
        "Al0.04O2) / bi-component graphite-SiOx negative (10 wt% SiOx)"
    ),
    "rated_capacity_ah": 5.0,
}

# Verified by introspection of installed pybamm 26.8.0.0 (docstrings):
PYBAMM_DOCSTRING_NYMAN2008_CITATION = (
    'A. Nyman, M. Behm, and G. Lindbergh, "Electrochemical characterisation '
    "and modelling of the mass transport phenomena in LiPF6-EC-EMC "
    'electrolyte," Electrochim. Acta, vol. 53, no. 22, pp. 6356-6365, 2008.'
)
NYMAN2008_ID = "Nyman2008"
NYMAN2008_DOI_NOTE = (
    "DOI not recorded in the PyBaMM docstring; resolved only if found in a "
    "retrieved source (Part C/F), never from memory"
)
