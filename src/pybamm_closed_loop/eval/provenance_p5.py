"""P5 Task 4: deterministic provenance verification for extraction candidates.

The P4 scorer already checks one thing: whether a candidate's quote appears
verbatim in the archived document (whitespace/unicode robust). P5 adds the
remaining provenance dimensions the milestone asks for, WITHOUT any LLM:

  document_match    source.document_id equals the item's document
  quote_verbatim    contiguous verbatim substring of the archived raw text
  splice_suspected  quote contains an ellipsis marker ("...", "…") - the P4
                    failure mode where two fragments are stitched together
  page_ok           claimed page equals the store segment page that actually
                    contains the quote (None when either side is unknown)
  locator_visible   the claimed locator's label (e.g. "Table 3", "Figure S1",
                    "Eq. (18)", "Section 4.1.2") is present in the raw text
                    near the quote (or anywhere when no quote is verifiable)
  paraphrase_warning  quote is NOT verbatim but is >= 0.80 similar to the
                    best-matching document window (nearest-edit distance
                    ratio) - i.e. a near-miss paraphrase, flagged rather
                    than silently accepted
  conditions_ok     temperature is a number AND cell_config is filled (the
                    frozen P4 condition-completeness rule)

Nothing here redefines the 8 P4 benchmark metrics; these are diagnostic
checks recorded next to them (T4 deliverable), and the P5 scorer keeps the
P4 metric semantics unchanged for comparability.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import asdict, dataclass
from typing import Any

from ..literature.ingest import DocumentStore
from ..registry.textnorm import ascii_fold

ELIPSES = ("...", "\u2026", ". . .")
PARAPHRASE_THRESHOLD = 0.80
LOCATOR_CONTEXT_CHARS = 1500


def _norm(text: str) -> str:
    return " ".join(ascii_fold(text).split())


@dataclass
class ProvenanceReport:
    document_id_claimed: str | None
    document_match: bool
    quote_present: bool
    quote_verbatim: bool
    splice_suspected: bool
    quote_position: int | None
    page_claimed: int | None
    page_actual: int | None
    page_ok: bool | None
    locator_claimed: str | None
    locator_visible: bool | None
    paraphrase_warning: bool
    best_contiguous_fraction: float
    conditions_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_LOCATOR_RE = re.compile(
    r"(table|tab\.?)\s*([ivxlcdm]+|\d+[a-z]?)"
    r"|(figure|fig\.?)\s*(s?\d+[a-z]?)"
    r"|(equation|eq\.?)\s*\(?\s*(\d+[a-z]?)"
    r"|(section|sect\.?)\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


def _locator_key(locator: str) -> tuple[str, str] | None:
    m = _LOCATOR_RE.search(locator)
    if not m:
        return None
    if m.group(1):
        return ("table", m.group(2).lower())
    if m.group(3):
        return ("figure", m.group(4).lower())
    if m.group(5):
        return ("equation", m.group(6).lower())
    return ("section", m.group(7).lower())


def _locator_in_text(key: tuple[str, str], text: str) -> bool:
    kind, num = key
    patterns = {
        "table": rf"\btable\s+{re.escape(num)}\b",
        "figure": rf"\bfig(?:ure)?\.?\s+{re.escape(num)}\b",
        "equation": rf"\beq(?:uation)?\.?\s*\(?\s*{re.escape(num)}\b",
        "section": rf"\b(?:section|sect\.?)\s+{re.escape(num)}\b",
    }
    return re.search(patterns[kind], ascii_fold(text).lower()) is not None


def _find_page(
    store: DocumentStore, document_id: str, quote_norm: str
) -> tuple[int | None, int | None]:
    """(char position in full raw text, page) of the first segment whose page
    text contains the quote; used for page/proximity checks."""
    segments = store.segments(document_id)
    for seg in segments:
        if quote_norm and quote_norm in _norm(seg.text):
            return seg.char_start, seg.page
    return None, None


def _best_window_ratio(raw_norm: str, quote_norm: str) -> float:
    """Similarity of the quote to its best-matching document window.

    A single contiguous LCS fraction under-counts small edits (one inserted
    word splits the match in two), so we locate the longest common block,
    cut a window around it and use SequenceMatcher's edit-distance ratio.
    """
    if not quote_norm:
        return 0.0
    matcher = difflib.SequenceMatcher(None, raw_norm, quote_norm, autojunk=False)
    block = matcher.find_longest_match(0, len(raw_norm), 0, len(quote_norm))
    if block.size == 0:
        return 0.0
    # align the window so the matched block sits at the same offset as in
    # the quote, then compare against roughly the quote's own length
    lo = max(0, block.a - block.b)
    hi = min(len(raw_norm), lo + len(quote_norm) + 20)
    window = raw_norm[lo:hi]
    ratio = difflib.SequenceMatcher(None, window, quote_norm, autojunk=False).ratio()
    return ratio


def verify_candidate(
    candidate: dict[str, Any],
    store: DocumentStore,
    document_id: str,
    raw_doc_text: str | None = None,
) -> ProvenanceReport:
    """Verify one extraction candidate's provenance against the archive."""
    raw = (
        raw_doc_text
        if raw_doc_text is not None
        else (store.raw_dir / f"{document_id}.txt").read_text()
    )
    raw_norm = _norm(raw)
    src = candidate.get("source") or {}
    doc_claimed = src.get("document_id")
    quote = src.get("quote")
    quote_norm = _norm(quote) if isinstance(quote, str) and quote.strip() else ""
    document_match = doc_claimed == document_id

    quote_position: int | None = None
    quote_verbatim = bool(quote_norm) and quote_norm in raw_norm
    if quote_verbatim:
        quote_position = raw_norm.find(quote_norm)

    splice = bool(quote) and any(marker in quote for marker in ELIPSES)

    page_claimed = src.get("page") if isinstance(src.get("page"), int) else None
    page_actual: int | None = None
    if quote_verbatim:
        _, page_actual = _find_page(store, document_id, quote_norm)
    page_ok: bool | None
    if page_claimed is None or page_actual is None:
        page_ok = None
    else:
        page_ok = page_claimed == page_actual

    locator = src.get("locator")
    locator_key = _locator_key(locator) if isinstance(locator, str) and locator else None
    locator_visible: bool | None = None
    if locator_key is not None:
        if quote_verbatim and quote_position is not None:
            lo = max(0, quote_position - LOCATOR_CONTEXT_CHARS)
            hi = min(len(raw_norm), quote_position + len(quote_norm) + LOCATOR_CONTEXT_CHARS)
            locator_visible = _locator_in_text(locator_key, raw_norm[lo:hi])
        else:
            locator_visible = _locator_in_text(locator_key, raw_norm)

    best_frac = 0.0
    if not quote_verbatim and quote_norm:
        best_frac = _best_window_ratio(raw_norm, quote_norm)
    paraphrase_warning = (not quote_verbatim) and best_frac >= PARAPHRASE_THRESHOLD

    conditions_ok = candidate.get("temperature") is not None and candidate.get(
        "cell_config"
    ) not in (None, "UNRESOLVED")

    return ProvenanceReport(
        document_id_claimed=doc_claimed if isinstance(doc_claimed, str) else None,
        document_match=document_match,
        quote_present=bool(quote_norm),
        quote_verbatim=quote_verbatim,
        splice_suspected=splice,
        quote_position=quote_position,
        page_claimed=page_claimed,
        page_actual=page_actual,
        page_ok=page_ok,
        locator_claimed=locator if isinstance(locator, str) else None,
        locator_visible=locator_visible,
        paraphrase_warning=paraphrase_warning,
        best_contiguous_fraction=round(best_frac, 3),
        conditions_ok=conditions_ok,
    )


def summarize(reports: list[ProvenanceReport]) -> dict[str, Any]:
    """Aggregate provenance diagnostics over the candidates of one run."""
    n = len(reports)

    def frac(pred) -> float:
        return (sum(1 for r in reports if pred(r)) / n) if n else float("nan")

    return dict(
        n_candidates=n,
        document_match_rate=frac(lambda r: r.document_match),
        quote_present_rate=frac(lambda r: r.quote_present),
        quote_verbatim_rate=frac(lambda r: r.quote_verbatim),
        splice_rate=frac(lambda r: r.splice_suspected),
        paraphrase_warning_rate=frac(lambda r: r.paraphrase_warning),
        page_ok_rate=frac(lambda r: r.page_ok is True),
        page_checked=sum(1 for r in reports if r.page_ok is not None),
        locator_visible_rate=frac(lambda r: r.locator_visible is True),
        locator_checked=sum(1 for r in reports if r.locator_visible is not None),
        conditions_ok_rate=frac(lambda r: r.conditions_ok),
    )
