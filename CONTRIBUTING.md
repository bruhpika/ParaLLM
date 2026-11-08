# Contributing to PARALLM

PARALLM is a scientific research prototype (public beta). Contributions are
welcome, but scientific and provenance rules are **non-negotiable**.

## Ground rules (must follow)

- **Never invent** electrochemical parameter values, PyBaMM parameter names,
  APIs, or model options. Verify names/options against the pinned installed
  PyBaMM version (introspect; do not assume).
- Every literature-derived parameter retains source, exact location, original
  value, unit, experimental conditions, and extraction status.
- Distinguish: user-supplied / literature-derived / calculated / assumed /
  calibrated / unresolved. Never silently substitute missing values.
- A successful optimization ≠ identifiability; synthetic recovery ≠
  experimental validation. Never use calibration data as validation data.
- An LLM must never directly overwrite scientific parameters without
  deterministic validation and explicit approval.
- Never commit secrets, API keys, credentials, or private data. Never
  overwrite raw experimental data or source documents.

## Development setup

```bash
# Core (PyBaMM-only, CPython 3.10–3.15)
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/pip install -e ".[dev]"
# Full ecosystem (PyBOP/PyProBE/SALib/pypdf/polars) — verified on CPython 3.12.16
python3.12 -m venv .venv-ecosystem312 && .venv-ecosystem312/bin/pip install -r requirements-integration.lock && .venv-ecosystem312/bin/pip install -e ".[dev,ecosystem]"
```

## Tests and quality

```bash
.venv/bin/python -m pytest                       # core (ecosystem tests skip)
.venv-ecosystem312/bin/python -m pytest          # full suite (201 passed in the release env)
.venv-ecosystem312/bin/python -m compileall -q src benchmarks scripts tests
```

- Add unit tests for every new module; integration test for anything
  touching PyBaMM. Keep tests deterministic; record seeds for stochastic
  cases. Scientific benchmarks stay in `benchmarks/` (separate from
  `tests/`).
- All PyBaMM interaction goes through `pybamm_engine/`; other modules must
  not call PyBaMM APIs directly.

## Pull requests

- Keep changes focused and documented. Preserve P0–P5 milestone history and
  scientific behavior; do not introduce new scientific functionality in
  release-hardening PRs.
- Update docs when behavior, configs, or reproducibility steps change.
- Attribute third-party code and preserve original copyright notices.
  Separate software licenses from dataset/document licenses
  (docs/DATA_PROVENANCE.md). Do not redistribute datasets or papers without
  permission.
- By contributing, you agree your contributions are licensed under the
  repository's MIT license (software only).
