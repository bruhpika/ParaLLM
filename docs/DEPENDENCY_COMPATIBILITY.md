# Dependency Compatibility Report

Verified 2026-11-04 on this machine (Linux x86_64, Intel Core Ultra 7 155H,
CPU-only). Every claim below was tested by running code; probe scripts live in
`scripts/compat_probe/` and are reproducible.

## 1. Environments

| Environment | Python | Packages | Purpose |
|---|---|---|---|
| `.venv` (P0, unchanged) | 3.14.8 | pybamm 26.8.0.0, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0, pydantic 2.14.2, matplotlib 3.11.2, pytest 9.2.0 | P0 baseline simulation (preserved) |
| `.venv-ecosystem` | 3.14.8 | pybamm[plot] 26.8.0.0, **pybop 26.10**, pints 0.6.1, polars 2.1.0 | PyBOP ↔ PyBaMM compatibility lane |
| `.venv-ecosystem312` | 3.12.16 (standalone, provisioned with `uv`) | pybamm 26.8.0.0, pybop 26.10, **PyProBE-Data 2.6.1**, polars 1.44.2 | Full three-package stack |

The P0 environment was not modified. Upstream sources were not modified.

## 2. Version constraints (verified)

| Package | Version | Requires-Python | Key pins | Our machine |
|---|---|---|---|---|
| pybamm | 26.8.0.0 (pinned by us) | >=3.10,<3.16 | — | ✅ 3.14 |
| pybop | 26.10 (2026-11-03) | >=3.10,<3.16 | `pybamm[plot]>=26.3.0` (**no upper pin**), pints>=0.6, polars>=1.18 | ✅ 3.14 |
| PyProBE-Data | 2.6.1 (2026-10-14) | **>=3.11,<3.13** | `polars>=1.18,<2`; optional `pybamm[cite]>=25.1.1` (no upper pin) | ❌ 3.14 / ✅ 3.12 |

**Critical incompatibility:** `PyProBE-Data` hard-caps Python below 3.13. On
this machine (system Python 3.14.8) `pip install PyProBE-Data` fails with
`ERROR: Ignored the following versions that require a different python
version ... Requires-Python >=3.11,<3.13` (all releases 1.1.0–2.6.1). This is
a metadata-level refusal, not a runtime failure. We provisioned a standalone
CPython 3.12.16 via `uv` to test the combined stack.

Also note: the PyPI project named `pyprobe` is an unrelated video-metadata
tool. The battery package is **`PyProBE-Data`** (import name `pyprobe`).
Similarly, `https://pybop.readthedocs.io` is not PyBOP's docs; use
`https://pybop-docs.readthedocs.io`.

## 3. Experiment results (all runnable via `scripts/compat_probe/`)

| # | Question | Env | Result | Evidence |
|---|---|---|---|---|
| 1 | Can PyBOP use a PyBaMM model with our baseline config (DFN + Chen2020 + IDAKLU)? | `.venv-ecosystem` | **PASS** | `exp1_pybop_dfn_baseline.py`: Dataset from DFN solution accepted; `Problem.evaluate` at true parameters → cost 8.2e-11 (≈0, noise-free), per-parameter sensitivities returned |
| 2 | Can PyBOP optimize selected parameters of a DFN model? | `.venv-ecosystem` | **PASS** | `exp2_pybop_dfn_optimization.py`: L-BFGS-B + `SumSquaredError` + `jac=True`, 30 iterations, synthetic Chen2020 data (σ=2e-3). Recovered [0.7524, 0.6595] vs true [0.75, 0.665] (abs err 2.4e-3 / 5.5e-3) |
| 3 | Can the existing Chen2020 parameter set be used appropriately? | `.venv-ecosystem` | **PASS** | `exp3_chen2020_parameters.py`: `pybop.Parameter` declarations on Chen2020 keys work; non-fitted values untouched; simulations run through `pybop.pybamm.Simulator` |
| 4 | Can PyProBE ingest and process an example experimental dataset? | `.venv-ecosystem312` | **PASS** | `exp4_pyprobe_ingest.py`: upstream Neware sample (50 MB xlsx + README.yaml) → 37 118-row discharge filtered by `.experiment().cycle().discharge()`; numpy + pandas extraction OK; cycle summary OK |
| 5 | Can processed experimental data be passed into a PyBOP workflow? | `.venv-ecosystem312` | **PASS** (plumbing only) | `exp5_pyprobe_to_pybop.py`: PyProBE arrays → `pybop.Dataset` → `Problem.evaluate` + 3 optimiser steps. Scientific values NOT reported: sample cell is NMC622/0.04 A.h, not the Chen2020 LG M50 |

## 4. API findings from live probing (docs alone were insufficient)

These behaviours were discovered by running the installed packages and differ
from some published examples:

1. **`pybop.Problem` requires ≥1 declared fitted parameter** — parameters are
   collected only from `pybop.Parameter` objects placed in
   `pybamm.ParameterValues.update()`; without one, `get_bounds_array()` raises
   `AttributeError` on a `None` distribution.
2. **`Parameters.names` is a list attribute at runtime**, shadowing the method
   of the same name in the source. Use it as a property.
3. **`problem.evaluate(...)` returns `pybop.costs.evaluation.Evaluation`** with
   `.values` (ndarray) and `.sensitivities` (dict of ndarrays); there are no
   scalar `.value()`/`.cost()` accessors.
4. **Transformations are distribution-dependent** (verified in
   `pybop/parameters/distributions.py`): `LogTransformation` is implemented
   only for `LogNormal` and `LogUniform`; `ScaledTransformation` for
   `Gaussian`/`Uniform`/`LogUniform`. Any other pairing raises `TypeError`.
5. **A raw `pybamm.Simulation` cannot process a `ParameterValues` containing
   `pybop.Parameter` objects** (`NotImplementedError` in
   `parameter_substitutor`). All fitting configurations must run through
   `pybop.pybamm.Simulator`, and its `solve()` requires an explicit `inputs`
   dict mapping fitted-parameter names to values.
6. **`OptimisationResult.cost` is a per-iteration list attribute**; the final
   value is `result.best_cost`. `result.x` is the optimiser solution.
7. **`pyprobe.analysis` is a submodule**, not re-exported at package root
   (`from pyprobe.analysis import cycling` works).
8. **PyProBE returns Polars DataFrames** (`.data`, `.df` properties);
   `.get(...)` returns numpy arrays; pandas only via `.df.to_pandas()`.
9. **`pybop.pybamm.Simulator` removes voltage events by default**
   (`remove_voltage_events=True`) — event-terminated protocols (our P0
   `"until 2.5 V"` experiment) are unsuitable for fitting; use fixed-duration
   steps or dataset-driven protocols in calibration workflows.
10. Minor: `SciPyMinimizeOptions` accepts `verbose` in CI examples but emits
    `OptimizeWarning: Unknown solver options: disp` from SciPy — harmless.

## 5. Recommended version combinations

**Option A — single environment (verified, recommended for integration):**
Python 3.12.16 + `pybamm==26.8.0.0` + `pybop==26.10` + `PyProBE-Data==2.6.1`
(polars resolves to 1.44.2, satisfying PyProBE's `<2` pin and PyBOP's `>=1.18`).

**Option B — split lanes (also verified):**
keep Python 3.14 for simulation/optimisation (`.venv-ecosystem`) and use a
3.12 environment only for PyProBE ingestion, exchanging `.npz`/parquet files
between lanes. More operationally complex; no scientific benefit.

**Option C — drop PyProBE, use its `generic` importer logic ideas:** rejected —
the task forbids reimplementing cycler processing.

The P0 environment stays exactly as-is; integration work should either move to
`.venv-ecosystem312` or migrate the project's canonical venv to 3.12 in a
later, explicitly approved step.

## 6. Residual risks

1. **PyBaMM drift:** neither PyBOP (`pybamm>=26.3.0`) nor PyProBE
   (`pybamm[cite]>=25.1.1`) upper-pin PyBaMM. We pin `pybamm==26.8.0.0`
   ourselves in every environment. PyBOP releases track PyBaMM closely
   (v24.9.0 was yanked due to an upstream break; v26.10 required PyBaMM
   >=26.3), so a future PyBaMM upgrade must be validated against PyBOP before
   adoption.
2. **API churn:** PyBOP v25.10 removed the old `FittingProblem`/`MCMCSampler`/
   FIM/sensitivity APIs; pre-25.10 tutorials found on the web are misleading.
   Target only v26.10 semantics (this document).
3. **PyProBE polars pin:** `polars<2` (since 2.6.1) due to a join-ordering bug;
   stack resolution is sensitive here. Record `polars==1.44.2` in locks.
4. **Python 3.13 support gap:** PyProBE excludes 3.13+; if the project later
   needs 3.13/3.14-only features, the PyProBE lane must stay on 3.12 or a
   maintained fork would be required (upstream change, not ours).
5. **Seed coverage:** PyBOP exposes seeds only for
   `SciPyDifferentialEvolution` and `EP_BOLFI`; PINTS samplers/optimisers have
   no seed parameter — we must seed `numpy.random` ourselves and record it.
