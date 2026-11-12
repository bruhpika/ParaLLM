"""V2.5 — Evidence engineering: condition-aware evidence windows.

The v0.1 retrieval layer hands the extractor a ±260-character window around a
probe. That window usually contains the *value* but not the *conditions* the
value was measured under (temperature, SOC, cell, rate) — which is why the
v0.1 benchmark reports weak condition completeness (0.116 all / 0.035 eval).

This module builds a wider, condition-aware evidence window:

- the probe span is always kept verbatim (never re-worded),
- surrounding sentences that mention experimental conditions are included,
- the conditions that *are* present in the window are extracted
  deterministically (no LLM) so their availability can be measured.

Everything here is deterministic and text-preserving: the window is a verbatim
substring of the archived document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..registry.textnorm import ascii_fold

# condition cues used for sentence selection and extraction
_TEMPERATURE_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(?:°|deg\s*|degrees?\s*)?\s*(k\b|c\b|celsius|kelvin)",
    re.IGNORECASE,
)
_SOC_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:soc|state[- ]of[- ]charge)", re.IGNORECASE)
_SOC_ALT_RE = re.compile(r"soc\s*(?:of|=|:)?\s*(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)
_CRATE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*c\b(?!\w)", re.IGNORECASE)
_CELL_RE = re.compile(r"\b(lg\s?m50|lgnm50|18650|21700|coin cell|pouch cell|cylindrical)\b", re.IGNORECASE)
_CHEMISTRY_RE = re.compile(
    r"\b(nmc\s?\d{3}|nmc|lfp|lco|lmo|nca|li[- ]metal|graphite|siox|siOx)\b", re.IGNORECASE
)
_METHOD_RE = re.compile(
    r"\b(eis|gitt|icp|fit|calibrat\w*|measur\w*|estimat\w*|assum\w*|comput\w*|calculat\w*)\b",
    re.IGNORECASE,
)

_CUE_RE = re.compile(
    r"(\d+\s*(?:°|deg\s*|degrees?\s*)?\s*(?:k|c|celsius|kelvin)\b"
    r"|soc|state[- ]of[- ]charge|\bc\b|\d+\s*%\s*(?:soc)"
    r"|lg\s?m50|lgnm50|coin cell|pouch|nmc|lfp|lco|li[- ]metal|graphite|siox"
    r"|eis|gitt|fit|calibrat|measur)",
    re.IGNORECASE,
)


@dataclass
class ConditionFacts:
    """Conditions detected inside an evidence window (deterministic)."""

    temperature_k: float | None = None
    temperature_text: str | None = None
    soc_percent: float | None = None
    soc_text: str | None = None
    c_rates: list[float] = field(default_factory=list)
    cell_mentions: list[str] = field(default_factory=list)
    chemistry_mentions: list[str] = field(default_factory=list)
    method_mentions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature_k": self.temperature_k,
            "temperature_text": self.temperature_text,
            "soc_percent": self.soc_percent,
            "soc_text": self.soc_text,
            "c_rates": list(self.c_rates),
            "cell_mentions": list(self.cell_mentions),
            "chemistry_mentions": list(self.chemistry_mentions),
            "method_mentions": list(self.method_mentions),
        }

    def coverage(self) -> dict[str, bool]:
        """Which condition classes are present in the evidence window."""
        return {
            "temperature": self.temperature_k is not None,
            "soc": self.soc_percent is not None,
            "c_rate": bool(self.c_rates),
            "cell": bool(self.cell_mentions),
            "chemistry": bool(self.chemistry_mentions),
            "method": bool(self.method_mentions),
        }


def extract_conditions(text: str) -> ConditionFacts:
    """Extract the conditions stated in a window (deterministic, verbatim)."""
    facts = ConditionFacts()

    for m in _TEMPERATURE_RE.finditer(text):
        raw = m.group(0)
        value = float(m.group(1))
        unit = m.group(2).lower()
        kelvin = value + 273.15 if unit.startswith("c") else value
        if 200.0 <= kelvin <= 400.0:
            facts.temperature_k = kelvin
            facts.temperature_text = raw.strip()
            break

    m = _SOC_RE.search(text) or _SOC_ALT_RE.search(text)
    if m:
        facts.soc_percent = float(m.group(1))
        facts.soc_text = m.group(0).strip()

    seen_rates: list[float] = []
    for m in _CRATE_RE.finditer(text):
        try:
            val = float(m.group(1))
        except ValueError:
            continue
        if 0.01 <= val <= 20 and val not in seen_rates:
            seen_rates.append(val)
    facts.c_rates = seen_rates[:5]

    facts.cell_mentions = [m.group(0).strip() for m in _CELL_RE.finditer(text)][:5]
    facts.chemistry_mentions = [m.group(0).strip() for m in _CHEMISTRY_RE.finditer(text)][:6]
    facts.method_mentions = [m.group(0).strip().lower() for m in _METHOD_RE.finditer(text)][:6]
    return facts


@dataclass
class EvidenceWindow:
    """A verbatim evidence window around a probe."""

    document_id: str
    probe: str
    text: str
    char_start: int
    char_end: int
    page: int | None = None
    conditions: ConditionFacts = field(default_factory=ConditionFacts)
    n_sentences_included: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "probe": self.probe,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page": self.page,
            "conditions": self.conditions.to_dict(),
            "coverage": self.conditions.coverage(),
            "n_sentences_included": self.n_sentences_included,
            "n_chars": len(self.text),
        }


# cues that indicate an experiment-setup statement (document level)
_SETUP_RE = re.compile(
    r"(all\s+(?:experiments|measurements|tests)|experiments\s+were|were\s+carried\s+out"
    r"|were\s+conducted|were\s+performed|assembled\s+cells|at\s+25\s*°?\s*c"
    r"|at\s+room\s+temperature|ambient\s+temperature|chamber"
    r"|\bcell\s+was\b|cells\s+were|c-rate|discharge\s+at|charge\s+at"
    r"|\bsoc\b|state\s+of\s+charge|cut-?off\s+voltage)",
    re.IGNORECASE,
)


@dataclass
class DocumentConditions:
    """Experiment-setup statements found at document level (verbatim)."""

    sentences: list[str] = field(default_factory=list)
    facts: ConditionFacts = field(default_factory=ConditionFacts)

    def coverage(self) -> dict[str, bool]:
        return self.facts.coverage()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentences": list(self.sentences),
            "facts": self.facts.to_dict(),
            "coverage": self.coverage(),
        }


def document_conditions(raw_text: str, max_sentences: int = 8) -> DocumentConditions:
    """Find the document-level experimental setup statements (deterministic).

    Experimental conditions are usually stated in the methods/experimental
    section, far from the table where a value is printed. This helper selects
    the sentences that carry setup cues (temperature, cell, rate, SOC) and
    returns them **verbatim**, ranked by how many distinct condition classes
    they mention.

    The returned sentences are document-level statements: they describe the
    experiment, not necessarily the specific value, so the consumer must label
    them as such.
    """
    spans = _split_sentences(raw_text)
    candidates: list[tuple[int, str, ConditionFacts]] = []
    for start, end in spans:
        sentence = raw_text[start:end].strip()
        if not sentence or len(sentence) > 600:
            continue
        if not _SETUP_RE.search(sentence):
            continue
        facts = extract_conditions(sentence)
        n_classes = sum(1 for v in facts.coverage().values() if v)
        if n_classes == 0:
            continue
        candidates.append((start, sentence, facts))

    # greedy class coverage: the scarcest condition classes are served first,
    # so the block covers temperature/SOC/cell before it repeats a method cue
    priority = ("temperature", "soc", "cell", "c_rate", "chemistry", "method")
    covered: set[str] = set()
    chosen_idx: list[int] = []
    for cls in priority:
        best = None
        for i, (_start, _sentence, facts) in enumerate(candidates):
            if i in chosen_idx:
                continue
            cov = facts.coverage()
            if not cov.get(cls):
                continue
            # prefer a sentence that adds the most *new* classes
            new_classes = sum(
                1 for c, v in cov.items() if v and c not in covered
            )
            key = (-new_classes, candidates[i][0])
            if best is None or key < best[0]:
                best = (key, i)
        if best is not None:
            chosen_idx.append(best[1])
            for c, v in candidates[best[1]][2].coverage().items():
                if v:
                    covered.add(c)
    # fill remaining slots with the sentences carrying the most condition classes
    for i, (_start, _sentence, facts) in enumerate(candidates):
        if len(chosen_idx) >= max_sentences:
            break
        if i in chosen_idx:
            continue
        n_classes = sum(1 for v in facts.coverage().values() if v)
        if n_classes >= 2:
            chosen_idx.append(i)
            for c, v in facts.coverage().items():
                if v:
                    covered.add(c)

    chosen = [candidates[i][1] for i in sorted(chosen_idx, key=lambda i: candidates[i][0])]
    facts = extract_conditions(" ".join(chosen))
    return DocumentConditions(sentences=chosen, facts=facts)


def _split_sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans (start, end) of ``text`` — deterministic, punctuation-based."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        end = m.start()
        if end > start:
            spans.append((start, end))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def build_evidence_window(
    raw_text: str,
    document_id: str,
    probe: str,
    *,
    compact_chars: int = 260,
    expand_chars: int = 900,
    max_condition_sentences: int = 6,
    page: int | None = None,
) -> EvidenceWindow:
    """Build a condition-aware window around ``probe`` in ``raw_text``.

    The probe span is always included verbatim. Additionally, up to
    ``max_condition_sentences`` nearby sentences that mention experimental
    conditions are included, extending the window by at most ``expand_chars``
    characters on each side.
    """
    folded = ascii_fold(raw_text)
    idx = folded.find(ascii_fold(probe))
    if idx < 0:
        raise ValueError(f"probe {probe!r} not found in document {document_id}")

    lo = max(0, idx - compact_chars)
    hi = min(len(raw_text), idx + len(probe) + compact_chars)

    # sentence boundaries in the neighbourhood
    window_start = max(0, idx - expand_chars)
    window_end = min(len(raw_text), idx + len(probe) + expand_chars)
    neighbourhood = raw_text[window_start:window_end]
    offsets = [(window_start + a, window_start + b) for a, b in _split_sentences(neighbourhood)]

    probe_lo, probe_hi = idx, idx + len(probe)
    selected: list[tuple[int, int]] = []
    for s_start, s_end in offsets:
        if s_end < probe_lo or s_start > probe_hi:
            if _CUE_RE.search(raw_text[s_start:s_end]):
                selected.append((s_start, s_end))
    # keep the closest sentences to the probe, then the outermost ones
    selected.sort(key=lambda sp: min(abs(sp[0] - probe_lo), abs(sp[1] - probe_hi)))
    selected = selected[:max_condition_sentences]
    for sp in selected:
        lo = min(lo, sp[0])
        hi = max(hi, sp[1])

    text = raw_text[lo:hi]
    conditions = extract_conditions(text)
    n_sentences = len(_split_sentences(text))
    return EvidenceWindow(
        document_id=document_id,
        probe=probe,
        text=text,
        char_start=lo,
        char_end=hi,
        page=page,
        conditions=conditions,
        n_sentences_included=n_sentences,
    )


def window_from_store(
    store: Any,
    document_id: str,
    probe: str,
    *,
    compact_chars: int = 260,
    expand_chars: int = 900,
) -> EvidenceWindow:
    """Build an evidence window from the document store (raw text + page)."""
    raw = (store.raw_dir / f"{document_id}.txt").read_text()
    page = None
    try:
        segments = store.segments(document_id)
        folded = ascii_fold(raw)
        idx = folded.find(ascii_fold(probe))
        for seg in segments:
            if seg.page is None:
                continue
            if idx >= seg.char_start and idx <= seg.char_end:
                page = seg.page
                break
    except Exception:  # pragma: no cover - store without page structure
        page = None
    return build_evidence_window(
        raw,
        document_id,
        probe,
        compact_chars=compact_chars,
        expand_chars=expand_chars,
        page=page,
    )
