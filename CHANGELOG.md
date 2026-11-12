# Changelog

All notable changes to PARALLM are documented here. The project follows the
milestone plan (P0–P8); scientific behavior is versioned conservatively and
documented with provenance.

## [Unreleased] — v0.2 "Parameter Assembly" (planned, not implemented)

Proposal only; no v0.2 code exists yet. Scope, exit criteria, risks and
decisions: `docs/ROADMAP_V0.2.md`. Positioning/competitive scan:
`docs/POSITIONING.md`.

### Planned
- **V2.1** Applicability & conflict engine — auditable, hand-set rubric; decision
  taxonomy `USE / FIX / CALIBRATE / MEASURE / REJECT`; rule-firing transcript;
  conflicts preserved with alternatives.
- **V2.2** Parameter assembly report + CLI/API (`parallm assemble`) → per-parameter
  dossier, set summary, JSON/Markdown/PyBaMM export.
- **V2.3** Observability join — per-parameter identifiability (FIM/Sobol from P2)
  → fit/fix/measure action matrix.
- **V2.4** Synthetic end-to-end validation (assemble → calibrate → validate on
  held-out rates) with a negative control; labelled *synthetic*, never
  experimental.
- **V2.5** Evidence engineering (P8′, replaces fine-tuning) — multi-window
  retrieval, table-aware chunking, condition-window expansion, verification pass;
  target: condition completeness ≥0.5 on a **private v4** with false extraction
  still 0.000.
- **V2.6** Closed loop (P7) — parameter-targeted: flagged field → targeted
  evidence request → retrieval → extraction → validation → approval → recalibrate.
- **V2.7** Product/community — PyPI (`parallm-pybamm`), CI (3.10–3.12), docs
  site, examples gallery, conflict-resolution mini-benchmark (v4a).

### Decisions (2026-11-08)
D1 auditable hand-set rubric · D2 LG M50 only (multi-chemistry → TODO) ·
D3 no fine-tuning · D4 no real-data-dependent claims · D5 private benchmarks ·
D6 human gate mandatory · D7 LLM out of the numeric decision path.

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
