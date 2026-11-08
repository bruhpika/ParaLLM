# Closed-Loop LLM Framework for Physics-Based Battery Parameterization

Research prototype: a closed-loop, LLM-assisted framework for parameterization
and inverse estimation of physics-based lithium-ion battery models (PyBaMM).

Core principle: **the LLM is an evidence interpreter and workflow orchestrator —
not an oracle for electrochemical constants.** Numerical estimation, unit
conversion, physical checks and simulation are performed by explicit,
deterministic computational tools.

- Target framework: PyBaMM (initial focus: lithium-ion DFN models)
- Status: **Phases P0–P3 landed (research prototype)** — deterministic
  baseline, parameter registry, PyBOP estimation/identifiability and literature
  provenance run offline; the P3 LLM extraction client (OpenAI-compatible) is
  optional and disabled unless `PYCL_LLM_API_KEY` and `PYCL_LLM_MODEL` are set
- PRD: `Closed_Loop_PyBaMM_LLM_Research_PRD.docx`

## Phase status

| Phase | Scope | Status |
|---|---|---|
| P0 | Reproducible PyBaMM DFN baseline + manifests + tests | ✅ done |
| P1 | Ecosystem audit (PyBOP 26.10 / PyProBE-Data 2.6.1) + verified compatibility + revised architecture | ✅ done (`docs/ECOSYSTEM_AUDIT.md`, `docs/DEPENDENCY_COMPATIBILITY.md`) |
| P2 | Numerical parameter estimation and identifiability (PyBOP-based) | ✅ done (see `results/p2/`, `benchmarks/`) |
| P3 | Literature intelligence and parameter provenance (LLM-assisted, offline by default) | ✅ done (see `results/p3/`) |
| P4–P8 | Validation, closed loop, fine-tuning | ⬜ not started |

## Repository layout

```
configs/            run configurations (YAML, version-pinned)
src/pybamm_closed_loop/
  pybamm_engine/    pinned PyBaMM build/solve/extract (P0)
  parameter_registry/, registry/  parameter store with provenance + pybop mapping
  calibration/      PyBOP fitting, synthetic data, identifiability (P2)
  literature/, datasets/, extraction/  PDF ingestion, LLM/rule extraction, provenance (P3)
  closed_loop/, validation/, diagnostics/, specifications/, eval/
  reporting/        run manifests and figures
tests/              software-correctness tests (unit/, integration/, regression/, baselines/)
benchmarks/         scientific benchmarks (separate from tests)
scripts/            thin CLI drivers (run_baseline.py, plot_baseline.py, compat_probe/, p3/)
docs/               architecture, roadmap, model documentation
data/               raw documents, synthetic/experimental data (immutable raw)
results/            run outputs: arrays, manifests, figures
```

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e .

# full P0 baseline (DFN, Chen2020, 1C discharge to 2.5 V)
.venv/bin/python scripts/run_baseline.py --config configs/baseline_dfn.yaml --out results/baseline
.venv/bin/python scripts/plot_baseline.py --results results/baseline --figures results/figures

# tests (software correctness)
.venv/bin/python -m pytest
```

### Testing — which venv runs what

| Environment | Command | What runs |
|---|---|---|
| `.venv` (CPython 3.14, main stack) | `.venv/bin/python -m pytest` | unit + integration + regression + characterization without PyBOP/PyProBE (ecosystem-dependent tests skip) |
| `.venv-ecosystem312` (CPython 3.12.16) | `.venv-ecosystem312/bin/python -m pytest` | full suite including PyBOP fitting/identifiability and PyProBE dataset-audit tests |

- Scientific benchmarks run separately (never inside the default pytest run):
  either opt in with `.venv-ecosystem312/bin/python -m pytest -m benchmark` or
  run the scripts under `benchmarks/` directly (they write to `results/`).
- Characterization tests replay committed baseline arrays under
  `tests/characterization/` (regenerated only with explicit maintenance
  tooling) so numerical behavior is gated before any refactor.
- Note: the `test_neware_*` integration tests need the external sample data
  under `data/external/pyprobe_sample/neware/` (not committed); test runs in a
  fresh checkout without it show exactly one environmental failure.

### Optional ecosystem install

```bash
# PyBOP 26.10, SALib, pypdf, polars (+ PyProBE-Data — needs Python < 3.13)
.venv-ecosystem312/bin/pip install -e ".[ecosystem]"
```

The `ecosystem` extra is verified on CPython 3.12.16 (the exact frozen set is
`requirements-integration.lock`); on Python ≥ 3.13 pip skips the
`PyProBE-Data` requirement via its environment marker. It pulls only what the
codebase imports (`pybop`, `pints`/`SALib` via `pybop`, `SALib`, `pypdf`,
`polars`, `pyprobe`); `cma`, `scikit-learn` and `fastexcel` arrive as
transitive dependencies. Bounds deliberately exclude `pypdf 7.x` and
`polars 2.x` (unverified majors).

## P0 baseline in one paragraph

A Doyle–Fuller–Newman (DFN) model of a commercial LG M50 cell (PyBaMM
`Chen2020` parameter set, 5 A.h nominal capacity) is discharged
galvanostatically at 1C (5 A) at 298.15 K until the 2.5 V cut-off. The DAE is
solved with the IDAKLU solver (rtol=atol=1e-6). The run terminates at
t ≈ 3555 s with ≈ 4.94 A.h extracted capacity. Every run writes a
reproducibility manifest (software versions, parameter snapshot, solver
settings, seed policy) and explicitly reports any requested variable that is
not available in the model — nothing is ever fabricated.

See `docs/P0_BASELINE_MODEL.md` for the physical model, parameter meanings and
scientific limitations.

## Reproducibility rules

- PyBaMM is pinned (`pybamm==26.8.0.0`); the engine refuses to run on a version
  mismatch.
- Parameter sets are loaded from the installed PyBaMM library only — no
  hand-typed electrochemical constants.
- Output variables that do not exist in the built model are recorded as
  unavailable; they are never synthesised.
- Deterministic runs record `seed: null` with an explicit note; every
  stochastic component (P2 synthetic data / noise injection) records an
  explicit `numpy` seed in its manifest.

## Ecosystem integration (PyBOP/PyProBE active since P2/P3)

Upstream reuse decisions are documented in `docs/ECOSYSTEM_AUDIT.md` (PyBOP
26.10, PyProBE-Data 2.6.1), `docs/DEPENDENCY_COMPATIBILITY.md` (verified
version matrix), `docs/REVISED_ARCHITECTURE.md` (module boundaries) and
`docs/INTEGRATION_PLAN.md` (phased plan). Compatibility probes live in
`scripts/compat_probe/`. P2 uses PyBOP for estimation/identifiability
(`calibration/`, `docs/IDENTIFIABILITY_STUDY.md`); P3 uses PyProBE for dataset
linkage (`datasets/pyprobe_link.py`, `docs/DATASET_AUDIT.md`).

## Agents

Project-specific agent/skill configuration lives in `.opencode/` (to be added
as modules land). See `AGENTS.md` for the scientific and engineering rules that
bind all contributors and agents.
