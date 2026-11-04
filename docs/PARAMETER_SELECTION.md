# Parameter Selection Study

Phase P2 / TASK 2 (volume-fraction pair verification) and TASK 5
(diffusivity feasibility). All names/values were verified against the
installed PyBaMM 26.8.0.0 / Chen2020 parameter set; nothing here is assumed
from memory (scientific rules 2–3).

## 1. Candidate pair: electrode active-material volume fractions (TASK 2)

### 1.1 Exact parameter names (verified)

| PyBaMM key (Chen2020) | Value | Type |
|---|---|---|
| `Negative electrode active material volume fraction` | 0.75 | scalar, dimensionless |
| `Positive electrode active material volume fraction` | 0.665 | scalar, dimensionless |

Verified by reading `pybamm.ParameterValues("Chen2020")` and by round-tripping
both keys through `pybop.Parameter` declarations (`scripts/compat_probe/exp3`,
`tests/unit/test_calibration_fitting.py`).

### 1.2 Physical definition and role in the DFN

The active-material volume fraction ε_s is the fraction of the electrode
(control) volume occupied by active-material particles. In the DFN it sets:

- the volumetric interfacial surface area a = 3ε_s / R_p (reaction area per
  electrode volume; R_p = particle radius), and
- the electrode's lithium-storage capacity (stoichiometry limits × ε_s).

Units: dimensionless (fraction, not percent). In Chen2020 the electrodes
contain no explicit binder/filler fraction: ε_s + ε = 1 exactly
(neg: 0.75 + 0.25 porosity; pos: 0.665 + 0.335 porosity).

### 1.3 Compatibility with Chen2020

Both keys exist as plain scalars in the Chen2020 set (93 entries) and are read
by the default DFN. Bounds of [0.55, 0.90] / [0.45, 0.80] keep estimates
physically plausible (volume fractions must stay in (0,1) and consistent with
electrode porosity). No definition conflicts with other Chen2020 parameters.

### 1.4 Sensitivity to the selected observables (measured)

From the Sobol study (`results/p2/identifiability_volume_fractions/`,
voltage windows 0.5C–2C):

| Quantity | neg. ε_s | pos. ε_s |
|---|---|---|
| Sobol S1 mean (1C window) | 0.34 | 0.65 |
| Sobol S1 mean (3-C windows) | 0.31 | 0.68 |
| mean \|normalized sensitivity\| (1C) | 0.61 | 1.18 |

Both parameters visibly shape the voltage transient; the positive-electrode
fraction dominates. Interactions (ST − S1) are small.

### 1.5 Can they be estimated together? (measured)

Yes, with a documented caveat:

- Recovery is stable from all tested initial guesses (TASK 1/3 benchmark).
- The two are **correlated**: correlation −0.76 (FIM, 1C) / −0.85 (MCMC
  posterior) / −0.82 (bootstrap) — a trade-off ridge (larger neg ε_s can be
  partially compensated by smaller pos ε_s).
- Profile likelihoods are bounded on both sides for both parameters at
  realistic costs — each parameter is *locally* constrained, but the ridge
  inflates joint uncertainty.
- Multi-condition data (0.5C/1C/2C) improves the weak direction and removes
  PyBOP's Hessian correlation warning.

**Verdict: approved as the first estimation pair.** They are the standard
first pair in the PyBOP examples for a reason (Hallemans et al. 2025): they
are among the best-constrained electrode parameters from voltage data.

## 2. Deprecated-name warning (verified API finding)

PyBaMM 26.8 renamed the solid diffusivities:

| Deprecated alias (still readable) | Current name | Chen2020 value |
|---|---|---|
| `Negative electrode diffusivity [m2.s-1]` | `Negative particle diffusivity [m2.s-1]` | 3.3e-14 |
| `Positive electrode diffusivity [m2.s-1]` | `Positive particle diffusivity [m2.s-1]` | 4e-15 |

Both aliases resolve to the same value on read; writing through the
deprecated name emits a `UserWarning`. **All P2+ code uses the current
names.** (`docs/P0_BASELINE_MODEL.md` lists values under the deprecated
read alias; the values themselves are correct.)

## 3. Diffusivity feasibility study (TASK 5 — no estimation performed)

Method: normalized finite-difference sensitivity of the DFN voltage to a ±2 %
scale factor on each transport/kinetic parameter (function parameters scaled
in memory; never persisted), over the 0.5C/1C/2C windows
(`benchmarks/identifiability/diffusivity_feasibility.py`).

### 3.1 Sensitivity of voltage (mean |normalized sensitivity|)

| Parameter | 0.5C | 1C | 2C | Verdict |
|---|---|---|---|---|
| Negative particle diffusivity | 0.011 | 0.021 | 0.048 | **effectively unobservable** |
| Positive particle diffusivity | 0.63 | 0.82 | 0.85 | **strongly observable** |
| Electrolyte diffusivity (function) | 0.23 | 0.46 | 1.25 | observable, esp. ≥2C |
| Neg. exchange-current density (function) | 0.72 | 0.68 | 0.49 | strong at low C |
| Pos. exchange-current density (function) | 0.13 | 0.23 | 0.33 | weak–moderate |

Physical reading: the graphite particle diffusion time constant
(R²/D ≈ 1 s) is far shorter than the 450–1800 s windows, so the graphite
particle stays nearly uniform — its diffusivity cannot be seen in voltage at
≤2C. The NMC particle (R²/D ≈ 7 s) develops visible gradients, especially at
2C.

### 3.2 Correlation with kinetic parameters (measured)

Sensitivity-vector correlations (0.5C+1C+2C combined):

| Pair | corr (1C only) | corr (3 C-rates) |
|---|---|---|
| neg D vs neg i0 | **−0.94** | −0.50 |
| pos D vs pos i0 | +0.39 | +0.32 |
| electrolyte D vs neg i0 | −0.73 | **−0.83** |
| electrolyte D vs pos i0 | +0.39 | **+0.87** |
| neg i0 vs pos i0 | +0.13 | **−0.90** |
| neg D vs pos D | +0.75 | +0.58 |

Conditioning of the joint sensitivity matrix (singular values, smallest
first): 1C-only 5-param block is nearly rank-deficient (sv = 0.013,
cond ≈ 470); with three C-rates sv_min rises to 0.17 (cond ≈ 64).

### 3.3 Do multiple C-rates improve discrimination?

**Yes, substantially** — multi-C data roughly halves the neg-D/neg-i0
correlation (−0.94 → −0.50), lifts the weakest sensitivity direction by an
order of magnitude, and is the only way electrolyte diffusivity becomes
visible. However, electrolyte D ↔ exchange-current density correlations
remain strong (|corr| > 0.8) even with three C-rates, and the two
exchange-current densities become strongly anti-correlated with each other
(−0.90) once multi-rate data are combined.

### 3.4 Recommendation for subsequent experiments

| Parameter | Recommendation |
|---|---|
| Negative particle diffusivity | **Do not estimate** from voltage data at ≤2C. Keep Chen2020 value, status `literature_derived`. Would need high-rate pulses/GITT where graphite gradients matter. |
| Positive particle diffusivity | **Good candidate** for the next estimation experiment (strong sensitivity, moderate correlations), ideally with ≥2C data and longer SOC windows. |
| Electrolyte diffusivity | **Only with constraints**: estimate alone while kinetic parameters are fixed by literature priors, or jointly only with additional observables (EIS, GITT/pulse, concentration-sensitive data). Never jointly with both exchange-current densities from voltage alone. |
| Exchange-current densities (both) | Voltage-only fits cannot separate the pair (−0.90); estimate one with the other fixed, use grouped/linked parameters (PyBOP `GroupedSPMe`-style), or add EIS. |

Additional observables that would break the remaining trade-offs (see
`docs/EXPERIMENTAL_DATA_REQUIREMENTS.md`): GITT/pulse relaxation (diffusion),
EIS at fixed SOC (kinetics + electrolyte), CV segments, and temperature
variation (Arrhenius separation).

## 4. Summary — what is suitable to estimate

1. **Suitable now (voltage-only, synthetic-validated):** the electrode
   active-material volume-fraction pair (TASK 1/3 benchmark; errors 0.5–1.2 %
   at σ = 2 mV).
2. **Suitable next:** positive particle diffusivity, with multi-C data.
3. **Conditionally suitable:** electrolyte diffusivity (with fixed/prior
   kinetics), one exchange-current density at a time.
4. **Not suitable from voltage alone:** negative particle diffusivity;
   both exchange-current densities jointly.
