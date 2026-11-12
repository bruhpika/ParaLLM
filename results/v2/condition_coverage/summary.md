# V2.5 — condition coverage of the evidence block (deterministic)

items: `data/eval/extraction_benchmark_v3.jsonl` (n=37); compact ±260 chars vs condition-aware ±900 chars (+ document-level setup sentences)

| condition class | compact (v0.1) | expanded window | + document conditions | either |
|---|---:|---:|---:|---:|
| temperature | 0.108 | 0.162 | 0.838 | 0.838 |
| soc | 0.108 | 0.216 | 0.757 | 0.757 |
| c_rate | 0.054 | 0.081 | 0.432 | 0.432 |
| cell | 0.081 | 0.270 | 0.514 | 0.514 |
| chemistry | 0.243 | 0.595 | 0.838 | 0.838 |
| method | 0.649 | 0.946 | 1.000 | 1.000 |

Evidence-side metric only: it measures how much condition information the retrieval layer supplies, not whether the extractor uses it.
