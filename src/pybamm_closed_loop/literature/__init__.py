"""Literature ingestion, retrieval and extraction layer (P3, Parts B-D)."""

from __future__ import annotations

__all__ = [
    "DocumentStore",
    "DocumentRecord",
    "Segment",
    "BM25Index",
    "RetrievalFacets",
    "RAGContext",
    "ExtractionBatch",
    "ExtractionCandidate",
]


def __getattr__(name: str):
    if name in ("DocumentStore", "DocumentRecord", "Segment"):
        from . import ingest

        return getattr(ingest, name)
    if name == "BM25Index":
        from . import index

        return index.BM25Index
    if name in ("RetrievalFacets", "RAGContext"):
        from . import retrieval

        return getattr(retrieval, name)
    if name in ("ExtractionBatch", "ExtractionCandidate"):
        from . import extraction

        return getattr(extraction, name)
    raise AttributeError(name)
