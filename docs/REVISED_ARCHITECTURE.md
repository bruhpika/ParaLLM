# Revised Architecture

Revision of `docs/ARCHITECTURE.md` after the ecosystem audit
(`docs/ECOSYSTEM_AUDIT.md`). The four-module conceptual architecture is
unchanged; the implementation boundary moves: numerical estimation and data
processing are delegated to upstream packages, and our codebase focuses on the
research-specific intelligence, provenance and validation layers.

## 1. Boundary: upstream vs. ours

```
┌──────────────────────────────────────────────────────────────────────┐
│ OUR RESEARCH LAYER (pybamm_closed_loop)                              │
│                                                                      │
│  literature/   extraction/   parameter_registry/   validation/       │
│  (retrieval)   (LLM→schema)  (provenance model)    (deterministic)   │
│                              specifications/  closed_loop/  reporting/
└───────────────┬──────────────────────────────┬───────────────────────┘
                │ ParameterSetSnapshot         │ observations
                │ (validated, provenanced)     │ (PyProBE Result)
┌───────────────▼──────────────┐  ┌────────────▼───────────────────────┐
│ UPSTREAM: PyBOP 26.10        │  │ UPSTREAM: PyProBE-Data 2.6.1       │
│ Dataset • Simulator • Problem│  │ Cell/Procedure/Experiment/Cycle/   │
│ costs • SciPy/PINTS optim.   │◄─┤ Step filters • cycling.summary     │
│ LogPosterior + MCMC          │  │ pybamm_experiment bridge           │
│ classify_using_hessian       │  └────────────────────────────────────┘
│ GroupedSPM/SPMe • EISSim.    │
└───────────────┬──────────────┘
        ┌───────▼────────┐
        │ UPSTREAM:      │
        │ PyBaMM 26.8.0.0│  (pinned; wrapped by our pybamm_engine for
        └────────────────┘   standalone baseline/synthetic runs)
```

Only `pybamm_engine/` and the calibration adapter may import PyBaMM/PyBOP
directly; only the data adapter may import PyProBE. Everything else exchanges
typed records (Pydantic) and numpy arrays.

## 2. Module revision

| Package (ours) | Revision | Status |
|---|---|---|
| `pybamm_engine/` | **Keep as-is (P0).** Standalone pinned simulation + extraction + manifests. In fitting flows, PyBOP's `pybop.pybamm.Simulator` is used instead (it must own the `pybop.Parameter` substitution). | done (P0) |
| `parameter_registry/` | **Unchanged in scope, now clearly non-redundant:** PyBOP has no provenance; we own parameter records (source, location, original/normalized values, conditions, status, validation history). Registry exports feed PyBOP as `pybamm.ParameterValues` + `pybop.Parameter` declarations. | P1 |
| `validation/` | **Unchanged in scope:** unit/condition normalization, plausibility, conflict preservation. Runs *before* anything reaches PyBOP. | P1/P6 |
| `literature/`, `extraction/` | **Unchanged:** retrieval + LLM extraction into strict schema. Pure research layer. | P6 |
| `calibration/` | **Shrink to an adapter.** No optimizers of our own (restriction): builds `pybop.Dataset` from observations (PyProBE output or synthetic), declares `pybop.Parameter`s from registry records (bounds/priors from literature), runs `pybop.SciPyMinimize`/`SciPyDifferentialEvolution`/`LogPosterior`+samplers. Records seeds (`numpy.random` where PINTS lacks seed options). | P3 (revised) |
| `diagnostics/` | **Split:** sensitivity → SALib directly (PyBOP removed its wrapper) + PyBaMM sensitivities; Hessian classification → `pybop.classify_using_hessian` (2 params); **identifiability for N>2 (FIM, profile likelihood, correlations) remains ours** — PyBOP removed its FIM and has no profile likelihood. | P4 (revised) |
| `closed_loop/` | **Unchanged:** discrepancy diagnosis, evidence requests, controlled recalibration via the calibration adapter, iteration audit, stopping rules. | P7 |
| `specifications/` | Unchanged: cell/model/condition specs. | P1 |
| `reporting/` | Unchanged: manifests; extended later to include PyBOP/PyProBE versions and results. | done (P0, ext.) |
| NEW `data_ingest/` (thin) | Adapter over PyProBE: `Cell`/filter chains → our observation records (`Time [s]`, `Current [A]`, `Voltage [V]`, metadata, dataset role: calibration vs validation). Never reimplements cycler parsing. | P5 (revised) |

## 3. Contract revisions (typed interfaces)

| From → To | Contract | Notes |
|---|---|---|
| registry → calibration | `FittingSpec`: parameter names, bounds/priors (→ `pybop.Parameter`), status must be `literature_derived`/`user_supplied`/`assumed` (flagged) | Provenance must exist before fitting (rule 4/5) |
| data_ingest → calibration | `ObservationSet`: arrays + metadata + role ∈ {calibration, validation} | From PyProBE `.get()`; roles enforced (rule 9) |
| calibration → PyBOP | `pybop.Dataset` + `pybop.Problem` + optimiser/sampler config | Boundary of upstream code |
| calibration → reporting | `CalibrationReport`: estimates, bounds, objective, convergence, seeds, upstream versions | |
| diagnostics → closed_loop | `IdentifiabilityReport`: sensitivity ranks, correlations, Hessian classification (if N=2), FIM/profile results (ours), "weakly identifiable" verdicts | Rule 7: optimiser convergence ≠ identifiability |
| closed_loop → literature | `EvidenceRequest` | unchanged |

## 4. Key architectural decisions from the audit

1. **No reimplemented optimizers or data parsers.** `calibration/` and
   `data_ingest/` are adapters + orchestration only (project restriction and
   engineering rule "prefer simple implementations").
2. **Fitting runs through `pybop.pybamm.Simulator`**, never raw
   `pybamm.Simulation` with `pybop.Parameter` objects (raises in PyBaMM's
   parameter substitution — verified). Our `pybamm_engine` remains the
   authority for non-fitting simulation (P0 baseline, synthetic generation).
3. **Event-terminated protocols are a baseline-only concept.** PyBOP removes
   voltage events (`remove_voltage_events=True`) for smooth objective
   evaluation; calibration experiments use fixed-duration steps or
   dataset-driven protocols. Documented in every `FittingSpec`.
4. **Python 3.12 is the integration baseline** (only version where
   PyBaMM+PyBOP+PyProBE coexist — verified). P0 artifacts stay valid; the
   canonical environment decision is recorded in
   `docs/DEPENDENCY_COMPATIBILITY.md`.
5. **Identifiability remains our responsibility** beyond PyBOP's 2-parameter
   Hessian check. We will use PyBaMM sensitivities + SALib + our own
   FIM/profile-likelihood code in `diagnostics/`.
6. **LLM never touches numbers downstream of extraction.** LLM outputs enter
   only as schema-validated `CandidateParameterRecord`s; deterministic
   validation must pass before a value becomes a `ParameterSetSnapshot`
   consumed by PyBOP (rules 1–2, 6, 10).

## 5. What was removed from our planned build

- Own optimizer implementations (was P3) → PyBOP.
- Own synthetic-noise machinery → `pybop.add_noise`/`Dataset` (we keep
  ground-truth bookkeeping).
- Own cycler-file parsing (was implicit in P5) → PyProBE.
- Own Sobol wrapper → SALib directly (PyBOP 26.10 removed its wrapper).
- Bayesian sampler implementations → PINTS via PyBOP.
