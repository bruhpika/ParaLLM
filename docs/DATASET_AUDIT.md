# Dataset Audit (P3 / Part F)

Code: `src/pybamm_closed_loop/datasets/` (`audit.py`, `pyprobe_link.py`).
Artifact: `data/registry/dataset_candidates.json` (regenerate with
`.venv-ecosystem312/bin/python scripts/p3/build_dataset_audit.py`).
Requirements checklist: `docs/EXPERIMENTAL_DATA_REQUIREMENTS.md` (P2).

**No dataset is selected in P3.** Selection requires a complete compliance
table per candidate and an explicit scientific decision by the user.

## 1. The Neware sample is NOT LG M50 validation data

Audited deterministically from the local files
(`data/external/pyprobe_sample/neware/`, PyProBE Neware sample):

| Fact | Observed |
|---|---|
| rows / columns | 789,589 x 7 (Date, Time [s], Step, Current [A], Voltage [V], Capacity [Ah], Event) |
| current range | -0.020 to +0.004 A (20 mA discharge pulses, 4 mA charge) |
| voltage range | 3.000 to 4.200 V |
| capacity range | 0.021 to 0.062 Ah (~40 mAh scale) |
| temperature | no temperature column (UNRESOLVED) |
| protocol | README.yaml: 4 mA CC-CV charge (hold to 0.04 A), 20 mA discharge pulses to 3 V (PyBaMM experiment strings, extracted via PyProBE's `readme_processor`) |
| chemistry | NMC622 small-format (per P1 ecosystem audit; not stated in the local README.yaml) |

Verdict: **INCOMPATIBLE** with the LG M50 demonstrator on identity,
capacity, temperature recording, voltage window (3.0-4.2 V vs 2.5-4.2 V)
and protocol. It is an ingestion test only — exactly as the milestone
requires.

## 2. Candidate datasets investigated (web, 2026-11-06)

| Candidate | Verified facts | Verdict |
|---|---|---|
| **PyProBE LGM50 sample** (`ImperialCollegeLondon/PyProBE`, `tests/sample_data/LGM50/`): `NDK - LG M50 deg - exp 2,2 - rig 3 - 25degC - cell C - BoL - RPT0_short_CA4.parquet` (2.19 MB) + `README.yaml` | LG M50, 25 degC, beginning-of-life RPT (file name); processed parquet in the repo (not in the pip wheel); repo code BSD-3-Clause (data license UNRESOLVED) | **CANDIDATE** — content audit pending (download + PyProBE processing against the requirements table) |
| **Chen2020 validation traces** (C/2, 1C, 1.5C discharge + relaxation, 3 cells, 25 degC chamber; DOI 10.1149/1945-7111/ab9050) | protocol/cells verified from the article text; the Data-availability statement (verified quote) covers the parameter set + OCVs in PyBaMM but does NOT state a deposit for the raw validation traces; supplementary material at stacks.iop.org/JES/167/080534/mmedia | **CANDIDATE** — ideal match if raw traces can be obtained; availability of raw observations UNRESOLVED |
| **BatteryArchive.org** LG M50 records | site index is JavaScript-rendered (data.html/list.html return a static shell); based on github.com/battery-lcf (verified footer); no LG M50 entry could be verified automatically | **UNRESOLVED** — requires manual browser verification |
| Neware 40 mAh NMC622 sample (local) | see section 1 | **INCOMPATIBLE** |

Per-candidate requirement rows (identity, capacity, temperature, C-rates,
voltage limits, protocol, metadata completeness, raw/processed
observations) are stored machine-readably in
`data/registry/dataset_candidates.json` with evidence strings.

## 3. Open questions before any selection

1. PyProBE LGM50 sample: does the RPT contain the 0.5C/1C/2C discharge
   windows and relaxation periods required by
   `docs/EXPERIMENTAL_DATA_REQUIREMENTS.md`? (README.yaml is 339 bytes and
   must be processed; measured capacity and voltage limits must be read
   from the parquet.) What is the explicit data license?
2. Chen2020 validation traces: can the raw per-cell voltage traces be
   obtained (supplementary data or authors)? If not, this dataset cannot be
   used as independent validation data (rule 9).
3. BatteryArchive: manual verification of LG M50 presence and metadata.

## 4. Recommendation

Proceed with the **PyProBE LGM50 BoL RPT** as the primary candidate for a
local content audit (P4): download the parquet + README.yaml, process via
PyProBE, complete the compliance table, and only then propose it for the
calibration/validation split. In parallel, request the Chen2020 validation
traces — if obtained, they are the scientifically ideal validation set for
the demonstrator. The Neware sample remains ingestion-test-only.
