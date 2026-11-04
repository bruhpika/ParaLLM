# Closed-Loop LLM Framework for Physics-Based Battery Parameterization

Research prototype: a closed-loop, LLM-assisted framework for parameterization
and inverse estimation of physics-based lithium-ion battery models (PyBaMM).

Core principle: **the LLM is an evidence interpreter and workflow orchestrator —
not an oracle for electrochemical constants.** Numerical estimation, unit
conversion, physical checks and simulation are performed by explicit,
deterministic computational tools.

- Target framework: PyBaMM (initial focus: lithium-ion DFN models)
- Status: **Phase P0 (baseline simulation) complete** — no LLM integration yet
- PRD: `Closed_Loop_PyBaMM_LLM_Research_PRD.docx`

## Phase status

| Phase | Scope | Status |
|---|---|---|
| P0 | Reproducible PyBaMM DFN baseline + manifests + tests | ✅ done |
| P1 | Parameter registry with provenance | ⬜ not started |
| P2–P8 | Synthetic data, inverse estimation, identifiability, validation, extraction, closed loop, fine-tuning | ⬜ not started |

## Repository layout

```
configs/            run configurations (YAML, version-pinned)
src/pybamm_closed_loop/
  pybamm_engine/    pinned PyBaMM build/solve/extract (P0)
  reporting/        run manifests and figures
tests/              software-correctness tests (unit/, integration/)
benchmarks/         scientific benchmarks (separate from tests)
scripts/            thin CLI drivers (run_baseline.py, plot_baseline.py)
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
- Deterministic runs record `seed: null` with an explicit note; seeds become
  mandatory from the first stochastic component (P2).

## Agents

Project-specific agent/skill configuration lives in `.opencode/` (to be added
as modules land). See `AGENTS.md` for the scientific and engineering rules that
bind all contributors and agents.
