# Scientific Limitations & Responsible Disclosure (v0.1.0-beta.1)

This document states what PARALLM demonstrates and, critically, what it does
**not** establish. Read before citing or operationalizing results.

## 1. No independent experimental validation (this beta)

**The public beta does not claim independent experimental validation.** No
calibrated parameters are validated against an independent, held-out
experimental dataset in this release. A real-data fitting experiment is
**designed but not run** (T6): disjoint calibration/validation, active-material
volume fractions primary (positive diffusivity secondary; negative diffusivity
≤2C unobservable per P2), executed via the PyBaMM engine — blocked pending
eligible data. See `docs/P5_REAL_DATA_EXPERIMENT_DESIGN.md`.

## 2. Experimental data availability — unresolved

No dataset currently in the repository satisfies the Chen2020-aligned
validation target (LG M50 BoL, 25 °C ± 1 K, CC-CV + galvanostatic discharge at
0.5C/1C/2C + low-rate OCV, documented license, independent of calibration):
- The audited LG M50 PyProBE sample (`data/registry/dataset_audit_lgm50.json`)
  is C/10 pseudo-OCV **charge** at ~32.3 °C with **license UNRESOLVED** —
  ineligible for calibration or validation claims.
- Chen2020 original experimental traces are **UNRESOLVED / not present**.
Details and required protocol: `docs/P5_DATA_ACQUISITION.md`,
`docs/EXPERIMENTAL_DATA_REQUIREMENTS.md`. Calibration data must never double as
validation data.

## 3. Synthetic recovery ≠ experimental validation; optimization ≠ identifiability

P2 demonstrates synthetic parameter recovery on seeded, model-generated data and
reports sensitivity/identifiability analyses. A successful optimization or a
good synthetic recovery **does not** prove parameter identifiability on real
cells and **is not** experimental validation. Structural/model mismatch,
unmodeled physics, and parameter correlations (e.g., electrolyte diffusivity ↔
exchange current, |corr|>0.8 in P2) limit what voltage data can identify.

## 4. Literature extraction — P5 v3 (37 items, 3 repeats/arm)

Benchmark v3 (37 items, 8 dev/29 eval, 6 abstention, 6 docs, v3 only) was run
with 3 repeats per LLM arm (mean ± std). Grounded retrieval
(`retrieval_strict`, n=3, all/eval) achieved value 0.946±0.022 / 0.953±0.017,
provenance 0.928±0.026 / 0.929±0.001, qualifier 0.741±0.033 / 0.776±0.019,
false extraction 0.000, abstention 1.000; strict no-evidence abstained on all
items. **However:**

- **Experimental-condition extraction is weak (explicit).** Condition
  completeness is **0.116 (all) / 0.035 (eval)** under retrieval (many
  passages lack an explicitly stated temperature+cell_config; inference is
  forbidden). The memory arm's higher condition score (0.483) is **ungrounded**
  filling, not evidence.
- **Memory-without-evidence produces unsupported claims:** provenance 0.000,
  false extraction 0.275, abstention 0.333. It must not be treated as a
  parameter source.
- **Residual errors remain** (e.g., Rct-vs-j0 payload confusion, table
  scale/header parsing on specific items) and **run-to-run variance** is
  observed at temperature 0. Per-item consistency: `results/p5/benchmark_v3/`.
- Results depend on the configured model/endpoint/prompt and the 37-item
  fixture; they measure evidence-grounded extraction on this benchmark, not
  general electrochemical reasoning.

Full numbers and protocol: `docs/BENCHMARK_RESULTS.md`,
`docs/P5_RETRIEVAL_ABLATION.md`, `docs/P5_EXTRACTION_RELIABILITY.md`.

## 4b. v0.2 evaluation status (expert agreement)

The v0.2 headline metric is **agreement between the applicability rubric and
expert decisions** on a labelled set of ≥20 conflict/applicability cases
(`docs/ROADMAP_V0.2.md` §3.1). Two honest caveats, stated wherever the number
appears:

- The labels are **drafted by the assistant and pending review by the project
  owner**; agreement against drafted labels is *not* yet agreement with reviewed
  expert judgement.
- The labelled set must contain ambiguous cases whose expert answer is
  `REVIEW`; agreement computed only on decidable cases would overstate the
  rubric's usefulness.

## 5. Scope, model, and parameter caveats

- Target demonstrator: PyBaMM DFN, Chen2020 (LG M50 graphite/NMC), isothermal
  298.15 K reference; pinned `pybamm==26.8.0.0`. Conclusions may not transfer
  to other chemistries, formats, models, temperatures, or degradation states.
- Chen2020 paper values vs the packaged PyBaMM parameter set differ in
  documented ways (e.g., tuned effective vs measured values, set extensions);
  see `docs/CHEN2020_DISCREPANCY_ANALYSIS.md`. Conflicts are preserved, not
  silently resolved.
- LLM output never overwrites scientific parameters without deterministic
  validation and explicit approval. Missing/unclear values remain unresolved.

## 6. Non-goals of this beta

No autonomous parameter invention, no fine-tuned electrochemistry LLM, no
claims of universal identifiability, no independent experimental validation,
and no real-data calibration in P5. P6–P8 (closed loop, fine-tuning, further
validation) are not started.