# Installation

## Supported Python versions

| scope | Python | verified env | notes |
|---|---|---|---|
| Core (PyBaMM baseline, registry, offline/deterministic extraction) | **3.10–3.15** | CPython 3.14.8 (`.venv`) | `pyproject.toml`: `>=3.10,<3.16` |
| Full ecosystem (PyBOP, PyProBE-Data, SALib, pypdf, polars) | **3.10–3.12** (practical) | **CPython 3.12.16** (`.venv-ecosystem312`) | `PyProBE-Data` requires `python_version < 3.13`; pypdf/polars capped below unverified majors |

## Pinned / verified versions (ecosystem env, CPython 3.12.16)

pybamm **26.8.0.0** · pybop **26.10** · pyprobe **2.6.1** · numpy 2.5.4 ·
scipy 1.18.1 · pandas 3.1.1 · pydantic 2.12.5 · pypdf 6.21.4 · polars 1.44.2.
The PyBaMM engine refuses to run on a version mismatch.

## Lockfiles

- `requirements.lock` — verified freeze of the **core** venv (CPython 3.14.8).
  Not a cross-platform resolve spec; install into a matching venv.
- `requirements-integration.lock` — verified freeze of the **ecosystem** venv
  (CPython 3.12.16, PyBOP/PyProBE stack). **Do not build this env on 3.14+.**

## Install — core

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -c "import pybamm; print(pybamm.__version__)"   # 26.8.0.0
.venv/bin/python -m pytest -q   # ecosystem-dependent tests skip
```

## Install — full ecosystem (recommended for P2–P5)

```bash
python3.12 -m venv .venv-ecosystem312
.venv-ecosystem312/bin/pip install -r requirements-integration.lock
.venv-ecosystem312/bin/pip install -e ".[dev,ecosystem]"
.venv-ecosystem312/bin/python -c "import pybamm,pybop,pyprobe; print(pybamm.__version__, pybop.__version__, pyprobe.__version__)"
.venv-ecosystem312/bin/python -m pytest -q   # 201 passed in the release env
```

The `ecosystem` extra installs only direct imports (`pybop`, `pints`/`SALib`,
`pypdf`, `polars`, `PyProBE-Data`); `cma`/`scikit-learn`/`fastexcel` arrive
transitively. Bounds exclude `pypdf 7.x` and `polars 2.x` (unverified).

## Clean-environment verification (release check)

```bash
tmp=$(mktemp -d) && python3.12 -m venv "$tmp/venv" \
  && "$tmp/venv/bin/pip" install -r requirements-integration.lock \
  && "$tmp/venv/bin/pip" install -e ".[dev,ecosystem]" \
  && "$tmp/venv/bin/python" -m pytest -q
```

## Configuration & secrets

Run configs live in `configs/` (YAML, version-pinned). The optional LLM client
reads credentials from the environment and **never** writes them to artifacts:

```bash
export PYCL_LLM_API_KEY=...     # required for LLM arms; never commit
export PYCL_LLM_BASE_URL=...    # OpenAI-compatible endpoint
export PYCL_LLM_MODEL=...      # e.g. a chat-completions model id
```

Offline/deterministic paths (`--provider offline`, the `offline` condition) need
no API key.

## Known environment notes

- IDAKLU/SUNDIALS comes via PyBaMM wheels; use the pinned version.
- The gitignored LG M50 sample data under `data/external/` is not required for
  the core/benchmark test paths; external-data-dependent tests may be
  skipped/absent in a fresh checkout.
- The copyrighted Chen2020 supplement PDF is not redistributed (see
  `docs/DATA_PROVENANCE.md`); P4/P5 supplement-derived benchmark fixtures and
  results are in-repo, but re-ingesting the raw supplement requires obtaining
  it separately.