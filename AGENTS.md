# AGENTS.md — Project Rules for Contributors and Agents

This repository is a scientific research software project (closed-loop LLM
framework for physics-based battery parameterization). The following rules are
**non-negotiable** and bind every human contributor and every automated agent.

## Scientific rules — non-negotiable

1. Never invent electrochemical parameter values.
2. Never invent PyBaMM parameter names, APIs or model options.
3. Verify all parameter definitions and units against the installed PyBaMM
   version and relevant documentation.
4. Every literature-derived parameter must retain its source, exact source
   location, original value, unit, experimental conditions and extraction
   status.
5. Distinguish clearly between:
   - User-supplied
   - Literature-derived
   - Calculated
   - Assumed
   - Calibrated
   - Unresolved
6. Never silently substitute missing parameter values.
7. A successful optimization does not prove parameter identifiability.
8. Synthetic parameter recovery is not equivalent to experimental validation.
9. Never use calibration data as independent validation data.
10. Never allow an LLM to directly overwrite scientific parameters without
    deterministic validation and explicit approval.

## Engineering rules

- Use modular Python architecture.
- Use type hints and structured data models.
- Write unit and integration tests.
- Keep scientific benchmarks separate from software tests.
- Record software versions, configurations, random seeds and simulation
  settings.
- Preserve raw data.
- Never overwrite experimental data or source documents.
- Make every major operation reproducible.
- Prefer simple, interpretable implementations over unnecessary abstraction.
- Document assumptions and limitations.

## Development workflow

Work incrementally. Do not implement the entire project at once. Work only on
the milestone explicitly assigned by the user.

**Before implementing a major module:**

1. Explain the intended architecture.
2. Identify scientific and engineering dependencies.
3. Explain potential failure modes.
4. Propose an implementation plan.
5. Wait for approval when the task changes scientific assumptions or scope.

**After implementation:**

1. Run relevant tests.
2. Report what passed and failed.
3. Explain scientific limitations.
4. Update documentation.
5. List unresolved issues.

The user is the scientific decision-maker. The assistant is the software
engineering and research implementation partner.

## Repository conventions

- `src/pybamm_closed_loop/` — library code (src layout, installed editable).
- `tests/` — software correctness only (unit/ + integration/). Fast, deterministic.
- `benchmarks/` — scientific performance benchmarks only. Never mixed into
  `tests/`; excluded from default pytest runs via the `benchmark` marker.
- `configs/` — declarative, version-pinned run configurations (YAML).
- `data/raw_documents/` and `data/experimental/` — immutable; never overwrite.
- `results/` — generated artifacts (arrays, manifests, figures); regenerable
  from configs via `scripts/`.
- All PyBaMM interaction goes through `pybamm_engine/`; other modules must not
  call PyBaMM APIs directly.
- Whenever a PyBaMM name, option, parameter or solver is used, verify it
  against the pinned installed version first (introspect, do not assume).

## Testing

```bash
.venv/bin/python -m pytest              # unit + integration (software correctness)
.venv/bin/python -m pytest -m benchmark # scientific benchmarks (explicit opt-in)
```

- Every new module ships with unit tests.
- Anything touching PyBaMM ships with at least one integration test.
- Tests must be deterministic; record seeds for any stochastic test.

## Commit hygiene

- Commit after each completed milestone/task, with messages describing the
  scientific content of the change.
- Never commit secrets. Never commit regenerated caches (`.venv`, `__pycache__`).
