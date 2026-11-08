# P4 benchmark v2 - cross-arm comparison

items: 20 (split filter: all); generated 2026-11-08T05:43:20.111072+00:00

- arm `llm_noretrieval`: model=mimo-v2.6-flash
- arm `llm_rag`: model=mimo-v2.6-flash
- arm `offline`: model=deterministic (no LLM)

| metric | llm_noretrieval | llm_rag | offline |
|---|---|---|---|
| abstention_accuracy | 1.000 | 1.000 | 1.000 |
| condition_completeness | n/a | 0.000 | 0.000 |
| false_extraction_rate | n/a | 0.062 | 0.000 |
| parameter_identification_accuracy | 0.000 | 0.962 | 0.654 |
| provenance_accuracy | n/a | 0.800 | 1.000 |
| qualifier_classification_accuracy | n/a | 0.600 | 0.176 |
| unit_accuracy | n/a | 0.880 | 1.000 |
| value_extraction_accuracy | n/a | 0.960 | 0.706 |

## dev split

| metric | llm_noretrieval | llm_rag | offline |
|---|---|---|---|
| abstention_accuracy | 1.000 | 1.000 | 1.000 |
| condition_completeness | n/a | 0.000 | 0.000 |
| false_extraction_rate | n/a | 0.000 | 0.000 |
| parameter_identification_accuracy | 0.000 | 1.000 | 1.000 |
| provenance_accuracy | n/a | 1.000 | 1.000 |
| qualifier_classification_accuracy | n/a | 0.625 | 0.125 |
| unit_accuracy | n/a | 0.750 | 1.000 |
| value_extraction_accuracy | n/a | 1.000 | 1.000 |

## eval split

| metric | llm_noretrieval | llm_rag | offline |
|---|---|---|---|
| abstention_accuracy | 1.000 | 1.000 | 1.000 |
| condition_completeness | n/a | 0.000 | 0.000 |
| false_extraction_rate | n/a | 0.087 | 0.000 |
| parameter_identification_accuracy | 0.000 | 0.944 | 0.500 |
| provenance_accuracy | n/a | 0.706 | 1.000 |
| qualifier_classification_accuracy | n/a | 0.588 | 0.222 |
| unit_accuracy | n/a | 0.941 | 1.000 |
| value_extraction_accuracy | n/a | 0.941 | 0.444 |
