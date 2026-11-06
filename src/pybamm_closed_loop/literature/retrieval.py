"""Facet-driven retrieval and RAG context assembly (P3, Part C).

The language model may only extract evidence from the passages returned
here: ``build_rag_context`` produces the complete, provenance-carrying
context that is handed to any extractor. If no passage supports a claim,
the extractor must return UNRESOLVED (enforced by the extraction schema +
validation, never trusted to the model).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .index import BM25Index
from .ingest import Segment


@dataclass
class RetrievalFacets:
    parameter_names: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    cell_chemistry: list[str] = field(default_factory=list)
    cell_format: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    techniques: list[str] = field(default_factory=list)

    def query_text(self) -> str:
        parts: list[str] = []
        parts.extend(self.parameter_names)
        parts.extend(self.synonyms)
        parts.extend(self.materials)
        parts.extend(self.cell_chemistry)
        parts.extend(self.cell_format)
        for k, v in self.conditions.items():
            parts.append(f"{k} {v}")
        parts.extend(self.techniques)
        return " ".join(parts)


@dataclass
class RetrievedSegment:
    segment_id: str
    document_id: str
    page: int | None
    heading: str | None
    text: str
    score: float

    @classmethod
    def from_segment(cls, seg: Segment, score: float) -> "RetrievedSegment":
        return cls(
            segment_id=seg.segment_id,
            document_id=seg.document_id,
            page=seg.page,
            heading=seg.heading,
            text=seg.text,
            score=score,
        )


@dataclass
class RAGContext:
    query: str
    facets: dict[str, Any]
    segments: list[RetrievedSegment]
    retrieved_from: list[str]  # document ids

    def to_prompt_block(self) -> str:
        """Text block handed to the LLM: ONLY these passages are evidence."""
        lines = [f"QUERY: {self.query}", ""]
        for i, seg in enumerate(self.segments):
            loc = f"page {seg.page}" if seg.page is not None else "no page structure"
            lines.append(f"[EVIDENCE {i + 1}] document={seg.document_id} {loc} heading={seg.heading!r}")
            lines.append(seg.text.strip())
            lines.append("")
        lines.append(
            "RULE: extract ONLY statements supported by the evidence above; "
            "otherwise return UNRESOLVED for the missing fields."
        )
        return "\n".join(lines)


def build_rag_context(
    facets: RetrievalFacets,
    index: BM25Index,
    k: int = 8,
) -> RAGContext:
    hits = index.search(facets.query_text(), k=k)
    segments = [RetrievedSegment.from_segment(seg, score) for seg, score in hits]
    return RAGContext(
        query=facets.query_text(),
        facets=asdict(facets),
        segments=segments,
        retrieved_from=sorted({s.document_id for s in segments}),
    )
