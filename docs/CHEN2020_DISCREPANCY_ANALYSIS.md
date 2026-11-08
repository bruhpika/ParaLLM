# P4 — Chen2020 discrepancy analysis (Part C)

Artifact: `data/registry/chen2020_discrepancies.json`, built
programmatically by `scripts/p4/chen2020_discrepancies.py` from the P3
registry (nothing hand-entered; every value/quote/condition/uncertainty is
pulled from registry records at build time). The analysis documents
discrepancies; it does NOT change any registry value or the installed
parameter set.

## Why this matters

The P0/P2 synthetic campaigns recover PyBaMM's *operative* values. The
registry records that several of those operative values are the paper's
*TUNED* values (Table IX iterations), not the measured/GITT-derived
ones (Tables V/VII) — recovering them from synthetic data proves the
calibration works, not that the underlying electrochemistry is recovered
(AGENTS.md rule 7).

## Head-line numbers (pybamm_value / paper_value, from the artifact)

| parameter | PyBaMM operative | paper reported | ratio | causes |
|---|---|---|---|---|
| Negative particle diffusivity [m2.s-1] | 3.3e-14 | 1.74e-15 ± 4.10e-15 (Table V, GITT/Sand) | 19.0 | calibration, operating_conditions |
| Positive particle diffusivity [m2.s-1] | 4e-15 | 1.48e-15 ± 1.05e-15 (Table V) | 2.70 | calibration, operating_conditions |
| Neg maximum concentration [mol.m-3] | 33133 | 29583 (Table VII; body text 29603) | 1.12 | calibration, source_conflict |
| Pos maximum concentration [mol.m-3] | 63104 | 51765 (Eq. 5) | 1.22 | calibration |
| Bruggeman (neg/pos/sep electrodes) | 1.5 each | 2.91 / 2.43 / 2.57 measured | 0.52–0.62 | model_assumption, calibration |

Unit-convention-only cases (no numeric discrepancy): active-material volume
fractions (75%/66.5% ≡ 0.75/0.665), separator porosity (47% ≡ 0.47), and the
verified naming inversion `Electrode width [m] = 1.58 m = paper "Electrode
length"` ((`cell_electrode_width`), `definition` cause).

## Key structural findings

1. **The big diffusivity gaps are calibration artifacts, not measurement
   errors.** The paper itself tunes effective diffusivities per C-rate
   (negative electrode: 1.3e-14 / 3.3e-14 / 6.3e-14 m2 s-1 at C/2 / 1C /
   1.5C — recorded in the registry conflict context) and states that
   measured 1.5 Bruggeman values give unphysical electrolyte depletion —
   i.e. a deliberately simplified single-value transport model. Any
   "estimation" target built on the PyBaMM set inherits these choices.
2. **Set extensions (16 families).** The PyBaMM Chen2020 set contains an SEI
   growth block, double-layer capacities, total heat transfer coefficient
   and contact resistance that the paper never parameterizes (the docs
   describe the SEI values as example values). These are `set_extension`
   entries; the SEI docs quote distinguishes "example parameters".
3. **P2 linkage (recorded, not re-derived).** Negative diffusivity is not
   estimable from voltage-only data at ≤2C (|S| 0.011–0.048) — the 19×
   calibration gap above was never testable with that observation set.
   Positive diffusivity is the promising target (S 0.63–0.85
   multi-C). Electrolyte diffusivity ↔ reaction rate collinearity (|corr| >
   0.8) blocks separate recovery. Short-chain MCMC posteriors (rhat 1.10-1.26)
   are directional only and are NOT used as evidence in the artifact.
4. **j0 representation.** The scalar Table VII reaction rates
   (3.42e-6 / 6.48e-7 A m-2 (m3 mol-1)^1.5) are embedded in PyBaMM's
   concentration-dependent j0 closures rather than carried by scalar
   parameters; the docs' "reference exchange-current density 5 / 2.7
   A.m-2" claims an equivalence in form but the EIS-measured values
   (Table VI: 0.28–0.602 mA cm-2, 25–60 °C) are the paper's actual
   measurements. Recorded as documentation-vs-paper conflict, preserved.

## Limitations

- Cause tags are documented expert judgment, not measurements.
- Text-vs-table variants (29583 vs 29603) and the supplement-vs-main-text
  separator porosity (46/46/48% vs 47%) are preserved, not averaged.
- The artifact links only to what the registry stores; it deliberately does
  not restate C-rate diffusivities outside the registry (single-source
  provenance policy).
