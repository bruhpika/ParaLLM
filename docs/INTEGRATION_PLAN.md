# Integration Plan

Plan for integrating PyBaMM 26.8.0.0, PyBOP 26.10 and PyProBE-Data 2.6.1 into
the framework. **Not yet implemented** — this document is the proposal
awaiting scientific approval. Constraints honored: no reimplementation of
PyBOP optimizers or PyProBE data processing; no upstream source changes; P0
baseline preserved.

## 0. Environment strategy

- Integration baseline: **Python 3.12.16** (`.venv-ecosystem312` pattern),
  with `pybamm==26.8.0.0`, `pybop==26.10`, `PyProBE-Data==2.6.1`,
  `polars==1.44.2` — the only combination where all three coexist (verified).
- P0's `.venv` (3.14) stays untouched and remains the reference for baseline
  reproduction. Decision pending: whether the project's canonical `.venv`
  migrates to 3.12 or lanes stay split (recommendation: single 3.12 venv named
  `.venv` created fresh from `requirements/core.lock` at integration start; P0
  artifacts are version-locked and reproducible either way).
- Every new lockfile pins all three packages + polars + pints explicitly.

## Phase I1 — Environment & adapter skeleton

1. Create the canonical 3.12 environment; regenerate `requirements/core.lock`.
2. Add `data_ingest/` and `calibration/` adapter skeletons with typed contracts
   (`ObservationSet`, `FittingSpec`, `CalibrationReport`) from
   `docs/REVISED_ARCHITECTURE.md`.
3. Unit tests for contract validation only (no numerics yet).
4. Exit: tests pass in 3.12 env; P0 suite still passes unchanged.

## Phase I2 — PyBOP calibration adapter (replaces old P3 build plan)

1. Implement `calibration/pybop_adapter.py`:
   - registry `ParameterSetSnapshot` → `pybamm.ParameterValues` +
     `pybop.Parameter` declarations (bounds/priors from provenance records,
     transformations chosen per distribution-pairing rules);
   - `ObservationSet` → `pybop.Dataset` (column mapping:
     `Terminal voltage [V]` → `Voltage [V]`, verified names);
   - deterministic fits: `pybop.SciPyMinimize` (L-BFGS-B + `jac=True`) and
     `pybop.SciPyDifferentialEvolution` (seeded);
   - Bayesian fits: `pybop.LogPosterior` +
     `pybop.DifferentialEvolutionMCMC`/`NUTS` (`numpy.random` seeding, chain
     files persisted).
2. Synthetic recovery benchmark (old P3, now PyBOP-based): DFN/Chen2020 ground
   truth, 2–3 hidden parameters, multiple initial guesses, fixed-duration
   protocols. Benchmarks under `benchmarks/parameter_recovery/`.
3. Exit: recovery benchmark report; `CalibrationReport` with objective,
   bounds, convergence, seeds, upstream versions.

## Phase I3 — Diagnostics & identifiability (old P4, revised)

1. Wrap `pybop.classify_using_hessian` for the 2-parameter case.
2. Sensitivity via PyBaMM sensitivities + SALib Sobol (direct, per upstream
   26.10 guidance).
3. Implement our FIM-based practical identifiability + profile likelihood for
   N>2 (genuinely missing upstream).
4. Exit: `IdentifiabilityReport` that flags weakly constrained parameters
   (rule 7: never infer identifiability from optimizer convergence).

## Phase I4 — PyProBE data lane (old P5, revised)

1. `data_ingest/pyprobe_adapter.py`: `Cell.import_from_cycler`/`import_data`
   → `ObservationSet` with metadata + dataset roles (calibration vs
   validation, rule 9).
2. Use `pybamm_experiment` strings to define fitting experiments; validate
   them through PyBaMM at config time.
3. Experimental validation benchmark with a documented public dataset (cell,
   chemistry and protocol must match our parameter set — the NMC622 sample
   cell is for plumbing only).
4. Exit: held-out prediction report (calibration/validation split enforced).

## Phase I5 — Literature & provenance layer (old P6, unchanged scope)

1. Corpus ingestion/retrieval (`literature/`), extraction schema
   (`extraction/`) feeding `parameter_registry/`.
2. Validation layer enforcing units/conditions/conflicts before any value can
   reach `FittingSpec`.
3. Exit: expert-reviewed extraction benchmark; provenance-complete records.

## Phase I6 — Closed loop (old P7)

1. Discrepancy diagnosis → `EvidenceRequest` (targeted retrieval) or
   `RecalibrationRequest` (bounded PyBOP rerun) or human review.
2. Iteration audit log, stopping rules, no unbounded loops.
3. Exit: auditable end-to-end demonstration.

## Phase I7 — Fine-tuning study (old P8, unchanged, optional)

Requires remote GPU; A/B/C/D ablation per PRD. Not blocking any other phase.

## Mapping to PRD milestones

| PRD | Status | Revised owner |
|---|---|---|
| P0 Baseline | ✅ done | our `pybamm_engine` |
| P1 Parameter registry | next | ours (PyBOP has no provenance) |
| P2 Synthetic generator | folded into I2 | PyBOP `Dataset`/`add_noise` + our ground-truth bookkeeping |
| P3 Inverse estimation | I2 | PyBOP optimizers |
| P4 Identifiability/UQ | I3 | PyBOP Hessian + ours (FIM/profile/SALib) |
| P5 Experimental validation | I4 | PyProBE ingest + PyBOP fit + our split enforcement |
| P6 Literature extraction | I5 | ours |
| P7 Closed loop | I6 | ours |
| P8 Fine-tuning | I7 | ours (domain adaptation) |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| PyBaMM drift breaks PyBOP (no upper pin) | Keep `pybamm==26.8.0.0` pinned; upgrade only after running the full probe suite (`scripts/compat_probe/`) |
| PyBOP API churn (v25.10-style restructures) | Pin `pybop==26.10`; adapter isolates PyBOP surface to `calibration/pybop_adapter.py` |
| PyProBE Python ≤3.12 cap | Integration baseline 3.12 (verified); revisit only if upstream lifts the cap |
| PINTS samplers unseeded | Seed `numpy.random` explicitly; record seeds in `CalibrationReport` (rule: reproducibility) |
| Event-terminated protocols in configs | `FittingSpec` validation rejects `until <voltage>` steps for fitting; baseline configs unaffected |
| Mismatched cell/chemistry data silently fitted | `ObservationSet` metadata must match `specifications.CellSpec` before `Problem` construction (rules 4–6) |

## Open questions for the scientific decision-maker

1. Confirm environment decision: migrate canonical `.venv` to Python 3.12
   (recommended) or keep split lanes?
2. First fitting demonstrator: keep Chen2020/LG M50 as the P2/P3 target cell?
3. Which 2–3 parameters to target first in I2 (e.g. electrode active-material
   volume fractions as in the canonical PyBOP example, or diffusion
   coefficients)?
4. Which public experimental dataset for I4 (must match chemistry/cell)?
5. Priority between I5 (literature) and I2–I4 (numerics) for the next
   milestone?
