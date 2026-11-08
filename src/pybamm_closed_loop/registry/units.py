"""Canonical battery-parameter unit handling (P3).

Small, explicit, purpose-built registry of the units used by PyBaMM
parameter names and battery literature. Every conversion is defined
numerically in this file so it can be unit-tested; nothing is guessed at
runtime. This is not PyBaMM functionality, so it does not violate the
"do not reimplement upstream" rule.
"""

from __future__ import annotations

import re

# canonical_unit -> dimension signature
# Primitives: L length, M mass, T time, N amount, I current,
# TH temperature, Q charge.
DIMENSIONS: dict[str, str] = {
    "dimensionless": "",
    "fraction": "",
    "length": "L",
    "area": "L^2",
    "volume": "L^3",
    "K": "TH",
    "m": "L",
    "m2": "L^2",
    "m3": "L^3",
    "m2.s-1": "L^2/T",
    "m.s-1": "L/T",
    "m3.mol-1": "L^3/N",
    "mol.m-3": "N/L^3",
    "A": "I",
    "A.m-2": "I/L^2",
    "A.h": "Q",
    "V": "M*L^2/(T^3*I)",
    "V.K-1": "M*L^2/(T^3*I*TH)",
    "S.m-1": "I^2*T^3/(M*L^3)",
    "Ohm": "M*L^2/(T^3*I^2)",
    "Ohm.m": "M*L^3/(T^3*I^2)",
    "F.m-2": "T^4*I^2/(M*L^4)",
    "J.mol-1": "M*L^2/(T^2*N)",
    "J.kg-1.K-1": "L^2/(T^2*TH)",
    "kg.m-3": "M/L^3",
    "W.m-1.K-1": "M*L/(T^3*TH)",
    "W.m-2.K-1": "M/(T^3*TH)",
    "m.K-1": "L/TH",
}

# unit token -> (canonical unit, multiplicative factor to canonical)
CONVERSIONS: dict[str, tuple[str, float]] = {
    "dimensionless": ("dimensionless", 1.0),
    "-": ("dimensionless", 1.0),
    "--": ("dimensionless", 1.0),
    "%": ("fraction", 1e-2),
    "m": ("m", 1.0),
    "mm": ("m", 1e-3),
    "cm": ("m", 1e-2),
    "um": ("m", 1e-6),
    "m2": ("m2", 1.0),
    "cm2": ("m2", 1e-4),
    "m3": ("m3", 1.0),
    "cm3": ("m3", 1e-6),
    "K": ("K", 1.0),
    "C": ("K", 1.0),
    "mol.m-3": ("mol.m-3", 1.0),
    "mol.dm-3": ("mol.m-3", 1e3),
    "A": ("A", 1.0),
    "A.m-2": ("A.m-2", 1.0),
    "A.cm-2": ("A.m-2", 1e4),
    "mA.cm-2": ("A.m-2", 10.0),
    "A.h": ("A.h", 1.0),
    "Ah": ("A.h", 1.0),
    "V": ("V", 1.0),
    "mV": ("V", 1e-3),
    "V.K-1": ("V.K-1", 1.0),
    "mV.K-1": ("V.K-1", 1e-3),
    "S.m-1": ("S.m-1", 1.0),
    "Ohm": ("Ohm", 1.0),
    "Ohm.m": ("Ohm.m", 1.0),
    "F.m-2": ("F.m-2", 1.0),
    "J.mol-1": ("J.mol-1", 1.0),
    "kJ.mol-1": ("J.mol-1", 1e3),
    "J.kg-1.K-1": ("J.kg-1.K-1", 1.0),
    "kg.m-3": ("kg.m-3", 1.0),
    "g.cm-3": ("kg.m-3", 1e3),
    "W.m-1.K-1": ("W.m-1.K-1", 1.0),
    "W.m-2.K-1": ("W.m-2.K-1", 1.0),
    "m.K-1": ("m.K-1", 1.0),
    "m2.s-1": ("m2.s-1", 1.0),
    "m.s-1": ("m.s-1", 1.0),
    "m3.mol-1": ("m3.mol-1", 1.0),
}

_M3MOL_RE = re.compile(r"^A\.m-2\.?\(?m3\.mol-1\)?\.?[0-9.]*$")


def normalize_token(token: str) -> str:
    """Normalise a unit token so alias matching is reliable.

    Handles paper typography: unicode minus (U+2212), en dash, soft hyphen,
    unicode micro sign (U+00B5) and middle dot (U+00B7) exponents, and
    inter-atom spaces.
    """
    if not isinstance(token, str):
        raise TypeError("unit token must be a string")
    t = token
    t = t.replace("\u2212", "-")  # unicode minus
    t = t.replace("\u2013", "-")  # en dash
    t = t.replace("\u2011", "-")  # non-breaking hyphen
    t = t.replace("\u00b7", ".")  # middle dot
    t = t.replace("\u00b5", "u")  # micro sign
    t = t.replace("\u03bc", "u")  # greek small letter mu
    t = re.sub(r"\s+", " ", t.strip())
    t = t.replace(" ", ".")
    if t.startswith("[") and t.endswith("]"):
        t = t[1:-1]
    return t


def to_canonical(token: str) -> tuple[str, float]:
    """Return (canonical_unit_name, factor) for a unit token.

    Raises KeyError for unknown units; never silently maps (rule 6).
    """
    norm = normalize_token(token)
    try:
        return CONVERSIONS[norm]
    except KeyError as exc:
        raise KeyError(f"unknown unit token: {token!r}") from exc


def pybamm_unit_suffix(pybamm_name: str) -> str:
    """Extract the bracketed unit suffix from a PyBaMM parameter name.

    Dimensionless PyBaMM parameters carry no bracket suffix; returns "" for
    those (the registry expresses them explicitly as "dimensionless").
    """
    m = re.search(r"\[([^\[\]]+)\]$", pybamm_name)
    return m.group(1) if m else ""


def is_exchange_current_reaction_rate_unit(token: str) -> bool:
    """True for the paper-style reaction-rate unit
    ``A m-2 (m3 mol-1)^1.5`` used in Chen2020 Table VII."""
    return bool(_M3MOL_RE.match(normalize_token(token)))


def dimension_of(canonical_unit: str) -> str | None:
    """Return the dimension signature (primitives L/M/T/N/I/TH/Q) of a
    canonical unit token, or ``None`` for unknown tokens."""
    return DIMENSIONS.get(canonical_unit)
