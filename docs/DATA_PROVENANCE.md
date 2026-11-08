# Data, Document & License Provenance

This separates **software licensing** from **dataset/document licensing**.
The repository's MIT `LICENSE` covers PARALLM source code only; it
does **not** grant rights to third-party datasets, papers, PDFs, or parameter
sets. Materials are redistributed only where permitted, with attribution and
recorded license evidence.

## Policy

- Preserve raw data and source documents; never overwrite them. Keep
  acquisition metadata (URL/DOI, retrieval date, sha256, license/evidence).
- Distinguish user-supplied / literature-derived / calculated / assumed /
  calibrated / unresolved values. Do not invent sources or values.
- Do not redistribute datasets or papers without permission. When permission
  is unclear, **do not commit the file**; keep an acquisition note and
  derived, provenance-linked artifacts where appropriate.

## Redistributed in-repo (permitted / evidenced)

| material | location | license / evidence | notes |
|---|---|---|---|
| Laue et al. 2021 (J Appl Electrochem 51:1253–1265) | `data/raw_documents/laue2021_jappl_electrochem_51_1253/` | **CC BY 4.0** (PDF text verified) | archived + sha256 in `data/raw_documents/p5_sources/acquisition_manifest.json`; ingested to `data/literature_store/` |
| Dessantis et al. 2023 (Batteries 9:146) | `data/raw_documents/dessantis2023_batteries9_0146/` | **CC BY 4.0** (verified) | same |
| Goussian et al. 2024 (Batteries 10:205) | `data/raw_documents/goussian2024_batteries10_00205/` | **CC BY 4.0** (verified) | same; no numeric cell parameters (data confidential) |
| PyBaMM parameter-sets documentation snapshot | `data/raw_documents/pybamm_parameter_sets_docs/` | PyBaMM project docs (PyBaMM is BSD-licensed upstream; snapshot kept with source URL/retrieval metadata) | ingested text snapshot |
| Chen2020 **text** extract (article) | `data/raw_documents/chen2020_jes_167_080534/`, `data/literature_store/` | ECS © — **text extract retained for provenance/benchmarking**; not a redistribution of the publisher PDF | used by v2/v3 fixtures with provenance |
| Benchmark fixtures & derived results | `data/eval/`, `results/p4/`, `results/p5/`, `data/registry/` | produced by this project (MIT, subject to underlying source terms noted per item) | include recorded provenance/qualifiers; raw model outputs preserved |

License evidence and sha256: `data/raw_documents/p5_sources/acquisition_manifest.json`.

## NOT redistributed (acquire separately)

| material | status | how to obtain / note |
|---|---|---|
| Chen et al. 2020 supplementary PDF (JES 167 080534, DOI 10.1149/1945-7111/ab9050) | **removed from git tracking**; gitignored | ECS ©, redistribution permission not verified. Obtain from the publisher DOI and place at `data/raw_documents/chen2020_supplement/JES_167_8_080534_suppdata.pdf`; see `data/raw_documents/chen2020_supplement/ACQUISITION.md`. Derived benchmark items/results remain with provenance. |
| LG M50 experimental sample data (PyProBE) | **gitignored** (`data/external/`) — not in repo | Upstream license **UNRESOLVED** in this audit; the audited file is C/10 pOCV charge @ ~32.3 °C (ineligible for the T6 validation target). See `data/registry/dataset_audit_lgm50.json`, `docs/P5_DATA_ACQUISITION.md`. |
| Chen2020 original experimental traces | **UNRESOLVED / not present** | No in-repo copy; acquire via authors/publisher data availability + license verification before use. |

## Upstream software (attributed, not vendored as source here except via deps)

PyBaMM (MIT), PyBOP (MIT), PyProBE-Data and their transitive
dependencies are installed from PyPI per the lockfiles; consult their upstream
LICENSE/NOTICE files in installed distributions. PyBaMM's Chen2020
`ParameterValues` are loaded from the installed PyBaMM library (not hand-typed).

## Third-party code in this repo

Repository source is original to the project except where explicitly attributed;
no vendored third-party source files carrying separate copyright notices were
identified in `src/`/`tests/`/`scripts/`/`benchmarks/` during the release audit.
Characterization baselines reference upstream-derived numeric behavior for
regression gating (documented in `tests/characterization/`). If you add
third-party code, preserve its copyright/license notice and record it here.