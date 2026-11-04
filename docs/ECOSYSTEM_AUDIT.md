# Open-Source Ecosystem Audit

Audit of upstream packages for reuse in this framework. Sources: PyPI JSON
APIs, GitHub source (release tags), official docs, and live probing of the
installed packages (see `docs/DEPENDENCY_COMPATIBILITY.md` and
`scripts/compat_probe/`). Verified 2026-11-04.

Naming warnings first:

- The battery package is **`PyProBE-Data`** on PyPI (import name `pyprobe`).
  The PyPI project `pyprobe` is an unrelated video-metadata extractor.
- PyBOP's documentation is at **https://pybop-docs.readthedocs.io** (the
  domain `pybop.readthedocs.io` hosts an unrelated package).

## 1. PyBaMM (simulation) — 26.8.0.0

Already integrated in P0 via our `pybamm_engine/` (DFN, Chen2020, IDAKLU).
Nothing to change. Roles going forward: forward model inside PyBOP's
`pybop.pybamm.Simulator`, and standalone simulation for synthetic data (P2)
and baseline reproduction.

## 2. PyBOP (parameterization & optimization) — 26.10

- License: BSD-3-Clause. Status: Beta, actively maintained (released
  2026-11-03; JOSS 2025, doi:10.21105/joss.07874; Faraday Institution /
  IntelLiGent / DigiBatt backing). Monthly-to-quarterly CalVer releases since
  2023.
- Requires Python >=3.10,<3.16 (3.14 supported since v26.10). Depends on
  `pybamm[plot]>=26.3.0` (no upper pin), `pints>=0.6`, `polars>=1.18`,
  numpy/scipy. No JAX/torch.
- **Important:** v25.10 was a breaking API restructure; older web tutorials
  reference classes that no longer exist. Everything below is v26.10.

### Capability map (exact v26.10 API, verified on installed package)

| Need | Public API | Notes |
|---|---|---|
| Parameter definitions | `pybop.Parameter(distribution=...\|bounds=..., initial_value=..., transformation=...)`, `pybop.Parameters` | Declared by `parameter_values.update({name: pybop.Parameter(...)})`. `bounds` and `distribution` are mutually exclusive. Name comes from the PyBaMM parameter key. |
| Distributions | `pybop.Gaussian`, `LogNormal`, `Uniform`, `LogUniform`, `Unbounded`, `Exponential`, `JointDistribution`, multivariate variants | Accept `scipy.stats` frozen distributions. `MarginalDistribution`/multivariate for correlated priors. |
| Transformations | `pybop.LogTransformation`, `ScaledTransformation`, `IdentityTransformation`, `UnitHyperCube`, `ComposedTransformation` | Pairing rules enforced (see compatibility doc finding 4). |
| Forward model | `pybop.pybamm.Simulator(model, parameter_values, protocol=pybamm.Experiment\|Dataset\|ndarray, solver=..., output_variables=..., remove_voltage_events=True)` | `solve(inputs: dict, calculate_sensitivities=bool)`. Voltage events removed by default for fitting smoothness. |
| EIS forward model | `pybop.pybamm.EISSimulator(model, parameter_values, f_eval=...)` | Built-in casadi/scipy EIS extension. |
| Data | `pybop.Dataset({"Time [s]":..., "Current [A]":..., "Voltage [V]":...}, domain=..., control_functions=...)` | Dict of numpy arrays (polars under the hood). EIS: `"Frequency [Hz]"`, `"Impedance"`. Helpers: `pybop.add_noise`, `import_pybamm_solution`, `import_pyprobe_result`, `downsample_constant_current`. |
| Problem | `pybop.Problem(simulator, cost)`, `pybop.MetaProblem` (multi-experiment), `pybop.LogPDF`, `pybop.LogPosterior` | `evaluate(inputs, calculate_sensitivities=...) -> Evaluation(.values, .sensitivities)`. |
| Cost functions | `pybop.SumSquaredError`, `MeanSquaredError`, `RootMeanSquaredError`, `MeanAbsoluteError`, `Minkowski`, `SumOfPower`, `GaussianLogLikelihoodKnownSigma(dataset, sigma=...)`, `GaussianLogLikelihood(dataset, sigma=...)` (sigma can itself be a `Parameter`), `LogPrior`, `WeightedCost`, `DesignCost` | `ErrorMeasure(dataset, target=..., weighting={"equal"\|"domain"\|array})`. Complex residuals supported (EIS). |
| Deterministic optimizers | `pybop.SciPyMinimize(problem, options=pybop.SciPyMinimizeOptions(method="L-BFGS-B"\|"Nelder-Mead"\|..., jac=True, maxiter=..., constraints=...))`; `pybop.SciPyDifferentialEvolution(..., SciPyDifferentialEvolutionOptions(seed=..., strategy=..., init='sobol'\|'latinhypercube'\|...))` | Gradients via PyBaMM/CasADi sensitivities when `jac=True`. Also PINTS-based: `CMAES`, `PSO`, `NelderMead`, `IRPropMin/Plus`, `SNES`, `XNES`, `AdamW`, `SimulatedAnnealing`, `CuckooSearch`, `RandomSearch`, `GradientDescent`. `EP_BOLFI` (Bayesian optimisation; Python <3.13 only). |
| Bayesian inference / MCMC | `pybop.LogPosterior(simulator, cost)` + PINTS samplers: `pybop.DifferentialEvolutionMCMC`, `DREAM`, `NUTS`, `EmceeHammerMCMC`, `HaarioACMC`, `HaarioBardenetACMC`, `HamiltonianMCMC`, `MALAMCMC`, `MetropolisRandomWalkMCMC`, `PopulationMCMC`, `Slice*`, `DramACMC`, ... with `pybop.PintsSamplerOptions(n_chains=..., max_iterations=..., warm_up_iterations=...)` | `sampler.run() -> SamplingResult` with `get_summary_statistics()`, `summary_table()`, `effective_sample_size()`, `rhat()`, `plot_trace/posterior/predictive/chains`, `save/load`. Chain post-processing: `pybop.ChainProcessor`, `SingleChainProcessor`, `MultiChainProcessor`. |
| Hessian diagnostics | `pybop.classify_using_hessian(result, dx=..., cost_tolerance=..., normalise=...)`, `pybop.plot_hessian_eigenvectors` | Finite-difference Hessian at the optimum → eigenvalue-based classification. **Exactly 2 parameters only** (`ValueError` otherwise). |
| Sensitivity | **None built-in in 26.10** (`sensitivity_analysis` removed; SALib is an optional extra and must be called directly — upstream example `examples/notebooks/battery_parameterisation/sensitivity_analysis_salib.ipynb`) | Also `sensitivity_analysis_hessian.ipynb` shows Hessian-based approach. |
| Identifiability | FIM (`observed_fisher`) **removed in v25.10**; no profile likelihood; only the 2-parameter Hessian classifier | Gap: our framework must fill practical identifiability for N>2 (own FIM/SALib/profile code). |
| EIS inference | `EISSimulator` + `GaussianLogLikelihoodKnownSigma(target="Impedance")` + `pybop.plot.nyquist` (example `examples/scripts/battery_parameterisation/simple_eis.py`) | **No DRT** code exists in any release. |
| Grouped-parameter models | `pybop.lithium_ion.GroupedSPM`, `GroupedSPMe` (Hallemans et al. 2025, doi:10.1149/1945-7111/add41b), `pybop.lithium_ion.CellTemperature`, `pybop.li_half_cell.*`, `pybop.ExponentialDecayModel` | Fewer, more identifiable parameter groups for estimation. Linked/derived parameters via PyBaMM symbolics (`examples/scripts/getting_started/linked_parameters.py`). |

### Canonical v26.10 example (verified shape; condensed from upstream
`examples/scripts/getting_started/optimising_with_scipy_minimize.py`)

```python
import numpy as np, pybamm, pybop

model = pybamm.lithium_ion.SPM()
parameter_values = pybamm.ParameterValues("Chen2020")
t_eval = np.linspace(0, 500, 240)
solution = pybamm.Simulation(model, parameter_values=parameter_values).solve(t_eval=t_eval)
dataset = pybop.Dataset({
    "Time [s]": t_eval,
    "Current [A]": solution["Current [A]"](t_eval),
    "Voltage [V]": pybop.add_noise(solution["Voltage [V]"](t_eval), 2e-3),
})
parameter_values.update({
    "Negative electrode active material volume fraction": pybop.Parameter(
        distribution=pybop.Gaussian(0.6, 0.05, truncated_at=[0.5, 0.8])),
    "Positive electrode active material volume fraction": pybop.Parameter(
        distribution=pybop.Gaussian(0.48, 0.05, truncated_at=[0.4, 0.7])),
})
simulator = pybop.pybamm.Simulator(model, parameter_values=parameter_values, protocol=dataset)
cost = pybop.SumSquaredError(dataset)
problem = pybop.Problem(simulator, cost)
optim = pybop.SciPyMinimize(problem, options=pybop.SciPyMinimizeOptions(
    verbose=True, maxiter=100, method="L-BFGS-B", jac=True))
result = optim.run()
```

MCMC variant: `LogPosterior(simulator, GaussianLogLikelihood(dataset))` +
`pybop.DifferentialEvolutionMCMC(log_pdf, options=pybop.PintsSamplerOptions(...))`
(upstream `monte_carlo_sampling.py`).

### Limitations (relevant to us)

- No literature retrieval/extraction, **no parameter provenance** (a `bpx`
  extra is declared but unused in library code) → our core contribution stays.
- No calibration/validation split logic; no residual-diagnostics workflow.
- Identifiability tooling is thin (2-parameter Hessian only; FIM removed).
- PINTS optimisers/samplers lack seed options (seed `numpy.random` ourselves).
- API instability across major versions (v25.10 restructure).

## 3. PyProBE (experimental data processing) — 2.6.1

- License: BSD-3-Clause. JOSS 2025, doi:10.21105/joss.07474 (Holland, Cummins
  & Marinescu, Imperial College London). Beta, actively maintained (release
  2026-10-14); recent releases mostly dependency maintenance.
- **Requires Python >=3.11,<3.13** (hard cap). Core deps: polars (>=1.18,<2),
  pandas, numpy, pydantic, fastexcel, streamlit, plotly, scikit-learn, sympy,
  loguru... Optional `pybamm[cite]>=25.1.1` extra.

### Capability map (exact API, verified on installed package)

| Need | Public API | Notes |
|---|---|---|
| Ingestion | `pyprobe.Cell(info=...)`; `cell.import_from_cycler(procedure_name, cycler="neware"\|"biologic"\|"biologic_MB"\|"arbin"\|"basytec"\|"maccor"\|"novonix"\|"generic", input_data_path, readme_path=..., column_importers=...)`; `pyprobe.process_cycler_data(...)`; `pyprobe.make_cell_list(record_filepath, worksheet_name)` (Excel Experiment Record); `cell.import_data(...)` (pre-converted `.parquet`) | Multi-file glob inputs supported. Column remapping via `pyprobe.cyclers.column_maps`: `ColumnMap`, `DateTimeMap`, `CastAndRenameMap`, `ConvertUnitsMap`, `CapacityFromChDchMap`, `ConvertTemperatureMap`, `StepFromCategorical`. |
| Structure | `Cell.info: dict`; `Cell.procedure[name] -> Procedure`; `.experiment(*names) -> Experiment`; `.cycle(*nums) -> Cycle`; `.step(...)/.charge()/.discharge()/.rest()/.constant_current()/.constant_voltage() -> Step` | Zero-based indices; chainable. |
| Metadata | `Cell(info={"Name", "Chemistry", "Nominal Capacity [Ah]", ...})`; per-procedure **README.yaml** with PyBaMM experiment strings + cycle loops; `column_definitions`/`define_column`/`print_definitions` | README.yaml is required for `.experiment()` filtering. |
| Filtering/data | `.data`/`.df` (properties, **polars** DataFrame); `.get(*cols)` (numpy, unit conversion on the fly, e.g. `.get("Current [mA]")`); `result["Voltage [V]", "Time [s]"]` | Canonical columns: `Time [s]`, `Current [A]`, `Voltage [V]`, `Capacity [Ah]`, `Step`, `Cycle`, `Event`, `Date`, derived `* Time [s]`/`* Capacity [Ah]` per level. |
| Prep for estimation | `.get()` numpy arrays → `pybop.Dataset`; `pybop.import_pyprobe_result` helper on the PyBOP side; `pyprobe.analysis.smoothing.downsample`; interpolator factories | No optimizer except DMA OCV fitting. |
| Statistics | `pyprobe.analysis.cycling.summary(...)` (SOH, CE, capacities); `pyprobe.analysis.pulsing` (`get_ocv_curve`, `get_resistances`, `Pulsing`); `pyprobe.analysis.degradation_mode_analysis` (OCP, `run_ocv_curve_fit`, `quantify_degradation_modes`, batch DMA); `differentiation`, `smoothing` | `pyprobe.analysis` is a submodule (explicit import). |
| Visualisation | `Result.plot(x=..., y=...)` (pandas-style); `Result.hvplot(...)` (extra); `pyprobe.plot.seaborn` wrapper; `pyprobe.launch_dashboard()` (streamlit) | |
| PyBaMM bridge | `RawData.pybamm_experiment -> list[str]` (PyBaMM operating-condition strings from README); `cell.import_pybamm_solution(procedure_name, experiment_names, solution, optional_variables=...)` (simulations become filterable like data) | **No PyBOP integration exists upstream** — `pybop.import_pyprobe_result` is the bridge on the PyBOP side. |

### Canonical example (verified; from official docs + our exp4)

```python
import pyprobe
cell = pyprobe.Cell(info={"Name": "Sample cell", "Chemistry": "NMC622",
                          "Nominal Capacity [Ah]": 0.04})
cell.import_from_cycler(procedure_name="Sample", cycler="neware",
                        input_data_path=".../sample_data_neware.xlsx",
                        readme_path=".../README.yaml")
discharge = cell.procedure["Sample"].experiment("Break-in Cycles").cycle(2).discharge()
voltage, current = discharge.get("Voltage [V]", "Current [A]")   # numpy
df = discharge.data                                             # polars
```

Upstream sample data ships in the repo
(`tests/sample_data/neware/` + `tests/sample_data/LGM50/*.parquet`).

### Limitations

- Python ≤3.12 hard cap; `polars<2` pin.
- No simulation/optimization; **BioLogic binary `.mpr` unsupported**
  (`.mpt`/`.txt` only); other cycler formats need the `generic` importer.
- README.yaml effectively required for experiment-level filtering.
- API churn in 2.x (removed `Plot` class; deprecated 1.x methods) — target
  the 2.1+ API (`import_from_cycler`, `import_data`, `add_data`, `set_soc`,
  `get`).

## 4. What we will NOT build (reused instead)

| Functionality | Reused from |
|---|---|
| Battery model simulation / sensitivities | PyBaMM (via `pybop.pybamm.Simulator` in fitting; our `pybamm_engine` standalone) |
| Synthetic dataset construction, noise injection | PyBOP (`pybop.Dataset`, `pybop.add_noise`, `import_pybamm_solution`) |
| Cost functions, bounded deterministic optimisation | PyBOP |
| MCMC / Bayesian inference machinery | PyBOP (PINTS backends) |
| Cycler-file ingestion, step/cycle filtering, cycle statistics | PyProBE |
| Experiment-string bridge to PyBaMM experiments | PyProBE (`pybamm_experiment`) |
| Grouped/identifiable reduced models | PyBOP (`GroupedSPM`/`GroupedSPMe`) |

## 5. What remains genuinely ours (research contribution)

Literature retrieval; LLM-based parameter extraction; parameter provenance
(source, location, conditions, status); unit/condition normalization;
deterministic scientific validation and conflict handling; domain adaptation
of extraction models; literature-informed priors feeding PyBOP Bayesian
estimation; identifiability/UQ beyond PyBOP's 2-parameter Hessian; closed-loop
discrepancy diagnosis and refinement; audit trails and reproducibility
manifests.
