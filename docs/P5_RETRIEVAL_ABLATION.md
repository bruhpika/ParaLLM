# P5 Retrieval / Knowledge Ablation (Task 3)

**Benchmark v3 only** (`data/eval/extraction_benchmark_v3.jsonl`, 37 items, 8 dev /
29 eval) — no P4/v2 aggregates are mixed. Model: `mimo-v2.6-flash` via the
configured OpenAI-compatible endpoint, temperature 0. Same task, schema, and
frozen P4 scoring rubric across conditions. **3 repeat runs per LLM condition**
(run-to-run variance observed at temperature 0); raw model outputs preserved
verbatim per repeat.

Raw outputs + reports: `results/p5/benchmark_v3/` (`raw_outputs_<cond>_r<k>.jsonl`,
`report_<cond>_r<k>.json`, `aggregate_<cond>.json`, `consistency_<cond>.json`,
`summary.md`). Two retrieval_strict repeats hit transient transport failures
(`http.client.IncompleteRead`, `TimeoutError`/DNS `URLError`); originals
preserved (`raw_outputs_retrieval_strict_r0.partial_pre_incompleteread.jsonl`),
runs resumed with an expanded retry wrapper (`RobustLLMClient`, T3 reliability
hardened in `eval/benchmark_p5.py`; `benchmarks/p5/run_ablation.py` uses it).
No prompt/scoring/model/fixture change between repeats.

## Conditions

| condition | evidence | knowledge | prompt |
|---|---|---|---|
| `retrieval_strict` | ±260-char archive passage | no (evidence only) | P5 strict |
| `no_retrieval_strict` | none | no | P5 strict → must abstain |
| `no_retrieval_memory` | none | **permitted** (marked) | P5 memory: `document_id=model_knowledge`, `quote=null`, method `model memory (unverified)` |
| `offline` (reference) | passage | n/a | deterministic extractor |

## Aggregate metrics (all 37 items, mean ± pop std over repeats)

| metric | retrieval_strict (n=3) | no_retrieval_memory (n=3) | no_retrieval_strict (n=3) | offline (n=1) |
|---|---:|---:|---:|---:|
| parameter identification | **0.718 ± 0.009** | 0.378 ± 0.086 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| value extraction (matched) | **0.946 ± 0.022** | 0.272 ± 0.083 | n/a | 0.500 ± 0.000 |
| unit accuracy (matched) | **0.839 ± 0.002** | 0.720 ± 0.112 | n/a | 0.769 ± 0.000 |
| provenance (matched) | **0.928 ± 0.026** | 0.000 ± 0.000 | n/a | 1.000 ± 0.000 |
| condition completeness (matched) | 0.116 ± 0.011 | 0.483 ± 0.062 | n/a | 0.000 ± 0.000 |
| qualifier accuracy (matched) | **0.741 ± 0.033** | 0.497 ± 0.045 | n/a | 0.115 ± 0.000 |
| abstention accuracy | **1.000 ± 0.000** | 0.333 ± 0.136 | **1.000 ± 0.000** | 1.000 ± 0.000 |
| false extraction rate | **0.000 ± 0.000** | 0.275 ± 0.042 | n/a | 0.000 ± 0.000 |

Held-out **eval split** (29 items), retrieval_strict: id 0.708±0.012, value
0.953±0.017, provenance 0.953±0.017 (matched), condition 0.035±0.001, qualifier
0.776±0.019, false 0.000±0.000.

## Interpretation (evidence vs unsupported claims)

- **Retrieval is required for grounded extraction on this benchmark.**
  `no_retrieval_strict` abstains on every item across all 3 repeats (leakage-safe
  behavior reproduced at v3 scale). `retrieval_strict` achieves high value/unit/
  provenance on matched candidates with **zero false extractions** and perfect
  abstention.
- **Memory-permitted without evidence is not a substitute for provenance.**
  `no_retrieval_memory` produces candidates (id 0.378, higher variance) but with
  **0.000 provenance, 0.275 false-extraction rate, and 0.333 abstention accuracy**
  — it fails to abstain on abstention items and emits unverifiable/unsupported
  claims (mean ~8.8 unsupported candidates total-equivalent per run diagnostics;
  `unsupported_mean` per item in `consistency_no_retrieval_memory.json`). Its
  higher condition-completeness (0.483) reflects the model freely filling stated
  conditions from memory, not evidence-grounded condition capture.
- **Condition completeness is the main residual weakness under retrieval** (0.116
  all / 0.035 eval): many passages state parameter values without explicitly
  stating temperature + cell_config together, and rule 6 forbids inference.

## Per-item consistency (retrieval_strict, 3 repeats)

15 metric-variances observed across 13 items; most are qualifier/condition/unit
borderline cases. Consistently weak items: `E12-j0-pos-eis` (id 0.00, Rct-vs-j0
payload confusion, known P4), `P5-L3-exchange-current-table` and
`P5-L4-solid-diffusivity-table`/`P5-L6-electrolyte-diffusivity-table` (table
scale/header parsing), `V5-reaction-rates` (id 0.00), `E4-supp-sep-porosity`
(id 0.33 mean). Consistently correct abstention on all 6 abstention items.
Full table: `results/p5/benchmark_v3/consistency_retrieval_strict.json`.

## Reproducibility

```bash
# (requires PYCL_LLM_API_KEY/BASE_URL/MODEL in env; key never written)
.venv-ecosystem312/bin/python benchmarks/p5/run_ablation.py --condition all --repeats 3
.venv-ecosystem312/bin/python benchmarks/p5/compute_consistency.py
```