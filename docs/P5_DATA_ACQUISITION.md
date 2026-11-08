# P5 Data Acquisition (Task 5)

P5 Task 5 investigates experimental datasets for the Chen2020/LG M50
demonstrator. **No calibration is run.** Calibration data must never double as
validation data (rule 9). Every acquisition status below is evidenced; nothing
is invented.

## Literature sources acquired (T2, completed)

Three CC BY 4.0 papers were acquired, license-verified from PDF text, archived
with sha256, and ingested (see `P5_BENCHMARK_EXPANSION.md` and
`data/raw_documents/p5_sources/acquisition_manifest.json`):
Dessantis 2023 (Batteries 9:146), Goussian 2024 (Batteries 10:205), Laue 2021
(J Appl Electrochem 51:1253–1265). A candidate Mondragon thesis
(ebiltegia.mondragon.edu) was unreachable (connection timeout) and dropped.

## Experimental data status (LG M50 / Chen2020 cell)

### Audited, locally available (P4 audit artifact)

| dataset | source | protocol / conditions | license | fit for T6? |
|---|---|---|---|---|
| `pyprobe_sample/lgm50` (LGM50_BoL_RPT0_short_CA4.parquet) | PyProBE sample data (`data/external/`, gitignored; sha256 + audit in `data/registry/dataset_audit_lgm50.json`) | C/10 pseudo-OCV **charge** only; charge at ~32.3 °C (README notes thermal control issue); no multi-rate discharge at 25 °C | **UNRESOLVED** (upstream license not established locally) | **No** — protocol (charge pOCV) and temperature (32.3 °C vs 298.15 K isothermal model) do not match the Chen2020 25 °C discharge validation target; usable only as an ingestion/format reference, not for calibration or validation claims. |

### Required for a Chen2020-aligned real-data experiment (per `docs/EXPERIMENTAL_DATA_REQUIREMENTS.md`)

LG M50 (5 Ah) beginning-of-life, temperature-controlled **25 °C ± 1 K**,
standardized charge (CC-CV, documented), then galvanostatic **discharge at
0.5C / 1C / 2C** (and a low-rate C/20–C/30 OCV reference) over 2.5–4.2 V, with
rest/relaxation recorded, time-synchronized V/I/T, documented cell history and a
clear license permitting research use. Calibration and validation subsets must be
disjoint (rule 9).

### Unresolved / acquisition-needed candidates

| candidate | basis | availability | blocker / next step |
|---|---|---|---|
| Chen2020 experimental traces (original characterization/validation data underlying JES 167 080534) | Direct match to the Chen2020 parameter set/cell | **UNRESOLVED** (not present in-repo) | Contact the Chen2020 authors / check the paper's data-availability statement and any linked repository; obtain raw traces + metadata + license/permission before any use. |
| Public LG M50 multi-rate discharge datasets (e.g., Oxford/Battery Degradation / About:Energy-published LG M50 characterisation sets, or other openly licensed LG M50 cycling with 25 °C C/2–2C discharge) | Cell family match (LG M50) but **parameter-set/provenance match must be verified** against Chen2020 | **UNRESOLVED from this repo** (not downloaded; licenses/protocols not verified here) | Identify a specific dataset release, verify LG M50 lot/generation, confirm 25 °C controlled multi-rate discharge + OCV, verify license, archive with sha256/manifest, and audit protocol before selection. Do not assume equivalence to Chen2020. |
| PyBaML/PyProBE-distributed LG M50 files beyond the local sample | Format-compatible ingestion path exists | **UNRESOLVED** | Verify upstream license and whether any file provides 25 °C multi-rate discharge (not the audited charge pOCV); record in a manifest before use. |

## Conclusion

No dataset currently in the repository satisfies the T6 validation target
(Chen2020-aligned, 25 °C, multi-rate discharge, licensed, independent of
calibration). The LG M50 PyProBE sample is **audited but ineligible** for that
role. Real-data fitting therefore remains **blocked on data acquisition +
license verification**; the T6 deliverable is an experiment design (not a
calibration run) — see `P5_REAL_DATA_EXPERIMENT_DESIGN.md`.
