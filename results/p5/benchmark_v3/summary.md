# P5 benchmark v3 - retrieval/knowledge ablation

items: `data/eval/extraction_benchmark_v3.jsonl`; repeats per condition (LLM): 3; generated 2026-11-08T11:58:20.377524+00:00

Means +/- population std over repeats. v3 only (P4 not mixed).

- `no_retrieval_memory`: model=deterministic (no LLM) repeats=3
- `no_retrieval_strict`: model=deterministic (no LLM) repeats=3
- `offline`: model=deterministic (no LLM) repeats=1
- `retrieval_strict`: model=mimo-v2.6-flash repeats=3

## all items (mean +/- std)

| metric | no_retrieval_memory | no_retrieval_strict | offline | retrieval_strict |
|---|---|---|---|---|
| abstention_accuracy | 0.333 +/- 0.136 | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 1.000 +/- 0.000 |
| condition_completeness | 0.483 +/- 0.062 | n/a | 0.000 +/- 0.000 | 0.116 +/- 0.011 |
| false_extraction_rate | 0.275 +/- 0.042 | n/a | 0.000 +/- 0.000 | 0.000 +/- 0.000 |
| parameter_identification_accuracy | 0.378 +/- 0.086 | 0.000 +/- 0.000 | 0.500 +/- 0.000 | 0.718 +/- 0.009 |
| provenance_accuracy | 0.000 +/- 0.000 | n/a | 1.000 +/- 0.000 | 0.928 +/- 0.026 |
| qualifier_classification_accuracy | 0.497 +/- 0.045 | n/a | 0.115 +/- 0.000 | 0.741 +/- 0.033 |
| unit_accuracy | 0.720 +/- 0.112 | n/a | 0.769 +/- 0.000 | 0.839 +/- 0.002 |
| value_extraction_accuracy | 0.272 +/- 0.083 | n/a | 0.500 +/- 0.000 | 0.946 +/- 0.022 |

## eval split (mean +/- std)

| metric | no_retrieval_memory | no_retrieval_strict | offline | retrieval_strict |
|---|---|---|---|---|
| abstention_accuracy | 0.267 +/- 0.094 | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 1.000 +/- 0.000 |
| condition_completeness | 0.339 +/- 0.043 | n/a | 0.000 +/- 0.000 | 0.035 +/- 0.001 |
| false_extraction_rate | 0.315 +/- 0.057 | n/a | 0.000 +/- 0.000 | 0.000 +/- 0.000 |
| parameter_identification_accuracy | 0.392 +/- 0.123 | 0.000 +/- 0.000 | 0.400 +/- 0.000 | 0.708 +/- 0.012 |
| provenance_accuracy | 0.000 +/- 0.000 | n/a | 1.000 +/- 0.000 | 0.929 +/- 0.001 |
| qualifier_classification_accuracy | 0.503 +/- 0.078 | n/a | 0.125 +/- 0.000 | 0.776 +/- 0.019 |
| unit_accuracy | 0.766 +/- 0.071 | n/a | 0.625 +/- 0.000 | 0.812 +/- 0.018 |
| value_extraction_accuracy | 0.197 +/- 0.085 | n/a | 0.250 +/- 0.000 | 0.953 +/- 0.017 |

## dev split (mean +/- std)

| metric | no_retrieval_memory | no_retrieval_strict | offline | retrieval_strict |
|---|---|---|---|---|
| abstention_accuracy | 0.667 +/- 0.471 | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 1.000 +/- 0.000 |
| condition_completeness | 1.000 +/- 0.000 | n/a | 0.000 +/- 0.000 | 0.370 +/- 0.052 |
| false_extraction_rate | 0.056 +/- 0.079 | n/a | 0.000 +/- 0.000 | 0.000 +/- 0.000 |
| parameter_identification_accuracy | 0.333 +/- 0.068 | 0.000 +/- 0.000 | 0.833 +/- 0.000 | 0.750 +/- 0.000 |
| provenance_accuracy | 0.000 +/- 0.000 | n/a | 1.000 +/- 0.000 | 0.926 +/- 0.105 |
| qualifier_classification_accuracy | 0.522 +/- 0.110 | n/a | 0.100 +/- 0.000 | 0.630 +/- 0.105 |
| unit_accuracy | 0.572 +/- 0.234 | n/a | 1.000 +/- 0.000 | 0.926 +/- 0.052 |
| value_extraction_accuracy | 0.589 +/- 0.068 | n/a | 0.900 +/- 0.000 | 0.926 +/- 0.052 |

## T4 provenance diagnostics (mean)

| check | no_retrieval_memory | no_retrieval_strict | offline | retrieval_strict |
|---|---|---|---|---|
| conditions_ok_rate | 0.372 | n/a | 0.000 | 0.272 |
| document_match_rate | 0.000 | n/a | 1.000 | 1.000 |
| locator_visible_rate | 0.000 | n/a | 0.000 | 0.496 |
| page_ok_rate | 0.000 | n/a | 0.000 | 0.000 |
| paraphrase_warning_rate | 0.000 | n/a | 0.000 | 0.277 |
| quote_present_rate | 0.000 | n/a | 1.000 | 1.000 |
| quote_verbatim_rate | 0.000 | n/a | 1.000 | 0.723 |
| splice_rate | 0.000 | n/a | 0.000 | 0.000 |
