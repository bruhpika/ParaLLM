# P5 Real-Data Fitting Experiment Design (Task 6)

**Design only — no calibration run is executed in P5.** Uses P2 sensitivity
results, P5 extraction/ablation results, and T5 data findings. Any future
execution must use the existing PyBaMM engine (`pybamm_engine/`), keep
calibration and validation data disjoint (rule 9), and treat calibrated values
as `calibrated` (never silently promoted; rule 5). PyBaMM 26.8.0.0 verified.

## Targets (primary) and rationale

| parameter (PyBaMM Chen2020 name) | baseline (Chen2020) | selection basis |
|---|---:|---|
| `Negative electrode active material volume fraction` | 0.75 | Drives capacity/stoichiometry utilization; directly bounded by electrode loading/porosity chain; extractable from literature with conditions — a practical first real-data target. |
| `Positive electrode active material volume fraction` | 0.665 | Paired capacity/voltage sensitivity; co-estimated with negative to avoid compensating stoichiometry errors. |

**Secondary (report, do not claim identified from a single discharge curve):**
`Positive particle diffusivity [m2.s-1]` (baseline 4e-15; P2 |S| 0.63–0.85
0.5C–2C, observable but rate/condition dependent) — only if a multi-rate
protocol and relaxation windows are available. `Negative particle diffusivity
[m2.s-1]` remains **unobservable at ≤2C** (P2 |S| 0.011–0.048) and must not be a
free target of a 0.5C–2C discharge fit. Electrolyte diffusivity ↔ exchange
current |corr|>0.8 (P2) — no joint identification from voltage alone.

## Data plan (from T5; execution blocked until acquired)

- **Required (blocking):** LG M50 BoL, 25 °C ± 1 K isothermal, CC-CV charge
  (documented), galvanostatic discharge **0.5C, 1C, 2C** over 2.5–4.2 V, plus a
  low-rate C/20–C/30 OCV reference; time-synchronized V/I/T; documented license
  and cell history. `data/registry/dataset_audit_lgm50.json` (PyProBE C/10 charge
  pOCV, 32.3 °C, license UNRESOLVED) is **ineligible** for this role.
- **Split (rule 9, fixed before fitting):** e.g. calibrate on {1C, 2C}
  discharge; hold out **0.5C** (and low-rate OCV/relaxation if present) as
  independent validation. Never report calibration fit as validation.
- **Preprocessing (deterministic):** align timestamps, enforce current sign
  convention, crop to 2.5–4.2 V window, resample to a fixed grid for RMSE,
  record capacity (Ah) per rate; reject/flag temperature excursions > ±1 K.

## Simulation / engine settings (deterministic, P0-consistent)

- Model: PyBaMM DFN (SPMe sensitivity cross-check optional), Chen2020
  `ParameterValues("Chen2020")`, isothermal 298.15 K, `Experiment` mirroring the
  acquired protocol exactly (CC-CV + rest + discharge C-rate). Solver/options as
  pinned in the repo (record `pybamm.__version__` 26.8.0.0 and full config hash
  in the run manifest).
- Bounds (physical, fixed a priori, documented): active material volume
  fractions in [0.3, 0.85] with porosity/volume-consistency checks against the
  paired inactive/porosity fractions (reject inconsistent combinations); if
  positive diffusivity is reported, log-scale bounds spanning the P2-feasible
  range only as a secondary diagnostic — do not promote to identified.
- Initial values: Chen2020 baselines (literature-derived, source Chen 2020). All
  other parameters held at Chen2020 baselines (recorded), provenance preserved.

## Fitting / selection procedure (when data unblocked)

1. **Identifiability gate (pre-fit):** confirm multi-rate sensitivity supports the
   chosen targets (P2: pos D responsive; neg D not). Fix unobservable/correlated
   parameters at baselines.
2. **Fit:** bounded least-squares on the calibration discharge voltage traces
   (+ optional capacity term), deterministic solver seeds/options recorded.
   LLM/agent output never overwrites parameters without deterministic validation
   and explicit approval (rule 10).
3. **Report:** per-rate voltage RMSE and capacity error on **calibration** and
   **held-out validation** separately; parameter values with bounds, qualifier
   `calibrated`, and full provenance; residual plots. Do not interpret as
   physical ground truth — identifiability ≠ validity (rule 7).

## Stop / failure criteria (do not proceed to claims)

- Data fails T5 eligibility (license, temperature/protocol mismatch, missing
  metadata) → stop, report blocker.
- Validation RMSE degrades or shows structured rate-dependent bias vs
  calibration → overfitting/structural mismatch; do not claim identification.
- Fitted volume fractions hit bounds or imply inconsistent electrode volume
  balance → reject fit, revisit assumptions.
- Any attempt to free negative diffusivity (≤2C) or a D_e–i0 pair from voltage
  only → flag as non-identifiable (P2).

## P5 evidence used

Retrieval-grounded extraction (T3) supplies literature priors/conflicts with
provenance (0.928) and zero false extractions on v3; memory-only claims are
treated as unsupported (T3/T4) and never used as priors without an archived
source. Chen2020 discrepancy baselines: `data/registry/chen2020_discrepancies.json`.

## Deliverable status

Experiment design documented; **calibration not run** (no eligible dataset in
repo, T5). Next executable step, once T5 is unblocked: implement the
pre-registered split + fitting script under `benchmarks/p5/` using the PyBaMM
engine, with a committed config and manifest, then validate on the held-out rate.
