# P0 Baseline: DFN Model with the Chen2020 Parameter Set

This document explains the physical model, the parameter set, the numerical
configuration and the scientific limitations of the P0 baseline. All values
below were read from the pinned installed PyBaMM (26.8.0.0); nothing is
hand-typed from memory.

## 1. Model

**Doyle–Fuller–Newman (DFN)** lithium-ion model (`pybamm.lithium_ion.DFN()`),
PyBaMM's "Doyle-Fuller-Newman model" with default options:

- Newman porous-electrode theory: solid-phase diffusion in spherical active
  particles (Fickian), concentrated-solution electrolyte transport, Butler–Volmer
  intercalation kinetics at particle surfaces.
- Isothermal (fixed 298.15 K — no thermal model in P0), no SEI, no lithium
  plating, no degradation, 0+1D (uniform current collectors), single particle
  phase, spherical particles.
- The effective options dictionary of the built model is recorded in the run
  manifest (`options_effective`) so the exact configuration is auditable.

## 2. Parameter set: Chen2020 (commercial LG M50 cell)

Shipped with PyBaMM (`pybamm.parameter_sets["Chen2020"]`, 93 entries). Source:

> Chen, C.-H., Brosa Planella, F., O'Regan, K., Gastol, D., Widanage, W. D.,
> Kendrick, E. "Development of Experimental Techniques for Parameterization of
> Multi-scale Lithium-ion Battery Models." *J. Electrochem. Soc.* **167** (8),
> 080534 (2020). DOI: 10.1149/1945-7111/ab9050

(citation string verified in the installed package's `CITATIONS.bib`.)

### Physical meaning of key parameters (verified values)

**Geometry / cell**

| Parameter | Value | Meaning |
|---|---|---|
| Nominal cell capacity | 5.0 A.h | Commercial LG M50 pouch-cell rated capacity |
| Electrode height / width | 0.065 m / 1.58 m | Coated electrode dimensions (tall jelly-roll format) |
| Negative (graphite) electrode thickness | 8.52e-5 m | Through-cell thickness of the graphite electrode |
| Positive (NMC) electrode thickness | 7.56e-5 m | Through-cell thickness of the NMC electrode |
| Separator thickness | 1.2e-5 m | Porous separator between electrodes |

**Electrode microstructure**

| Parameter | Value | Meaning |
|---|---|---|
| Negative/positive particle radius | 5.86e-6 / 5.22e-6 m | Mean radii of spherical active-material particles (sets solid diffusion time scale) |
| Negative/positive active-material volume fraction | 0.75 / 0.665 | Fraction of electrode volume occupied by active material |
| Negative/positive/separator porosity | 0.25 / 0.335 / 0.47 | Void volume fraction filled with electrolyte (ion transport) |

**Thermodynamics (stoichiometry)**

| Parameter | Value | Meaning |
|---|---|---|
| Max concentration in negative / positive electrode | 33133 / 63104 mol.m-3 | Saturation limit of lithium in graphite / NMC (fixed by crystal structure) |
| Initial concentration in negative / positive electrode | 29866 / 17038 mol.m-3 | Cell state at start of the run; sets initial SOC (≈ fully charged) |
| Initial electrolyte concentration | 1000 mol.m-3 | Bulk Li+ concentration in the electrolyte (≈ 1 M) |

**Transport and kinetics**

| Parameter | Value | Meaning |
|---|---|---|
| Negative/positive electrode diffusivity | 3.3e-14 / 4e-15 m2.s-1 | Solid-phase (particle) lithium diffusivity; graphite ≫ NMC |
| Electrolyte diffusivity | function (`electrolyte_diffusivity_Nyman2008`) | Concentration-dependent (Nyman 2008 correlation) |
| Negative/positive electrode conductivity | 215 / 0.18 S.m-1 | Effective electronic conductivity of the solid matrix |
| Charge transfer coefficient (both) | 0.5 | Symmetric Butler–Volmer kinetics |
| Exchange-current density (both) | functions (`..._Chen2020`) | Concentration-dependent intercalation kinetics for graphite / NMC |
| Thermodynamic factor | 1.0 | Electrolyte activity correction |

**Operating envelope**

| Parameter | Value | Meaning |
|---|---|---|
| Initial / ambient / reference temperature | 298.15 K | Isothermal operation at 25 °C |
| Lower / upper voltage cut-off | 2.5 V / 4.2 V | Cell safety/operating limits; discharge terminates at the lower cut-off |

Note: several transport/kinetic parameters are Python functions of
concentration/temperature, not constants. The run manifest's
`parameter_snapshot.json` records them as `<callable:name>` — it documents what
was used without fabricating numbers.

## 3. Numerical configuration

| Item | Value |
|---|---|
| Solver | `pybamm.IDAKLUSolver` (Sundials IDA), rtol = atol = 1e-6 |
| Experiment | `pybamm.Experiment(["Discharge at 1C until 2.5 V"])` — galvanostatic 5 A |
| Random seed | `null` — deterministic DAE solve, no stochastic component |
| Version pin | `pybamm==26.8.0.0`, enforced at runtime (`VersionMismatchError`) |

Solver note: `pybamm.CasadiSolver` is deprecated in 26.8 and takes ~42 s for
this experiment versus ~0.4 s for IDAKLU; IDAKLU is the default everywhere in
this project.

## 4. Baseline result (reproducible)

- Termination: `event: Voltage < 2.5 [V] [experiment]`
- Simulated span: 0 → 3555.5 s (293 saved points)
- Capacity extracted ≈ 4.94 A.h (≈ 98.8 % of nominal 5.0 A.h at 1C/25 °C)
- Voltage: 4.038 V (start) → 2.500 V (cut-off)

Regenerate with:

```bash
.venv/bin/python scripts/run_baseline.py --config configs/baseline_dfn.yaml --out results/baseline
.venv/bin/python scripts/plot_baseline.py --results results/baseline --figures results/figures
```

Outputs: `results/baseline/` (solution arrays, run manifest, parameter
snapshot, extraction metadata) and `results/figures/` (voltage/current,
concentrations, electrode potentials).

## 5. Scientific limitations of the baseline

1. **Not an experimental validation.** The run verifies the *implementation*
   (model solves, outputs extract, runs are reproducible). It says nothing
   about whether Chen2020 parameters predict any particular measured cell.
2. **Isothermal.** Temperature is fixed at 298.15 K; no thermal model, no
   self-heating, no temperature-dependent validation.
3. **No degradation.** SEI growth, lithium plating, LAM and stress are all
   off; the baseline describes a fresh cell at room temperature only.
4. **Parameter set is literature-derived, not user-calibrated.** Chen2020
   values are used exactly as shipped with PyBaMM. Their status in this
   project is `literature_derived`; none are calibrated here.
5. **Simplified geometry.** 0+1D with uniform current collectors; no jelly-roll
   or pouch geometry effects, no cell-level thermal gradients.
6. **One operating condition.** A single 1C discharge at 25 °C; no C-rate or
   temperature variation, no charge/discharge cycling.
7. **Model-form uncertainty is unquantified.** The DFN equations themselves are
   an idealisation (single particle phase, Bruggeman transport, Fickian solid
   diffusion); a good voltage fit would not prove the model form is correct.
8. **Function-based parameters are not snapshotted numerically.** They are
   recorded by name in `parameter_snapshot.json`; reproducing the run requires
   the same PyBaMM version (which is exactly what the pin enforces).

## 6. What is intentionally absent (per PRD scope)

- No LLM components, no literature extraction (P6).
- No inverse estimation or calibration (P3+).
- No synthetic data generation (P2).
- No claims about parameter identifiability.
