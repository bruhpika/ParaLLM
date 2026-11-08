# Architecture

The system is divided into four cooperating modules. Deterministic scientific
components own all numerical operations; the LLM (later phases) interprets
evidence, structures information and proposes next actions. The LLM can never
write scientific parameters directly.

```
             ┌──────────────────────────────────────────────┐
             │            closed_loop (Orchestrator)        │
             │  iteration log • stopping rules • approval   │
             └──┬──────────────┬──────────────┬─────────────┘
                │              │              │
   ┌────────────▼───┐  ┌───────▼────────┐  ┌──▼───────────────┐
   │ 1 Domain Intel │  │ 2 Validation   │  │ 3 Inverse Model  │
   │ literature/    │→ │ validation/    │→ │ pybamm_engine/   │
   │ extraction/    │  │ units/checks   │  │ calibration/     │
   └────────────────┘  └────────────────┘  │ diagnostics/     │
            ▲                               └────────┬─────────┘
            │ targeted retrieval                    │ residual summary
            └───────────────────────────────────────┘
        Shared core: parameter_registry • specifications • reporting
```

## Module responsibilities

| Module | Package | Responsibility | Status |
|---|---|---|---|
| 1. Domain Intelligence | `literature/`, `extraction/` | Document ingestion, retrieval, domain-adapted extraction, parameter mapping, missing-data detection | P6 |
| 2. Parameter Validation | `validation/` | Unit normalization, definition/condition checks, plausibility, conflict preservation | P1/P6 |
| 3. Inverse Modelling | `pybamm_engine/`, `calibration/`, `diagnostics/` | PyBaMM execution, synthetic data, bounded optimization, sensitivity/identifiability/UQ | P0 engine ✅, rest P2–P4 |
| 4. Closed-Loop Refinement | `closed_loop/` | Discrepancy diagnosis, targeted retrieval, controlled recalibration, iteration audit | P7 |
| Shared core | `parameter_registry/`, `specifications/`, `reporting/` | Provenance data model, cell/model specs, manifests and exports | P0 reporting ✅, registry P1 |

## Interfaces (typed contracts)

| From → To | Contract | Producer phase |
|---|---|---|
| `specifications` → all | `CellSpec`, `ModelConfig` (chemistry, model + pinned version, options, conditions) | P1 |
| Domain Intel → Validation | `CandidateParameterRecord[]` (raw value/unit, provenance, evidence excerpt, status) | P6 |
| Validation → registry | `ValidatedParameterRecord` ∈ {accepted, needs_review, rejected} + `ValidationReport` | P6 |
| registry → Inverse Modelling | `ParameterSetSnapshot` (unresolved fields explicit) | P1 |
| Inverse Modelling → Closed-Loop | `SimulationResult`, `CalibrationReport` (fit, sensitivity, identifiability, uncertainty) | P2–P4 |
| Closed-Loop → Domain Intel | `EvidenceRequest` (targeted retrieval for unresolved/weak parameters) | P7 |
| Closed-Loop → Inverse Modelling | `RecalibrationRequest` (subset + bounds, human-approved) | P7 |
| all → reporting | `RunManifest` (versions, seeds, snapshots, decisions) | P0 ✅ |

## P0 implementation (current)

The only implemented scientific component is the PyBaMM engine:

- `pybamm_engine/config.py` — Pydantic configuration models; version pin
  enforcement; YAML round-trip. Extra fields are rejected (`extra="forbid"`).
- `pybamm_engine/engine.py` — the single place that touches the PyBaMM API:
  model/parameter-set/solver factories, `run()`, `save_result()`. Unknown
  parameter sets and version drift raise explicit errors.
- `pybamm_engine/outputs.py` — extraction of time series and spatial profiles
  into numpy arrays; unavailable variables are reported, never fabricated.
- `reporting/manifest.py` — reproducibility manifest (versions, platform,
  solver settings, parameter set metadata, seed policy, extraction
  availability) and JSON-safe parameter snapshots.
- `reporting/figures.py` — voltage/current, concentration and electrode
  potential figures; adapt to available variables.

## Design principles

1. **Deterministic core.** All numerics (simulation, unit conversion,
   optimization) live in plain Python tools with explicit inputs/outputs.
2. **Provenance or it didn't happen.** Every value keeps its source, unit,
   conditions and status (user_supplied / literature_derived / calculated /
   assumed / calibrated / unresolved).
3. **Honest gaps.** Missing evidence produces `not_found` / `unresolved`, never
   plausible-sounding guesses.
4. **One PyBaMM boundary.** Only `pybamm_engine/` imports PyBaMM, so version
   drift is contained and tested in one place.
5. **Reproducibility by construction.** Every run emits a manifest; configs are
   declarative and version-pinned; seeds are recorded (null only when truly
   deterministic).

## Current implementation map (audit hardening sprint, Nov 2026)

As-implemented data flow, verified by running every pipeline once on this
machine (Linux, main venv = `.venv` CPython 3.14, ecosystem venv =
`.venv-ecosystem312` CPython 3.12 with pybop 26.10 / PyProBE-Data 2.6.1):

```
configs/baseline_dfn.yaml ── scripts/run_baseline.py
      └─► pybamm_engine.engine.run(): ParameterValues("Chen2020") → DFN →
            IDAKLUSolver(rtol=atol=1e-6) → solve → outputs.extract_all
            └─► save_result() → results/baseline/ (npz + 3 JSON)
configs/p2/recovery_*.yaml ── benchmarks/parameter_recovery/run_recovery_benchmark.py
      └─► calibration.synthetic.generate_datasets (pybamm forward + pybop.add_noise,
            seeded) ─► calibration.fitting.build_problem/run_fit_with_result
            (pybop.Problem / MetaProblem + SciPyMinimize)
            └─► results/p2/<run_id>/ (report.json, summary.md, pngs)
configs/p2/identifiability.yaml ── benchmarks/identifiability/run_identifiability.py
      └─► calibration.{synthetic,fitting,identifiability} + direct pybop MCMC
            └─► results/p2/identifiability_volume_fractions/
configs/p2/diffusivity_feasibility.yaml ── benchmarks/identifiability/diffusivity_feasibility.py
      └─► direct pybamm (ParameterValues/Experiment/Simulation)
            └─► results/p2/diffusivity_feasibility/
data/eval/extraction_benchmark_v1.jsonl ── benchmarks/p3/run_extraction_benchmark.py
      ├─► data/literature_store/ (ingested once, immutable afterwards)
      └─► results/p3/extraction_benchmark_v1_<provider>/
data/raw_documents/chen2020…/fulltext.txt ── python -m pybamm_closed_loop.registry.seed
      └─► data/registry/{registry.json, revisions.jsonl}
```

Verified entry points (single run, this machine):

| Entry point | Venv | Runtime |
|---|---|---|
| `scripts/run_baseline.py` (full 1C discharge) | `.venv` | ≈2.4 s |
| `scripts/plot_baseline.py` | `.venv` | <1 s |
| `benchmarks/parameter_recovery/run_recovery_benchmark.py` (full config) | `.venv-ecosystem312` | minutes |
| `benchmarks/identifiability/run_identifiability.py` (full config) | `.venv-ecosystem312` | minutes |
| `benchmarks/p3/run_extraction_benchmark.py --provider offline` | `.venv-ecosystem312` | seconds |

Reproducibility spot-check: a fresh `run_baseline.py` execution wrote
`solution_arrays.npz` bit-identical to the committed `results/baseline/`
arrays (max abs diff 0.0 over all series/profiles).

Layering notes (verified):

- `pybamm_engine/engine.py` → `reporting/manifest.py` is the only upward edge
  (engine depends on reporting for manifest assembly).
- `calibration/` adapters import `pybamm`/`pybop` at module top-level; they are
  therefore importable only in ecosystem venvs (by design; tests use
  `importorskip("pybop")`).
- `benchmarks/identifiability/diffusivity_feasibility.py` calls PyBaMM APIs
  directly (does not go through `pybamm_engine/`); it is a benchmark, not a
  library module. Kept as-is during the audit sprint; may be revisited later.

### Test suite (safety net)

- `tests/unit/` + `tests/integration/` — pre-existing, 84 passed / 4 skipped in
  `.venv` (pybop-free; pybop-dependent tests auto-skip) and 96 passed in
  `.venv-ecosystem312` (full suite). Runtime on this machine: ~5–7 s.
- `tests/characterization/` — added by the audit sprint: short, fast pipeline
  runs that snapshot key scientific outputs into `tests/baselines/` and compare
  with explicit tolerances (`np.allclose(..., equal_nan=True)` or JSON field
  tolerances documented in each test's docstring). Baselines were generated
  from the pre-audit code and verified deterministic across 3 consecutive
  runs. Baseline regeneration: `tests/baselines/generate_baselines.py`
  (run per venv, see module docstring). These tests are the merge gate for the
  audit sprint: numerics must not drift without an explicit, reviewed decision.

### Runner matrix

| Task | Command |
|---|---|
| Unit + integration (pybamm-only) | `.venv/bin/python -m pytest` |
| Full suite incl. pybop | `.venv-ecosystem312/bin/python -m pytest` |
| Scientific benchmarks (opt-in) | `.venv-ecosystem312/bin/python -m pytest -m benchmark` or run the benchmark scripts directly |

Agents in the audit sprint work in git worktrees under `/tmp/opencode/worktrees/`
(branches `wg/agent*`); worktree-local `src/` shadows the editable install
because pytest inserts `pythonpath = ["src"]` at the front. Disjoint file
ownership for this sprint:

| Agent | Owns |
|---|---|
| A (bugs) | `src/pybamm_closed_loop/calibration/`, `src/pybamm_closed_loop/pybamm_engine/`, `benchmarks/parameter_recovery/`, `benchmarks/identifiability/` |
| B (security) | `src/pybamm_closed_loop/literature/`, `src/pybamm_closed_loop/eval/`, `src/pybamm_closed_loop/datasets/`, `scripts/p3/`, repo-level `.gitignore` |
| C (quality) | `src/pybamm_closed_loop/registry/`, `src/pybamm_closed_loop/validation/`, `src/pybamm_closed_loop/reporting/`, `scripts/run_baseline.py`, `scripts/plot_baseline.py`, `scripts/compat_probe/`, `pyproject.toml` (tool config section only) |
| D (deps) | `requirements*.lock`, `README.md`, `pyproject.toml` (dependencies section only — coordinated via orchestrator) |
| E (reviewer) | read-only; runs suites on merged branch |
| Orchestrator | `tests/`, `docs/` (incl. `docs/internal/` audit artifacts), merges |


## P4–P5 additions (beta, non-breaking)

- `eval/extraction_prompt_p5.py`, `provenance_p5.py`, `benchmark_p5.py` —
  P5 reliability/provenance/scoring (P0–P4 modules untouched); benchmark v3
  loader/scoring and a retrieval/knowledge ablation harness (3 repeats/arm,
  raw outputs preserved, robust transport retries).
- `benchmarks/p4/`, `benchmarks/p5/`, `scripts/p4/`, `scripts/p5/` —
  reproducible benchmark runners and data/ingest builders.
- LLM client remains optional and env-configured (`PYCL_LLM_*`); offline
  deterministic paths require no key. See `docs/BENCHMARK_RESULTS.md` and
  `docs/SCIENTIFIC_LIMITATIONS.md` for disclosed results/limits.
