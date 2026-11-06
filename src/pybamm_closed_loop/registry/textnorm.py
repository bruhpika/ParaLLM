"""Unicode-to-ASCII folding with preserved character offsets (P3).

The archived article text mixes unicode typography (minus sign, middle dot,
micro sign). Retrieval, probing and quoting all need ASCII-stable handling,
but provenance quotes must remain verbatim. A 1:1 character map preserves
length, so character offsets found in the folded text are exactly valid in
the original text.
"""

from __future__ import annotations

_CHARMAP = {
    "\u2212": "-",  # unicode minus
    "\u2013": "-",  # en dash
    "\u2011": "-",  # non-breaking hyphen
    "\u00b7": ".",  # middle dot
    "\u00b5": "u",  # micro sign
    "\u03bc": "u",  # greek small letter mu (often used as micro)
    "\u00a0": " ",  # no-break space
    "\u2019": "'",  # right single quote
    "\u2018": "'",  # left single quote
    "\u201c": '"',
    "\u201d": '"',
}


def ascii_fold(text: str) -> str:
    """Fold unicode typography to ASCII, 1:1 per character (length kept)."""
    return "".join(_CHARMAP.get(ch, ch) for ch in text)
