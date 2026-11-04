# Identifiability Study

Phase P2 / TASK 4. Diagnostics for the electrode active-material volume
fraction pair (neg ε_s, pos ε_s) on DFN/Chen2020 synthetic data.

**Rule 7 compliance:** optimiser convergence is never used as evidence of
identifiability. Every claim below is backed by a quantitative diagnostic.

Reproduce:

```bash
.venv-ecosystem312/bin/python benchmarks/identifiability/run_identifiability.py \
    --config configs/p2/identifiability.yaml --out results/p2
```

Artifacts: `results/p2/identifiability_volume_fractions/` (`report.json`,
`summary.md`, `profile_likelihood.png`, `bootstrap_scatter.png`,
`sobol_single.png`, `sobol_multi.png`, `mcmc_posterior.png`).

Evaluation point for all local diagnostics: single-condition refit
x̂ = (0.74116, 0.66939); truth = (0.75, 0.665); noise σ = 2 mV.

## 1. Methods selected and rationale

| Method | Source | Why selected | Limitation |
|---|---|---|---|
| Hessian classification | PyBOP `classify_using_hessian` (2-param supported case) | Curvature/correlation at the optimum; exactly our N=2 case | finite-difference, local; PyBOP caps it at 2 parameters |
| FIM + correlation from FD Jacobian | own (`calibration/identifiability.py`) | Local practical identifiability; works for any N | linearisation around x̂ |
| Profile likelihood | own | Non-linear identifiability; reveals boundedness and ridges | coarse grid (11 points/param), one parameter re-optimised |
| Parametric bootstrap (n=20) | own | Sampling variability under known noise; bias check | few replicates; same-model generation |
| Sobol indices (SALib Saltelli, N=64) | SALib 1.6.0 direct (PyBOP removed its wrapper in v26.10) | Global sensitivity, interaction detection | moderate sample size; box-bounded inputs |
| MCMC posterior | PyBOP `LogPosterior` + `DifferentialEvolutionMCMC` | Joint uncertainty + posterior correlation | short chains (see convergence caveat) |

Not used: profile-likelihood confidence intervals calibrated by Δχ²
thresholds (not implemented); the removed PyBOP FIM (`observed_fisher`
deleted in v25.10).

## 2. Results

### 2.1 PyBOP Hessian classification (2-parameter supported case)

| Data | PyBOP message | Eigenvalues (cost units) |
|---|---|---|
| 1C only | "The optimiser has located a minimum. **There may be a correlation between these parameters.**" | 0.25, 5.60 (ratio ≈ 22) |
| 0.5C+1C+2C | "The optimiser has located a minimum." (no correlation warning) | 0.69, 25.2 (ratio ≈ 37) |

Multi-condition data strengthens curvature along the weak direction
(0.25 → 0.69) and removes the correlation warning.

### 2.2 FIM / correlation from finite-difference Jacobians

| Quantity | 1C only | 0.5C+1C+2C |
|---|---|---|
| correlation (neg, pos) | **−0.756** | **−0.815** |
| singular values | 1.66, 0.36 | 3.52, 0.59 |
| FIM condition number | 21.6 | 35.5 |
| mean \|norm. sensitivity\| (neg, pos) | 0.61, 1.18 | 0.37, 0.83 |

Honest reading: the *correlation* stays ≈ −0.8 in both designs (the
trade-off ridge is intrinsic to the pair), but multi-condition data roughly
**doubles the information along the weak direction** (sv 0.36 → 0.59) and
puts more total information in the strong direction. The higher condition
number reflects the faster growth of the strong direction, not degradation.

### 2.3 Profile likelihood (1C, 11 grid points each, other parameter re-fit)

- **neg ε_s** (grid 0.59–0.89): profiled cost has a smooth single minimum at
  0.741 and rises on both sides (0.00024 at min → 0.0040/0.0028 at the ends).
  The re-fitted pos ε_s drifts monotonically 0.72 → 0.64 along the grid — the
  visible trade-off ridge.
- **pos ε_s** (grid 0.54–0.80): clear minimum at 0.669; cost rises steeply
  toward 0.54 (0.048) while the re-fitted neg ε_s saturates at its bounds
  (0.90/0.55) — outside the ridge the pair cannot compensate.

**Conclusion:** both parameters are *locally identifiable* from the 1C
window; joint confidence regions are elongated along the ridge.

### 2.4 Parametric bootstrap (n=20 re-noise-and-refit)

| Parameter | mean | std | min–max | truth | bias |
|---|---|---|---|---|---|
| neg ε_s | 0.7489 | 0.0055 | 0.7352–0.7566 | 0.75 | −0.0011 |
| pos ε_s | 0.6652 | 0.0023 | 0.6619–0.6711 | 0.665 | +0.0002 |

Bootstrap estimate correlation: **−0.818**. At σ = 2 mV over the 900 s
window, one-sigma sampling errors are ≈ 0.7 % (neg) and 0.35 % (pos) of
value; bias is small compared to spread.

### 2.5 Sobol indices (Saltelli N=64 → 256 model runs per design)

| Design | S1 neg | S1 pos | ST − S1 (interactions) |
|---|---|---|---|
| 1C | 0.343 | 0.646 | < 0.005 |
| 3 C-rates | 0.314 | 0.676 | < 0.005 |

Voltage is dominated by pos ε_s sensitivity; parameter interactions are
negligible in this box (bounds of the fit). Per-time curves in
`sobol_single.png`/`sobol_multi.png` show S1 growing through the discharge.

### 2.6 MCMC posterior (DifferentialEvolutionMCMC, 3 chains × 400 iters + 200 warm-up)

Setup: `GaussianLogLikelihood(σ = 2 mV)` → `LogPosterior`; 1200 evaluations,
25 s; `numpy.random` seeded 77 (PINTS samplers expose no seed option).

| Quantity | neg ε_s | pos ε_s | sigma* |
|---|---|---|---|
| posterior mean | 0.7374 | 0.6709 | 0.00272 |
| posterior std | 0.0114 | 0.0038 | 0.00026 |
| 95 % CI | [0.718, 0.755] | [0.664, 0.677] | [0.00185, 0.00290] |
| truth | 0.75 (inside CI) | 0.665 (inside CI) | 0.002 (at CI edge) |

Posterior correlation (neg, pos) = **−0.85**.
r̂ = [1.26, 1.10, 1.16] — **chains are not fully converged** at this length
(PINTS note: bounds are ignored by samplers; out-of-bounds proposals get
infinite cost). The posterior is indicative of the ridge geometry and
interval scale only; longer chains are required for publishable UQ.

\* API finding: `pybop.GaussianLogLikelihood` promotes σ ("Sigma for output
1") to a sampled parameter (mean 0.0027 ± 0.0003 for true σ = 0.002), and
`MetaProblem` de-duplicates it across conditions.

## 3. Conclusions

1. **Locally practically identifiable (idealized conditions):** with
   noise-free model structure, σ = 2 mV noise and a 900 s 1C window, the pair
   is recoverable to ≈ 1 % (neg) and ≈ 0.5 % (pos) relative error; both
   profiles are bounded; posterior contains the truth.
2. **Jointly correlated (−0.75 to −0.85):** every method agrees on the
   trade-off ridge. Report joint confidence regions, never independent error
   bars alone.
3. **Multi-condition (0.5C/1C/2C) helps** by strengthening the weak
   direction (sv 0.36 → 0.59), improving recovery ~10–25 %, and removing the
   Hessian correlation warning — but it does not eliminate the ridge.
4. **Not demonstrated:** identifiability under model-form error or on real
   cells (rule 8); tolerance to parameter-set bias; robustness to other
   noise levels/seeds.

## 4. Additional observations that would strengthen identifiability

- Longer windows / full discharge (more SOC coverage of the OCV curvature).
- A low-rate (C/20 or C/30) reference run to pin stoichiometry endpoints.
- Pulse/GITT segments for diffusion/kinetics separation (see
  `docs/PARAMETER_SELECTION.md`).
- Repeated runs per condition to estimate the true noise level.
