"""Literature document ingestion (P3, Part B).

Ingests research papers, supplementary information, PDFs and structured
datasets into an immutable raw store with per-segment provenance
(document id, page, char offsets, heading context). No page numbers,
table numbers or citations are ever fabricated: PDF page numbers are the
PDF's own 1-based page indices; text documents carry page=None and are
located by char offsets and headings only.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable


_DOCUMENT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def validate_document_id(document_id: str) -> None:
    """Reject ids that could escape the store root when used as filenames.

    Hardening: ``document_id`` is interpolated into paths under the store
    root (``raw/<id>.txt``, ``segments/<id>.json``); ids containing path
    separators (or consisting only of dots) would traverse. Only POSIX
    single-segment, non-hidden names built from letters/digits/._- (like
    ``chen2020_jes_167_080534``) are accepted.
    """
    if not isinstance(document_id, str) or not _DOCUMENT_ID_RE.fullmatch(document_id):
        raise ValueError(
            f"invalid document id {document_id!r}: must be a single plain "
            "file name (letters, digits, and/or . _ -; no path separators, "
            "not starting with a dot)"
        )


@dataclass
class DocumentRecord:
    document_id: str
    kind: str  # "paper" | "supplement" | "pdf" | "structured-dataset" | "html"
    source_url: str | None
    doi_or_url: str | None
    title: str | None
    retrieved: str
    content_sha256: str
    page_structure: bool
    raw_path: str
    n_segments: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Segment:
    segment_id: str
    document_id: str
    char_start: int
    char_end: int
    page: int | None
    heading: str | None
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DocumentStore:
    """Immutable raw-document store with a segment index."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.segments_dir = self.root / "segments"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self._docs: dict[str, DocumentRecord] = {}
        self._segments: dict[str, list[Segment]] = {}
        self._load()

    # -- persistence ---------------------------------------------------
    def _manifest_path(self) -> Path:
        return self.root / "documents.json"

    def _load(self) -> None:
        if not self._manifest_path().exists():
            return
        for d in json.loads(self._manifest_path().read_text()):
            try:
                rec = DocumentRecord(**d)
            except TypeError as exc:
                raise ValueError(
                    f"corrupt document manifest entry (unexpected fields): {d!r}"
                ) from exc
            validate_document_id(rec.document_id)
            self._docs[rec.document_id] = rec
            seg_path = self.segments_dir / f"{rec.document_id}.json"
            if seg_path.exists():
                self._segments[rec.document_id] = [
                    Segment(**s) for s in json.loads(seg_path.read_text())
                ]

    def _flush(self) -> None:
        tmp = self._manifest_path().with_suffix(".tmp")
        tmp.write_text(
            json.dumps([asdict(d) for d in self._docs.values()], indent=2, sort_keys=True)
        )
        tmp.replace(self._manifest_path())

    # -- access --------------------------------------------------------
    def documents(self) -> list[DocumentRecord]:
        return list(self._docs.values())

    def get_document(self, document_id: str) -> DocumentRecord:
        return self._docs[document_id]

    def segments(self, document_id: str | None = None) -> list[Segment]:
        if document_id is not None:
            return self._segments.get(document_id, [])
        out: list[Segment] = []
        for doc_id in self._segments:
            out.extend(self._segments[doc_id])
        return out

    # -- ingestion -----------------------------------------------------
    def ingest_text(
        self,
        document_id: str,
        text: str,
        kind: str = "paper",
        source_url: str | None = None,
        doi_or_url: str | None = None,
        title: str | None = None,
        retrieved: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> DocumentRecord:
        """Ingest a plain-text/HTML-derived document. Immutable: re-ingesting
        the same id is allowed only with identical content."""
        return self._ingest(
            document_id=document_id,
            pages=[(None, text)],
            kind=kind,
            source_url=source_url,
            doi_or_url=doi_or_url,
            title=title,
            retrieved=retrieved,
            meta=meta,
        )

    def ingest_pdf(
        self,
        document_id: str,
        pdf_path: str | Path,
        kind: str = "pdf",
        source_url: str | None = None,
        doi_or_url: str | None = None,
        title: str | None = None,
        retrieved: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> DocumentRecord:
        """Ingest a PDF. Page numbers recorded in segments are 1-based PDF
        page indices (printed pagination may differ; noted in meta)."""
        try:
            import pypdf
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pypdf is required for PDF ingestion (pip install pypdf)"
            ) from exc
        reader = pypdf.PdfReader(str(pdf_path))
        pages: list[tuple[int | None, str]] = [
            (i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)
        ]
        meta = dict(meta or {})
        meta.setdefault(
            "page_numbering",
            "segments carry 1-based PDF page indices; printed pagination may differ",
        )
        return self._ingest(
            document_id=document_id,
            pages=pages,
            kind=kind,
            source_url=source_url,
            doi_or_url=doi_or_url,
            title=title,
            retrieved=retrieved,
            meta=meta,
        )

    def _ingest(
        self,
        document_id: str,
        pages: list[tuple[int | None, str]],
        kind: str,
        source_url: str | None,
        doi_or_url: str | None,
        title: str | None,
        retrieved: str | None,
        meta: dict[str, Any] | None,
    ) -> DocumentRecord:
        validate_document_id(document_id)
        full_text = "\n".join(t for _, t in pages)
        sha = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        if document_id in self._docs:
            existing = self._docs[document_id]
            if existing.content_sha256 != sha:
                raise ValueError(
                    f"document {document_id!r} already exists with different "
                    "content; raw documents are immutable (rule: never "
                    "overwrite source documents)"
                )
            return existing
        raw_path = self.raw_dir / f"{document_id}.txt"
        raw_path.write_text(full_text)
        segments = self._segment(document_id, pages)
        self._docs[document_id] = DocumentRecord(
            document_id=document_id,
            kind=kind,
            source_url=source_url,
            doi_or_url=doi_or_url,
            title=title,
            retrieved=retrieved or date.today().isoformat(),
            content_sha256=sha,
            page_structure=any(p is not None for p, _ in pages),
            raw_path=str(raw_path),
            n_segments=len(segments),
            meta=meta or {},
        )
        self._segments[document_id] = segments
        (self.segments_dir / f"{document_id}.json").write_text(
            json.dumps([s.to_dict() for s in segments], indent=1, sort_keys=True)
        )
        self._flush()
        return self._docs[document_id]

    # -- segmentation --------------------------------------------------
    @staticmethod
    def _segment(document_id: str, pages: Iterable[tuple[int | None, str]]) -> list[Segment]:
        segments: list[Segment] = []
        offset = 0
        heading: str | None = None
        idx = 0
        for page_no, text in pages:
            for start, end, chunk, new_heading in _paragraph_spans(text, offset, heading):
                if new_heading is not None:
                    heading = new_heading
                if not chunk.strip():
                    continue
                segments.append(
                    Segment(
                        segment_id=f"{document_id}#seg{idx:05d}",
                        document_id=document_id,
                        char_start=start,
                        char_end=end,
                        page=page_no,
                        heading=heading,
                        text=chunk,
                    )
                )
                idx += 1
            offset += len(text) + 1  # +1 for the joining newline
        return segments


_HEADING_RE = re.compile(r"^(Table\s+[IVXLC]+\.|Figure\s+\d+\.|[A-Z][^\n]{0,110})$")


def _paragraph_spans(
    text: str, offset: int, heading: str | None
) -> list[tuple[int, int, str, str | None]]:
    """Split text into paragraphs with absolute char spans; track headings.

    A line is treated as a heading when it is short, does not end with
    sentence punctuation and matches a table/figure caption pattern or a
    short title-like line. Returns (start, end, chunk, new_heading).
    """
    spans: list[tuple[int, int, str, str | None]] = []
    pos = 0
    for m in re.finditer(r"\n\s*\n|\r\n\r\n", text):
        chunk = text[pos : m.start()]
        spans.append((offset + pos, offset + m.start(), chunk, None))
        pos = m.end()
    tail = text[pos:]
    spans.append((offset + pos, offset + len(text), tail, None))
    out: list[tuple[int, int, str, str | None]] = []
    current_heading = heading
    for start, end, chunk, _ in spans:
        new_heading = current_heading
        lines = chunk.strip().splitlines()
        if lines:
            first = lines[0].strip()
            if _HEADING_RE.match(first) and first.endswith((".", ":", ".")):
                new_heading = first
        out.append((start, end, chunk, new_heading))
        current_heading = new_heading
    return out
