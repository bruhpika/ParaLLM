# Literature Ingestion and Retrieval (P3 / Parts B + C)

Code: `src/pybamm_closed_loop/literature/` (`ingest.py`, `index.py`,
`retrieval.py`). Raw documents: `data/raw_documents/` (immutable);
ingested store + segment index: `data/literature_store/`.

## 1. Ingestion pipeline (Part B)

`DocumentStore` ingests research papers, supplementary information, PDFs
and structured datasets:

| Input | Method | Provenance carried by every segment |
|---|---|---|
| plain text / HTML-derived text | `ingest_text` | `document_id`, char offsets, `page=None` |
| PDF (via pypdf) | `ingest_pdf` | `document_id`, char offsets, `page` = 1-based **PDF** page index |
| structured datasets | `ingest_text` of metadata + `datasets/pyprobe_link.py` for observations | dataset id + column/row facts |

Guarantees:

1. **Immutable raw store**: re-ingesting the same `document_id` with
   different content raises `ValueError` (rule: never overwrite source
   documents). Identical content is idempotent. Content is hashed
   (sha256) in `documents.json`.
2. **No fabricated locations**: page numbers exist only where a real page
   structure exists (PDF); text documents carry `page=None` and are located
   by char offsets and heading/anchor strings only. Where the HTML-to-text
   conversion of the Chen2020 article lost table labels, records cite exact
   caption text instead of invented numbers (documented in
   `registry/sources.py::ANCHOR_NOTE_UNNUMBERED_TABLES`).
3. **Statement-level evidence**: `Segment` objects (5-level id
   `doc#segNNNNN`) keep char offsets into the raw text, the nearest heading
   or table/figure caption, and the page when known. Extraction quotes are
   always substrings of a segment.

The Chen2020 article (verified 2026-11-04, CC BY-NC-ND 4.0,
DOI 10.1149/1945-7111/ab9050) is archived at
`data/raw_documents/chen2020_jes_167_080534/` and is the reference document
for the seeded registry.

## 2. Retrieval (Part C)

`index.py` provides a deterministic BM25 index (k1=1.5, b=0.75) over all
segments; `retrieval.py` assembles RAG contexts from facets:

- `RetrievalFacets`: parameter names + synonyms, electrode materials, cell
  chemistry, cell format, experimental conditions, measurement techniques.
- `expand_query` expands the query with documented alias groups
  (`SYNONYMS` in `index.py`): parameter names/synonyms (e.g. diffusivity =
  diffusion coefficient / Ds), materials (NMC811, graphite-SiOx), cell
  format (LG M50 / 21700), conditions (temperature, C-rate), techniques
  (GITT, EIS, four-point probe, SEM, ICP). When a group is triggered all of
  its aliases are added.
- `build_rag_context` returns the top-k segments with scores and provenance.

## 3. Evidence-only extraction contract (Part C requirement)

`RAGContext.to_prompt_block()` emits ONLY the retrieved passages plus the
rule: *"extract ONLY statements supported by the evidence above; otherwise
return UNRESOLVED for the missing fields."* The extraction schema and the
deterministic validation layer enforce this (a quote that cannot be found
in the archived source is a fatal `REJECTED` finding — see
`docs/SCIENTIFIC_VALIDATION.md`).

## 4. What is intentionally NOT implemented

- No full-text PDF figure/table reconstruction (values are read from
  printed tables by humans/LLM with the caption as location).
- No citation-graph expansion across papers (single-corpus retrieval for
  now; multi-document corpora are supported structurally).
- No embeddings/vector store: BM25 + alias expansion is deterministic,
  dependency-light and adequate for the P3 corpus scale.

## 5. Tests

`tests/unit/test_literature_ingest.py`: offset integrity, immutability,
PDF page provenance (hand-built 2-page PDF), BM25 ranking, synonym
expansion, RAG context assembly. `tests/integration/test_p3_pipeline.py`
runs the full pipeline on the real archive.
