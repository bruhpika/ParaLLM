# PARALLM — LLM-assisted, provenance-grounded parameterization for PyBaMM

> **Parameters — not a problem anymore (for [PyBaMM](https://pybamm.org)).**  
> *Public beta `v0.1.0-beta.1` (research prototype).*

PARALLM is a closed-loop, LLM-assisted framework for parameterization and inverse
estimation of physics-based lithium-ion battery models built on
[PyBaMM](https://pybamm.org). It targets the hard part of physics-based battery
modelling: finding defensible parameter values with clear provenance.

## The problem

PyBaMM models (e.g., DFN) need dozens of electrochemical parameters whose values
depend on chemistry, geometry, and experimental conditions. They are scattered
across papers and supplements, reported in inconsistent units/definitions, and
many are weakly identifiable from voltage data alone. Treating an LLM as a
source of truth produces plausible but ungrounded numbers.

## Core idea

**The LLM is an evidence interpreter and workflow orchestrator — not an oracle
for electrochemical constants.** Numerical estimation, unit conversion, physical
checks, and simulation are explicit and deterministic.

- Retrieval-grounded extraction with provenance (quotes, locators, conditions) —
  never silently invent or substitute values.
- Deterministic validation and a provenance-tracked parameter registry
  (user-supplied / literature-derived / calculated / assumed / calibrated /
  unresolved).
- PyBOP-based inverse estimation and identifiability on synthetic data;
  calibration data is never used as validation data.

## Capabilities (P0–P5, this beta)

| Milestone | Scope | Status |
|---|---|---|
| P0 | Reproducible PyBaMM DFN baseline (Chen2020, 1C, IDAKLU) + manifests | ✅ |
| P1 | Ecosystem audit (PyBOP 26.10 / PyProBE-Data 2.6.1), compatibility + architecture | ✅ |
| P2 | PyBOP estimation, sensitivity/identifiability, **synthetic parameter recovery** | ✅ |
| P3 | Literature ingestion, provenance registry, deterministic + optional LLM extraction | ✅ |
| P4 | LLM extraction evaluation (v2, 20 items) + Chen2020 discrepancy + dataset audit | ✅ |
| P5 | Reliability/provenance checks, v3 benchmark, **retrieval ablation** (37 items, 3 repeats/arm), real-data experiment design (not run) | ✅ |

## Headline benchmark (P5, v3 — 37 items, 3 repeats/arm, mean ± std)

Retrieval-grounded vs knowledge-without-evidence vs strict no-evidence, same
model/task/schema/rubric, **v3 only** (`mimo-v2.6-flash`, temp 0). Full
eval-split and per-item consistency: `results/p5/benchmark_v3/summary.md`,
`docs/BENCHMARK_RESULTS.md`.

| metric (all) | retrieval + strict | no retrieval, memory permitted | no retrieval, strict |
|---|---:|---:|---:|
| parameter identification | **0.718 ± 0.009** | 0.378 ± 0.086 | 0.000 ± 0.000 |
| value extraction (matched) | **0.946 ± 0.022** | 0.272 ± 0.083 | n/a |
| provenance (matched) | **0.928 ± 0.026** | 0.000 ± 0.000 | n/a |
| condition completeness (matched) | **0.116 ± 0.011** (weak) | 0.483 ± 0.062 (ungrounded) | n/a |
| qualifier accuracy (matched) | **0.741 ± 0.033** | 0.497 ± 0.045 | n/a |
| false extraction rate | **0.000 ± 0.000** | 0.275 ± 0.042 | n/a |
| abstention accuracy | **1.000 ± 0.000** | 0.333 ± 0.136 | **1.000 ± 0.000** |

**Read this honestly:** retrieval is required for grounded extraction; memory-only
emits unsupported claims (zero provenance, non-zero false extraction, fails to
abstain). **Experimental-condition extraction is weak** (condition completeness
0.116 all / 0.035 eval under retrieval). These are literature/benchmark results
and **synthetic recovery results — not independent experimental validation.**

## Architecture

One PyBaMM boundary; deterministic numerics; provenance-first registry; optional
LLM client (env-configured). See `docs/ARCHITECTURE.md`.

```
literature/ + datasets/  -> ingest & retrieve evidence
eval/ + extraction/      -> extract (deterministic or retrieval-grounded LLM) + score + provenance checks
validation/ + registry/  -> deterministic checks, provenance-tracked parameter store
pybamm_engine/           -> pinned PyBaMM build/solve/extract (the only PyBaMM boundary)
calibration/             -> PyBOP fitting, synthetic data, identifiability
reporting/               -> manifests & figures
```

## Repository structure

```
.
├── src/pybamm_closed_loop/      # installable package
│   ├── pybamm_engine/           #   pinned PyBaMM build/solve/extract (only PyBaMM boundary)
│   ├── calibration/             #   PyBOP fitting, synthetic data, identifiability
│   ├── literature/              #   document ingestion, store, retrieval
│   ├── extraction/              #   extraction pipeline (deterministic / optional LLM)
│   ├── eval/                    #   prompts, benchmark scoring, provenance checks (P3–P5)
│   ├── registry/ + parameter_registry/  # provenance-tracked parameter store
│   ├── validation/              #   deterministic physical/unit/condition checks
│   ├── datasets/                #   dataset linkage/audit helpers
│   └── reporting/               #   manifests & figures
├── configs/                     # version-pinned run configs (YAML)
├── benchmarks/                  # scientific benchmarks (separate from tests)
├── scripts/                     # CLI drivers (baseline, plots, compat, p3/p4/p5)
├── tests/                       # unit / integration / characterization (software correctness)
├── data/                        # fixtures, ingested store, registry; raw external data gitignored
├── results/                     # committed run outputs (baseline, p2–p5, figures)
└── docs/                        # architecture, reproducibility, benchmarks, limits, data provenance
```

## Installation

Supported Python: **3.10–3.15** (core). Full ecosystem (PyBOP/PyProBE/SALib/
pypdf/polars) verified on **CPython 3.12.16** (`<3.13` required for
`PyProBE-Data`). Details: `docs/INSTALLATION.md`.

```bash
# Core (PyBaMM-only)
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e ".[dev]"

# Full ecosystem (recommended, Python 3.12)
python3.12 -m venv .venv-ecosystem312
.venv-ecosystem312/bin/pip install -r requirements-integration.lock
.venv-ecosystem312/bin/pip install -e ".[dev,ecosystem]"
```

## Quickstart — working examples

```bash
# 1) Reproducible P0 baseline (DFN, Chen2020, 1C discharge to 2.5 V)
.venv/bin/python scripts/run_baseline.py --config configs/baseline_dfn.yaml --out results/baseline
.venv/bin/python scripts/plot_baseline.py --results results/baseline --figures results/figures

# 2) Synthetic parameter estimation / recovery (ecosystem venv)
.venv-ecosystem312/bin/python benchmarks/parameter_recovery/run_recovery_benchmark.py \
  --config configs/p2/recovery_single.yaml --out results/p2/recovery_single

# 3) Literature extraction benchmark, offline/deterministic (no API key)
.venv-ecosystem312/bin/python benchmarks/p3/run_extraction_benchmark.py --provider offline
# P5 v3 ablation (LLM, 3 repeats/arm) requires env keys — never commit them:
#   PYCL_LLM_API_KEY=... PYCL_LLM_BASE_URL=... PYCL_LLM_MODEL=...
#   .venv-ecosystem312/bin/python benchmarks/p5/run_ablation.py --condition all --repeats 3

# 4) Tests
.venv/bin/python -m pytest                  # core (ecosystem tests skip)
.venv-ecosystem312/bin/python -m pytest     # full (201 passed in release env)
```

Expected outputs and limitations for each: `docs/QUICKSTART.md`.

## Reproducibility & pinned stack

PyBaMM **26.8.0.0** (engine refuses version drift); PyBOP **26.10**;
PyProBE **2.6.1** (PyProBE-Data `<3.13`); numpy 2.5.4, scipy 1.18.1,
pandas 3.1.1, pydantic 2.12.5 (ecosystem env). Lockfiles:
`requirements.lock` (core, py3.14) and `requirements-integration.lock`
(ecosystem, py3.12.16). Configs in `configs/`. Deterministic runs record
`seed: null`; stochastic components record explicit seeds. LLM API keys are
read from the environment and never written to artifacts.

## Data, licenses & provenance

- **Software:** MIT (`LICENSE`) — applies to code only, not third-party
  data/documents.
- **Documents/datasets:** redistributed only where permitted (CC BY sources
  archived with license evidence/sha256). The Chen2020 supplement PDF is **not
  redistributed** (acquire separately); LG M50 sample data is gitignored and its
  upstream license is UNRESOLVED. See `docs/DATA_PROVENANCE.md`.

## Scientific limitations (read before citing results)

- **No independent experimental validation** is claimed in this beta.
- **Synthetic parameter recovery ≠ experimental validation;** optimization ≠
  identifiability. Calibration and validation data must stay disjoint.
- **Experimental-condition extraction is weak** (P5 retrieval condition
  completeness 0.116 all / 0.035 eval); an eligible Chen2020-aligned 25 °C
  multi-rate validation dataset is **unresolved** (T5/T6).
- Full disclosure: `docs/SCIENTIFIC_LIMITATIONS.md`.

## Citing

See `CITATION.cff`. Software citation for the beta: PARALLM v0.1.0-beta.1 (2026).

## Contributing & security

`CONTRIBUTING.md`. Do not open issues containing secrets or private data; report
security concerns privately to the maintainers.

## Acknowledgements

- **[The PyBaMM Team](https://www.pybamm.org/team)** and the
  [PyBaMM](https://pybamm.org) project — the physics-based battery modelling
  framework and Chen2020 parameter set this work builds on (PyBaMM is
  BSD-licensed upstream).
- **[PyBOP](https://github.com/pybop-team/PyBOP)** (the PyBOP team) — parameter
  optimization and identifiability tooling used for P2 estimation and
  sensitivity/identifiability analysis.
- **[PyProBE / PyProBE-Data](https://github.com/pybop-team/PyProBE-Data)** —
  battery test-data handling and dataset linkage utilities.
- **PINTS**, **SALib**, **CasADi/SUNDIALS (via PyBaMM)**, **NumPy/SciPy/pandas**,
  **pydantic/PyYAML/matplotlib**, **pypdf**, and **polars** — the numerical,
  configuration, and data stack this project relies on.
- The authors of the openly licensed literature used in the benchmark
  (attributed with license evidence in `docs/DATA_PROVENANCE.md`).

## Author

**Harshith Bhardwaz Kenkary** — <harshithkenkary@gmail.com>  
GitHub: [harshithkenkary](https://github.com/harshithkenkary)

## AI assistance disclosure

This project was developed with the assistance of AI coding tools (used to help
draft code, tests, and documentation). All scientific claims, benchmark numbers,
and release artifacts were reviewed against committed code, configs, and
deterministic outputs; AI assistance does not change the scientific
responsibility for reported results, and no independent experimental validation
is claimed.

## Status

Public beta `v0.1.0-beta.1`. P0–P5 complete; P6–P8 (closed loop, fine-tuning,
further validation) not started. History preserved on branch `audit/hardening`.
