# P4 — LLM extraction evaluation (Parts A/B)

Real-LLM benchmark of the P3 extraction pipeline over benchmark v2
(`data/eval/extraction_benchmark_v2.jsonl`). Code: `src/pybamm_closed_loop/eval/benchmark_p4.py`
(new module; P3's `eval/benchmark.py` is imported, never modified). Artifacts:
`results/p4/benchmark_v2/` (`report_<arm>.json`, `raw_outputs_<arm>.jsonl`,
`summary.md`).

## Setup

- Model: `mimo-v2.6-flash` via the configured OpenAI-compatible endpoint
  (temperature 0, system prompt = P3 `EXTRACTION_PROMPT_SYSTEM`). API key is
  read from the environment at run time and never stored or logged.
- 20 items: 6 dev (the P3 six-item benchmark, re-emitted with gold
  qualifiers) + 14 eval (held-out, 3 tiers — see `LITERATURE_BENCHMARK.md`).
- Arms:
  - `offline` — deterministic non-LLM baseline (P3 `OfflineDeterministicExtractor`).
  - `llm_rag` — LLM with the ±260-char evidence window around each probe.
  - `llm_noretrieval` — same LLM, empty evidence block (ablation).
- Run protocol (frozen before the canonical run): model output is preserved
  verbatim (`raw_outputs_<arm>.jsonl`), schema-validated candidates are scored
  without any manual correction; `--rescore` re-scores frozen raw outputs
  deterministically (no model calls). No test items were used to tune the
  pipeline; the six dev items were available during development.

## Scoring methodology (frozen)

8 metrics (P3 definitions) plus these P4-specific rules, frozen before the
final run:

- **Qualifier classification (new metric)**: gold qualifier from
  {measured, fitted, calculated, assumed}; alternates allowed only where
  fixed in the fixture (`qualifier_alt`). "unknown" never counts.
- **Name grouping**: scorer folds underscores (`electrolyte_volume_fraction`
  → `electrolyte volume fraction`) and adds a scorer-local
  `max_concentration` group (the P3 synonym table has no such family). The
  `symmetry factor` family has no group (deliberate: it is a finding, not a
  fixture bug — see limitations).
- **Unit canonicalization**: whitespace/caret typography (`A m^-2 (m^3
  mol^-1)^1.5` ↔ `A m-2 (m3 mol-1)1.5`) and leading scale factors
  (`1e-15 m2 s-1`, paper-table style `10-15 m2 s-1`) are factored when
  comparing; plain decimals never factor (rule 6, no silent reinterpretation).
- **Provenance**: verbatim quote check against the full raw document,
  unicode-folded and whitespace-collapsed (line breaks inside sentences are
  typography). Ellipsis-spliced ("...") or reordered quotes FAIL.
- **False extraction semantics**: false = evidence-unverified candidate
  (hallucination risk). Evidence-grounded candidates that correspond to no
  gold parameter are counted separately as `excess_extractions`, not as
  false.
- Run-to-run variance was observed despite temperature 0 (two full `llm_rag`
  runs aborted mid-session + one intermediate full run: the intermediate run
  had identification 0.885 / provenance 0.571 / unit 0.762 under the earlier
  scorer, and extracted different item subsets). The canonical recorded run
  is the one in `results/p4/benchmark_v2/`. Numbers below are from that run.

## Results (canonical run, all 20 items)

| metric | offline | llm_noretrieval | llm_rag |
|---|---|---|---|
| parameter identification | 0.654 | 0.000 | 0.962 |
| value extraction | 0.706 | n/a | 0.960 |
| unit accuracy | 1.000 | n/a | 0.880 |
| provenance | 1.000 | n/a | 0.800 |
| condition completeness | 0.000 | n/a | 0.000 |
| qualifier classification | 0.176 | n/a | 0.600 |
| abstention | 1.000 | 1.000 | 1.000 |
| false extraction rate | 0.000 | n/a | 0.062 |

Eval split (14 held-out items): identification 0.944, value 0.941, unit 0.941,
provenance 0.706, qualifier 0.588, conditions 0.000, abstention 1.000,
false-extraction 0.087.

## Findings

1. **Retrieval is genuinely required; the corpus is leakage-safe.** The
   no-retrieval arm abstained on all 20 items (identification 0, abstention
   3/3, zero candidates). The model does not reproduce these corpus-specific
   values without evidence, so the RAG-arm successes measure retrieval+extraction,
   not parameter memorization.
2. **Qualifier semantics is the weakest LLM skill (0.600).** Conservative
   "unknown" dominance on prose items (conductivity averages, rated capacity,
   Kokam capacity) and a measured→calculated relabeling on the EIS j0 value
   (`E12`: the paper computes j0 from measured Rct; both qualifiers are
   defensible; the scorer keeps the fixture's a-priori `measured`). This
   metric needs a human arbiter in future iterations.
3. **Condition completeness is 0 for every arm.** Stated conditions
   (temperature, cell config) are compressed into free-text
   `context`/`measurement_method` instead of the structured
   `temperature`/`cell_config` fields. Fixable by schema-prompting changes;
   not attempted in P4 (P3 prompt untouched).
4. **Provenance (0.800).** Failures: quotes spliced with "..." (`E8`,
   `E4`), flattened multi-line-table quotes (`E15`), and section-boundary
   misattribution (`E4`: a 48% porosity attributed via a Figure S6 quote).
   All are true protocol failures, not scorer artifacts. A quote-verify
   loop (re-ask on failure) is the natural next step.
5. **Units (0.880).** Remaining misses: percent→fraction re-expression
   without re-labeling (`V1`: `0.335, dimensionless` vs gold `33.5 %`), and
   honest `UNRESOLVED` unit flags (`E3`: the docs never print the unit for
   the 1e6 placeholder; the model refuses to infer it, the gold expects
   A.m-2).
6. **Deliberate-ambiguity handling (`E4`).** The model emitted
   `UNRESOLVED` for the separator attribution (Figure S7 lists 48/46/46%)
   while also returning a 48% extraction from a misattributed quote —
   conservative behavior on the gold value itself, and counted as excess/right
   split accordingly.
7. **Deterministic baseline is ontology-bound (id 0.654).** Its regex
   patterns mislabel unseen value types (E9: five values mislabeled as
   `active material volume fraction`), demonstrating that the distribution
   shift in the P4 corpus exceeds the pattern baseline's coverage — the
   metric anchoring point, not a competitor.

## Limitations

- Single provider, single canonical run; run-level variance documented above.
- The `'symmetry factor'` gold family cannot group-match anything (no synonym
  group); after the canonical run this is recorded as a fixture limitation
  (`E3` contributes one identification miss) rather than a post-hoc scorer
  change.
- E12's qualifier ambiguity (measured vs calculated) is reported as a miss;
  changing the gold after seeing outputs would be circular.
- The dev split was used to tune P3's prompt/pipeline; eval numbers carry up
  to dev-usage bias — that is precisely why the dev/eval split and the
  held-out tiers exist.
