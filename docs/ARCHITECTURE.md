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
