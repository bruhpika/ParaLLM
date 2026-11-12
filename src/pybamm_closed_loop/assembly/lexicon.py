"""Auditable keyword lexicon for parsing free-text experimental conditions.

The parameter registry stores conditions as free text (e.g.
``"LG M50 21700, extracted electrodes"``), so the applicability rubric needs a
deterministic way to recover comparable facts (cell product, format, chemistry
family) from those strings.

Design rules (auditable, no guessing):
- Every keyword is listed here, so a reviewer can see exactly why a candidate
  scored the way it did.
- Nothing is inferred silently: an unrecognised string yields
  ``None`` (unknown), never a default value. Unknown facts lower confidence
  but never block a candidate by themselves.
- Chemistry matching is done on **family** labels (``NMC``, ``LFP``, ``LCO``,
  ``NCA``, ``LMO``, ``Li-metal``, ``graphite``...) so that, e.g., NMC111 and
  NMC811 are "same family, different composition" rather than "unknown".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# cell product identifiers seen in the corpus (substring match, case-insensitive)
CELL_PRODUCTS: tuple[str, ...] = (
    "lg m50",
    "lgnm50",
    "prada",
    "oregan",
    "ecker",
    "marquis",
    "m50",
)

# cylindrical/pouch/coin format keywords -> canonical format labels
FORMAT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "21700": ("21700",),
    "18650": ("18650",),
    "pouch": ("pouch",),
    "coin": ("coin cell", "coin-cell", "coin"),
    "cylindrical": ("cylindrical", "cylinder", "can"),
    "prismatic": ("prismatic",),
}

# chemistry family keywords, ordered: the first family found wins
CHEMISTRY_FAMILIES: dict[str, tuple[str, ...]] = {
    "NMC": ("nmc", "linio", "lini", "ni0.8", "ni0.83", "nmc811", "nmc 811"),
    "NCA": ("nca", "linico"),
    "LFP": ("lfp", "lifepo4", "lifepo"),
    "LCO": ("lco", "lico", "lithium cobalt", "licoo2"),
    "LMO": ("lmo", "limo"),
    "Li-metal": ("li-metal", "li metal", "lithium metal", "li–metal", "anode-free"),
    "graphite": ("graphite", "gr–", "siOx", "siox", "silicon"),
}

# electrode-side keywords (positive/negative) used for the compatibility note
POSITIVE_KEYWORDS: tuple[str, ...] = ("positive", "cathode", "nmc", "lco", "lmo", "lfp", "nca")
NEGATIVE_KEYWORDS: tuple[str, ...] = ("negative", "anode", "graphite", "siOx", "siox", "li-metal")


@dataclass(frozen=True)
class CellFacts:
    """Facts recovered from a free-text condition blob."""

    cell_product: str | None
    format: str | None
    chemistry_families: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "cell_product": self.cell_product,
            "format": self.format,
            "chemistry_families": list(self.chemistry_families),
            "warnings": list(self.warnings),
        }


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def parse_cell_facts(*texts: str | None) -> CellFacts:
    """Recover (cell product, format, chemistry families) from condition text.

    Multiple texts (e.g. ``cell`` + ``chemistry`` + ``material``) are combined;
    the union of the chemistry families is returned.
    """
    blob = " | ".join(_normalise(t) for t in texts if t)
    warnings: list[str] = []

    product: str | None = None
    for candidate in CELL_PRODUCTS:
        if candidate in blob:
            product = "LG M50" if candidate in ("lg m50", "lgnm50", "m50") else candidate
            break

    fmt: str | None = None
    for label, keys in FORMAT_KEYWORDS.items():
        if any(k in blob for k in keys):
            fmt = label
            break

    families: list[str] = []
    for family, keys in CHEMISTRY_FAMILIES.items():
        if any(k in blob for k in keys) and family not in families:
            families.append(family)

    if not families:
        warnings.append("no chemistry family recognised in conditions")
    if product is None:
        warnings.append("no cell product recognised in conditions")

    return CellFacts(
        cell_product=product,
        format=fmt,
        chemistry_families=tuple(families),
        warnings=tuple(warnings),
    )


def same_chemistry_family(a: str, b: str) -> bool:
    """True when two family labels denote the same family."""
    return a == b
