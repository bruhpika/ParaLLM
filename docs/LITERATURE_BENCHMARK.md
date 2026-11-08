# P4 — Literature benchmark design (Part B)

Design and leakage controls for `data/eval/extraction_benchmark_v2.jsonl`.
Scoring usage and results: see `LLM_EXTRACTION_EVALUATION.md`.

## Corpus

Three real sources, all archived under `data/raw_documents/` (immutable):

| document_id | source | kind |
|---|---|---|
| `chen2020_jes_167_080534` | Chen2020 main article fulltext (P3 archive) | paper |
| `chen2020_supplement_s1` | Chen2020 supplementary information, downloaded 2026-11-08 (`JES_167_8_080534_suppdata.pdf`, 9 pp., S1–S6), ingested via pypdf with real PDF page indices | supplement |
| `pybamm_parameter_sets_docs` | PyBaMM stable docs, "Parameter Sets" page, saved 2026-11-08 (25,856 chars) | structured-dataset |

## Item design

20 items = 6 dev + 14 eval. Every gold value carries an optional `qualifier`
with optional `qualifier_alt`, `canonical_value`/`canonical_unit` (for table items
with scale-carrying headers), `uncertainty`, an `expert_note` and, where
relevant, a `conflict_note`; `expect_abstain` items have empty gold.

### Tiers (leakage controls)

- `same-doc-dev` (6): the P3 six-item benchmark (porosity, conductivity,
  rated capacity, isothermal temperature, reaction rates, SEM-abstain). Used
  during development.
- `same-doc-heldout` (8): article material NOT used in P3 development:
  Table V diffusivities (1.48 ± 1.05 / 1.74 ± 4.10 ×1e-15 m2 s-1), positive
  cmax 51765, list-form particle radii (5.22/5.86/1.52 µm), Bruggeman 1.5
  (assumed, theoretical-vs-measured conflict), EIS j0 (0.28 / 0.602 mA cm-2,
  25/60 °C), t+ 0.2594, Table VII active-material volume fractions (66.5/75%).
- `cross-document` (2): supplement-only material: Figure S7 separator
  porosities (48/46/46% vs main-text 47%; gold=48% "calculated", first listed
  regional value — ambiguity deliberate) and the manufacturer data-sheet
  abstain item (Table S1 is a figure; text layer has no values).
- `other-cell-family` (4): leakage-control family on the docs page: MSMR
  reference j0 (5 / 2.7 A.m-2 "assumed"), the 1e6 A.m-2 placeholder (without
  printed unit), the Kokam 5 Ah capacity item, and the SEI-abstain item.
  None of these is LG M50 material: an extraction pipeline that had
  "memorized" Chen-corpus specifics cannot pass these from the Chen framing.

### Family coverage

All eight extraction families are present in eval: volume fractions, solid
diffusivities, electrolyte transport (t+), exchange-current densities, max
concentrations, particle radii, porosity, Bruggeman exponents — plus three
`expect_abstain` items (SEM, datasheet, SEI) and list-form/table-format
stress (columns print units in headers; one unit is never printed; one item
is in % units while a sibling reports fractions).

### Provenance discipline

- Probes are single-line verbatim substrings (two probes were reworded after
  probe-QA found line breaks inside them; the intended windows were
  unchanged).
- Gold quotes against the supplement are guaranteed only against the pypdf
  text layer (real page numbers carried by the store).
- Conflict preservation: `conflict_note` fields link items to the P3
  registry conflicts (tuned-vs-measured diffusivities, cmax, Bruggeman
  override, separator porosity 47% vs 46/46/48%).

## Reproduce

```bash
.venv-ecosystem312/bin/python benchmarks/p4/run_llm_evaluation.py --arm all
```

Arms can be run individually; `--rescore` re-scores frozen raw outputs
without model calls (offline arm is re-derived locally). API keys only via
environment variables; never stored in the repo.
