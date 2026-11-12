# Quickstart (working examples)

All commands run from the repo root. Core examples use `.venv`; PyBOP/benchmark
examples use `.venv-ecosystem312` (see `docs/INSTALLATION.md`). No API keys are
needed except the optional P5 LLM ablation (env vars, never committed).

## 1) Reproducible PyBaMM baseline (P0)

```bash
.venv/bin/python scripts/run_baseline.py --config configs/baseline_dfn.yaml --out results/baseline
.venv/bin/python scripts/plot_baseline.py --results results/baseline --figures results/figures
```

**Config:** `configs/baseline_dfn.yaml` — DFN, `ParameterValues("Chen2020")`,
IDAKLUSolver `rtol=atol=1e-6`, experiment `Discharge at 1C until 2.5 V`, pinned
`pybamm==26.8.0.0`. **Expected outputs** under the `--out`/`--figures` dirs:
`solution_arrays.npz` (time series + spatial profiles), `run_manifest.json`
(versions, solver, parameter snapshot, seed policy, variable availability),
`extraction_summary.json`, and figures (voltage/current, concentrations,
potentials). The run is deterministic (seed recorded as null). ~seconds.

## 2) Synthetic parameter estimation / recovery (P2, ecosystem venv)

```bash
.venv-ecosystem312/bin/python benchmarks/parameter_recovery/run_recovery_benchmark.py \
  --config configs/p2/recovery_single.yaml --out results/p2/recovery_single
```

**Config:** `configs/p2/recovery_single.yaml` (single-parameter recovery;
multi-condition variant: `configs/p2/recovery_multi.yaml`). Generates seeded
synthetic data from the Chen2020 forward model, fits with PyBOP/SciPy, and
reports recovery error. **Expected outputs** under `--out`: JSON/Markdown
report(s) and plots. **Limitation:** synthetic parameter recovery demonstrates
the estimation machinery; it is **not** experimental validation and does not
prove identifiability on real cells.

## 3) Literature extraction benchmark (P3 offline / P5 v3)

Offline/deterministic (no API key, fast):
```bash
.venv-ecosystem312/bin/python benchmarks/p3/run_extraction_benchmark.py --provider offline
```
Writes scored results under `results/p3/extraction_benchmark_v1_offline/`.

P5 v3 retrieval ablation (3 repeats/arm, **requires env keys** — never commit):
```bash
export PYCL_LLM_API_KEY=... PYCL_LLM_BASE_URL=... PYCL_LLM_MODEL=...
.venv-ecosystem312/bin/python benchmarks/p5/run_ablation.py --condition all --repeats 3
.venv-ecosystem312/bin/python benchmarks/p5/compute_consistency.py
```
Writes `results/p5/benchmark_v3/` (raw outputs per repeat, per-repeat reports,
aggregates with mean±std, per-item consistency, `summary.md`). Committed release
results reflect 3 repeats/arm on the 37-item v3 fixture
(`data/eval/extraction_benchmark_v3.jsonl`); see `docs/BENCHMARK_RESULTS.md`.
**Note:** reproducing LLM arms depends on the configured model/endpoint and
shows run-to-run variance; treat committed aggregates as the reference run.

## 4) Run the test suite

```bash
.venv/bin/python -m pytest                  # core: 184 passed, 6 skipped
.venv-ecosystem312/bin/python -m pytest     # full: 201 passed, 3 warnings
.venv-ecosystem312/bin/python -m compileall -q src benchmarks scripts tests
```

Scope: unit + integration + characterization. Measured on the `v0.1.0-beta.1`
release commit `bec653d` — core env CPython 3.14.8 (PyBOP/PyProBE tests skip),
ecosystem env CPython 3.12.16 with PyBOP 26.10 + PyProBE-Data 2.6.1. The three
warnings are PyBOP optimiser notices, not failures.

Scientific benchmarks live in `benchmarks/` (separate from `tests/`) and are not
part of the default pytest run.

## Key configs (examples)

- `configs/baseline_dfn.yaml` — P0 DFN baseline (pinned model/solver/experiment).
- `configs/p2/recovery_single.yaml`, `configs/p2/recovery_multi.yaml` — synthetic recovery.
- `configs/p2/identifiability.yaml`, `configs/p2/diffusivity_feasibility.yaml` — identifiability/feasibility.
- `configs/p3/*.yaml` — ingestion/extraction/registry settings.

## Known limitations (read before interpreting outputs)

- No independent experimental validation in this beta. Synthetic recovery ≠
  experimental validation; optimization ≠ identifiability.
- P5 experimental-condition extraction is weak (condition completeness 0.116
  all / 0.035 eval under retrieval). Eligible Chen2020-aligned 25 °C multi-rate
  validation data is unresolved; the real-data experiment is designed, not run.
- Full disclosure: `docs/SCIENTIFIC_LIMITATIONS.md`. Data/licenses:
  `docs/DATA_PROVENANCE.md`.