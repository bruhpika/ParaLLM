# Experimental Data Requirements

Phase P2 / TASK 6. **Planning document only — no dataset is selected or
endorsed here.** The Neware sample used in P1 is a 40 mAh NMC622 ingestion
demonstration and is explicitly *not* an LG M50 validation dataset.

The purpose of future experimental data is independent validation of
calibration results (scientific rule 9: calibration data must never double as
validation data) against a cell that actually matches the demonstrator
parameter set.

## 1. Target cell definition (must match the model)

Our demonstrator is the PyBaMM **Chen2020** parameter set, characterized in:

> Chen, C.-H., Brosa Planella, F., O'Regan, K., Gastol, D., Widanage, W. D.,
> Kendrick, E., "Development of Experimental Techniques for Parameterization
> of Multi-scale Lithium-ion Battery Models," J. Electrochem. Soc. 167(8),
> 080534 (2020). DOI: 10.1149/1945-7111/ab9050

Verified set contents: commercial **LG M50** cell, nominal 5.0 A.h, graphite
negative / NMC positive ("graphite_LGM50"/"nmc_LGM50" data), voltage window
2.5–4.2 V, 298.15 K reference.

## 2. Required dataset characteristics

### 2.1 Cell identity (hard requirements)

1. Commercial **LG M50** cells (same product generation), with manufacturer,
   form factor and, ideally, lot/date documented.
2. Nominal capacity ≈ 5 A.h; measured capacity within ±5 % of nominal at the
   test temperature (records capacity fade state).
3. Cell history documented: fresh/formation status, prior cycling (prefer
   beginning-of-life or with recorded characterization history).

### 2.2 Environmental conditions

4. Temperature: 25 °C (298.15 K) ± 1 K, measured at the cell, recorded as a
   time series (the baseline model is isothermal at 298.15 K).
5. Temperature-controlled chamber or thermal bath; ambient logging for
   leakage checks.

### 2.3 Protocol (must match model assumptions and planned diagnostics)

6. Galvanostatic discharge at ≥3 rates from the demonstrated set
   **0.5C / 1C / 2C** (5 A reference), each from a standardized 100 % SOC
   state.
7. Charge protocol documented (CC-CV with CV termination current, e.g.
   C/20 cut-off) with rest before discharge; SOC reference defined.
8. Voltage limits 4.2 V / 2.5 V consistent with the parameter set.
9. At least one **low-rate reference** (C/20–C/30) OCV curve for stoichiometry
   endpoints.
10. Optional but highly valuable for the diffusivity/kinetics plan
    (`docs/PARAMETER_SELECTION.md`): GITT or pulse-relaxation segments, EIS at
    ≥3 SOC points, CV segments, and/or repeats at a second temperature.
11. Rest periods between steps (voltage relaxation) recorded, not discarded.

### 2.4 Measurement quality

12. Voltage accuracy ≤ 1 mV (resolution ≤ 0.1 mV), current accuracy ≤ 0.5 %
    of applied, temperature ± 0.5 K.
13. Sampling ≤ 10 s during transients (≤ 1 s preferred during pulses).
14. Raw, unfiltered time-stamped data preserved; any filtering documented.

### 2.5 Provenance and reproducibility (project rules)

15. Public availability with a stable identifier (DOI/repository) and a
    license permitting analysis and publication of derived results.
16. Machine-readable format (CSV/parquet or cycler-native export convertible
    by PyProBE: Neware/Arbin/BioLogic .mpt/Basytec/Maccor/Novonix or generic
    column-mapped), plus protocol documentation (PyProBE-style README.yaml
    semantics: step descriptions as PyBaMM experiment strings).
17. Metadata: cell ID, chemistry, capacity, test rig, operator/date,
    equipment calibration records where available.

### 2.6 Validation design (rule 9)

18. Enough repeats/cycles to split **calibration vs held-out validation**:
    e.g. calibration on 1C discharge(s), validation on 0.5C and 2C and/or a
    held-out cycle; split defined *before* fitting and recorded in the run
    manifest.

## 3. Explicitly unsuitable datasets (do not substitute for convenience)

| Dataset | Why unsuitable |
|---|---|
| PyProBE Neware sample (`tests/sample_data/neware`) | NMC622, 0.04 A.h — wrong chemistry/scale; ingestion demo only |
| Arbitrary NMC811/graphite cells of other formats | Parameter set geometry/capacity mismatch (rules 3–4) |
| Degraded/cycled cells without history | Chen2020 is a beginning-of-life set; degradation not modelled in P0–P4 |

## 4. Candidate sources to evaluate later (NOT selected)

These are leads requiring verification of cell identity, protocol match,
metadata completeness and license before any use:

1. **Data accompanying Chen et al. 2020** (DOI above) — the parameter set's
   own experimental basis; verify raw-data availability and license.
2. **PyProBE LGM50 sample** (`tests/sample_data/LGM50/*.parquet`,
   "NDK - LG M50 deg ... 25degC ... BoL - RPT" files) — appears to be LG M50
   at 25 °C with BoL RPT protocol; provenance ("NDK" database), degradation
   state and reuse terms must be audited first; PyProBE docs pair it with
   ORegan2022, not Chen2022 (compatibility to be checked).
3. **Battery Archive** LG M50 records — per the PRD this is a source of
   experimental cycling data/metadata, not a parameter database; candidate
   records must be checked against requirements §2 item by item.

## 5. Decision procedure (when a dataset is proposed)

1. Check every hard requirement in §2; record a compliance table.
2. Confirm cell identity matches Chen2020 scope (or justify a parameter-set
   switch as a scientific decision by the user).
3. Define the calibration/validation split in the run config *before* any
   fit.
4. Only then attach the dataset to the P5 experimental-validation milestone.
