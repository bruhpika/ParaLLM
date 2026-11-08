# P5 Extraction Reliability (Task 1) & Provenance (Task 4)

Targets the four weakest P4 metrics on the held-out v2 eval split:
**condition completeness 0.0, qualifier 0.600, provenance 0.800, unit 0.880**
(`results/p4/benchmark_v2/summary.md`, `llm_rag` eval). P5 adds prompt-side
discipline and deterministic provenance diagnostics without changing the
extraction schema, validators, or scoring semantics. P3's
`EXTRACTION_PROMPT_SYSTEM` is reused as baseline reference and never modified.

## Prompt changes (`eval/extraction_prompt_p5.py`)

Built with `build_extraction_prompt_p5(memory_permitted=...)`. Key rules:

- **Units as printed (unit 0.880 target):** keep the exact printed unit and scale
  prefixes; do NOT convert (a `33.5 %` stays `33.5` + `%`, not `0.335`
  dimensionless). Positive scale factors in unit strings are scored
  (`14.7` with `10^4 A.m-2` canonicalizes to 1.47e5 A/m²).
- **Conditions (condition completeness 0.0 target):** `temperature` in Kelvin only
  when explicitly stated (stated numeric, "25 °C", "ambient/room temperature");
  never inferred (no isothermal→298.15 without a stated value). `cell_config`
  filled from stated chemistry/format/SOC/state, else `UNRESOLVED`.
- **Qualifier rubric (0.600 target):** measured / calculated (from other
  quantities via a stated expression) / fitted (model fit, Sand-equation fit,
  calibration/tuning) / assumed (convention/theory/adopted value) / unknown only
  when origin is unstated. One per candidate.
- **Provenance (0.800 target):** `source.document_id` exact, `page` from evidence
  header only (never guessed), `locator` from visible label, `quote` is one
  **verbatim contiguous** span copied character-for-character — never splice with
  `...`, never reorder, never summarize (P4 failure modes: ellipsis splices,
  flattened table rows).
- **Conflicts:** one candidate per printed value (method/SOC/temperature/main
  vs supplement), each with its own quote/conditions/qualifier.
- **Abstention/missing:** missing fields → `UNRESOLVED` (rule 6); abstain with
  `[]` when evidence does not support any parameter.

Memory-ablation variant (`memory_permitted=True`, T3 condition 1 only): may use
model knowledge but must set `source.document_id="model_knowledge"`,
`source.quote=null`, `measurement_method="model memory (unverified)"`; no
fabricated provenance.

`extract_with_prompt` returns `(candidates, abstained, raw_content)`; raw model
output is always preserved verbatim (P4 lesson). Parsing/filtering uses the same
`parse_llm_json` + schema validation + `UNRESOLVED`-drop path as P4.

## Provenance diagnostics (`eval/provenance_p5.py`, Task 4)

Deterministic, no LLM. Per candidate: `document_match`, `quote_present`,
`quote_verbatim` (P4 frozen rule: whitespace/unicode-robust contiguous substring
in the archived raw text), `splice_suspected` (`...`/`…`), `page_ok` (claimed
page vs the store segment page that actually contains the quote; `None` when
either side unknown), `locator_visible` (Table/Fig/Eq/Section label present near
the quote or in the document), `paraphrase_warning` (not verbatim but ≥0.80
edit-distance ratio to the best-matching document window), `conditions_ok`.

**Retrieval-strict (3 repeats, v3, all items) mean diagnostics:**
document_match 1.000, quote_present 1.000, quote_verbatim **0.723**,
splice_suspected **0.000**, paraphrase_warning **0.277**, locator_visible 0.496
(of 89 checked), page_ok 0.000 (0 checked — page claims mostly null because the
evidence passage is passed without a page header in the RAG block; the archive
segments do carry real PDF page numbers, so page-checking is feasible when the
model claims a page), conditions_ok 0.272. The ~28% non-verbatim quotes are
paraphrase/near-miss cases (flagged), not ellipsis splices.

**Memory condition:** document_match 0.000, quote_verbatim 0.000 by design
(`model_knowledge`, null quote) — these are **unsupported claims**, surfaced as
non-zero false-extraction/unsupported counts and zero provenance (see T3).
**No-retrieval-strict:** 0 candidates (perfect abstention).

## Weakest-metric movement (P4 → P5, not a direct apples-to-apples claim)

P4 `llm_rag` eval (v2, 14 eval items, single canonical run): condition 0.000,
qualifier 0.588, provenance 0.706, unit 0.941. P5 `retrieval_strict` eval (v3,
29 eval items, 3 repeats, mean±std): condition **0.035±0.001**, qualifier
**0.776±0.019**, provenance **0.953±0.017** (matched-candidate rule), unit
**0.938±0.024**; false extraction **0.000±0.000**. **Condition completeness
remains the dominant weakness** (rule 6 forbids inferring temperature/cell
config the passage does not state; many gold-bearing passages state values but
not a full stated temperature+cell_config). Improvements on the expanded v3
must be read against the changed fixture (more other-cell-family/table items);
per-tier and per-item consistency are in `results/p5/benchmark_v3/`.

## Reproducibility

```bash
.venv-ecosystem312/bin/python -m pytest tests/unit/test_extraction_prompt_p5.py tests/unit/test_provenance_p5.py -q
```