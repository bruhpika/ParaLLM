# Changelog

All notable changes to PARALLM are documented here. The project follows the
milestone plan (P0–P8); scientific behavior is versioned conservatively and
documented with provenance.

## [0.1.0-beta.1] - 2026-11-08 (public beta)

First public beta. **No independent experimental validation is claimed.**

### Added
- **P0 — PyBaMM DFN baseline:** pinned PyBaMM (26.8.0.0) Chen2020 DFN, 1C
  discharge to 2.5 V (IDAKLU), deterministic manifests, figures, and tests.
- **P1 — Ecosystem audit:** verified compatibility for PyBOP 26.10 /
  PyProBE-Data 2.6.1 on CPython 3.12.16; revised architecture and integration
  plan.
- **P2 — Estimation & identifiability (PyBOP):** synthetic data generation,
  bounded fitting, sensitivity/identifiability, and a synthetic parameter
  recovery benchmark (synthetic recovery ≠ experimental validation).
- **P3 — Literature & provenance:** document ingestion/store, deterministic
  + optional LLM extraction, parameter registry with provenance/qualifiers,
  validation checks, dataset linkage.
- **P4 — LLM extraction evaluation:** benchmark v2 (20 items, 3 real docs,
  3 arms); Chen2020 discrepancy analysis; LG M50 dataset audit/feasibility
  (no fitting performed).
- **P5 — Reliability, v3 benchmark, retrieval ablation:** benchmark v3 (37
  items, 6 docs incl. 3 CC BY PDFs, 8 dev/29 eval, 6 abstention, 3 repeats
  per LLM arm, mean±std); retrieval_strict id 0.718±0.009, value
  0.946±0.022, provenance 0.928±0.026, condition 0.116±0.011 (weak),
  qualifier 0.741±0.033, false 0.000, abst 1.000; memory-without-evidence
  yields unsupported claims (prov 0.000, false 0.275); strict no-evidence
  abstains. Deterministic provenance diagnostics. Real-data experiment
  designed (not run; eligible dataset unresolved).
- Release-quality docs, MIT software license with third-party scope
  note, data-provenance separation, and reproducibility/limitation
  disclosure.

### Security / compliance
- LLM API keys read from environment only; no secrets committed.
- Copyrighted Chen2020 supplement PDF removed from git tracking (acquire
  separately); CC BY sources redistributed with attribution and recorded
  license evidence.

### Known limitations
- No independent experimental validation; experimental-condition extraction
  is weak (condition completeness 0.116 all / 0.035 eval under retrieval);
  eligible Chen2020-aligned multi-rate validation dataset unresolved.
