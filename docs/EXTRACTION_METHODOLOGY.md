# Extraction Methodology (P3 / Parts D + H)

Code: `src/pybamm_closed_loop/literature/extraction.py`,
`src/pybamm_closed_loop/eval/benchmark.py`.
Runner: `benchmarks/p3/run_extraction_benchmark.py`.

## 1. Structured extraction output (Part D)

Every extraction is a JSON object with exactly these keys (validated by
`registry.model.validate_extraction_schema`):

| Key | Content |
|---|---|
| `parameter_name` | parameter name as written in the source |
| `value`, `unit` | numeric value + unit token as printed |
| `definition` | physical definition (or `UNRESOLVED`) |
| `material` | electrode/electrolyte material |
| `temperature` | Kelvin, or null |
| `cell_config` | cell configuration |
| `measurement_method` | how the quantity was obtained |
| `qualifier` | **one of: measured / fitted / calculated / assumed / unknown** |
| `context` | supporting context |
| `source` | `document_id` + `page` (or null) + `locator` + verbatim `quote` |
| `reported_uncertainty` | float or null |

Rules enforced (schema + validation + review):

1. The extractor sees **only** the RAG context passages (rule in the prompt
   block).
2. Missing evidence -> the field is `UNRESOLVED`/null; the extractor
   abstains rather than inventing values, pages, table numbers or citations.
3. **The `qualifier` field separates measured, fitted, calculated and
   assumed quantities.** A fitted/calibrated literature parameter (e.g. the
   Chen2020 tuned diffusivities) must never be recorded as a direct
   experimental measurement — the validation layer flags
   `qualifier="fitted"` with an explicit note and the registry stores such
   values with status `CALIBRATED`.
4. Extraction output is a **proposal** (`ValueCandidate`); only
   deterministic validation + explicit review states can move it into the
   registry (rule 10).

## 2. Providers

| Provider | Purpose | Interface |
|---|---|---|
| `OpenAICompatibleClient` | the general-purpose LLM baseline; any OpenAI-compatible endpoint (`PYCL_LLM_BASE_URL`, `PYCL_LLM_API_KEY`, `PYCL_LLM_MODEL`) | chat completions, temperature 0, JSON-array output |
| `OfflineDeterministicExtractor` | CI-safe non-LLM baseline; numeric-unit pattern mining over retrieved passages with method-keyword qualifiers | `extract_from_segments(segments, target_names)` |

The offline extractor is clearly labelled `proposed_by="deterministic"`; it
is a software baseline, not an LLM result. It resolves parameter names from
the retrieval facets when an alias group in the passage matches a target
name (RAG-consistent labelling), handles `x*10^-n` scientific notation, and
abstains when no numeric evidence is present.

## 3. Extraction benchmark (Part H)

Fixture: `data/eval/extraction_benchmark_v1.jsonl` — 6 expert-reviewed
items over the archived Chen2020 text (passage probes are verbatim archive
substrings; gold values are the printed values, canonicalised at scoring
time by the same `registry/units.py` used everywhere else):

| Item | Tests | Gold |
|---|---|---|
| I1 porosity | % -> fraction conversion, two values one passage | pos 33.5 %, neg 25 % |
| I2 conductivity | S m-1 values with method context | 0.18 / 215 S m-1 |
| I3 rated capacity | manufacturer-cited value | 5 A.h |
| I4 isothermal temperature | assumption qualifier | 298.15 K |
| I5 reaction rates | `x*10^-n` notation + compound unit | 3.42e-6 / 6.48e-7 A m-2 (m3 mol-1)^1.5 |
| I6 abstention | no numeric evidence for the query | (none) |

Metrics (all computed by `eval/benchmark.py`):

1. **parameter identification accuracy** (gold matched by alias group)
2. **value extraction accuracy** (canonical units, rel tol 1e-6)
3. **unit correctness** (canonical equality or dot-prefix, documented rule)
4. **condition completeness** (temperature + cell_config resolved)
5. **provenance accuracy** (correct document + quote verifiable verbatim in
   the archive)
6. **false extraction rate** (extractions matching no gold parameter group)
7. **abstention accuracy** (correct abstentions on expect-abstain items)

### Measured baseline (offline deterministic provider, 2026-11-06)

| metric | value |
|---|---|
| parameter_identification_accuracy | 1.000 |
| value_extraction_accuracy | 1.000 |
| unit_correctness | 1.000 |
| condition_completeness | 0.000 |
| provenance_accuracy | 1.000 |
| false_extraction_rate | 0.000 |
| abstention_accuracy | 1.000 |

Artifacts: `results/p3/extraction_benchmark_v1_offline/`.
Honest reading: the pattern baseline is perfect on identification/value/
unit/provenance/abstention for this controlled corpus but **cannot produce
experimental conditions at all** (condition_completeness = 0) — exactly the
axis where an LLM + retrieval is expected to win. The corpus is small and
same-document; numbers will move on broader corpora.

### LLM baseline runbook (not run in P3 — no API key in this environment)

```bash
export PYCL_LLM_BASE_URL=https://api.openai.com/v1   # or any compatible endpoint
export PYCL_LLM_API_KEY=...                           # never stored in this repo
export PYCL_LLM_MODEL=...
.venv-ecosystem312/bin/python benchmarks/p3/run_extraction_benchmark.py --provider llm
```

Writes `results/p3/extraction_benchmark_v1_llm/`. The same 7 metrics make
the LLM baseline directly comparable with the offline one. Fine-tuning is
explicitly out of scope for P3.

## 4. Benchmark limitations

- 6 items, one document, controlled passages (retrieval recall is validated
  separately in unit tests, not conflated into these metrics).
- Gold qualifier matching is intentionally excluded from the 7 metrics
  (fixture notes record the expected qualifiers; review-rubric tests cover
  the fitted-vs-measured distinction).
- Unit metric uses a documented dot-prefix rule for the compound
  reaction-rate unit (`A.m-2` counts as correct against
  `A.m-2.(m3.mol-1)^1.5`).
