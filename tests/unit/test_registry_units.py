"""Unit tests: registry units and text normalisation (P3)."""

import pytest

from pybamm_closed_loop.registry.textnorm import ascii_fold
from pybamm_closed_loop.registry.units import (
    is_exchange_current_reaction_rate_unit,
    normalize_token,
    pybamm_unit_suffix,
    to_canonical,
)


def test_pybamm_suffix_extraction():
    assert pybamm_unit_suffix("Negative particle diffusivity [m2.s-1]") == "m2.s-1"
    assert pybamm_unit_suffix("Negative electrode porosity") == ""


def test_normalize_token_folds_unicode_and_spaces():
    assert normalize_token("m2 s\u22121") == "m2.s-1"
    assert normalize_token("[m2.s-1]") == "m2.s-1"
    assert normalize_token("mol dm\u22123") == "mol.dm-3"
    assert normalize_token("5.86 \u00b5m") == "5.86.um"


def test_to_canonical_conversions():
    assert to_canonical("%") == ("fraction", 1e-2)
    assert to_canonical("m2 s-1") == ("m2.s-1", 1.0)
    assert to_canonical("um") == ("m", 1e-6)
    assert to_canonical("\u00b5m") == ("m", 1e-6)
    assert to_canonical("mA cm-2") == ("A.m-2", 10.0)
    assert to_canonical("kJ mol-1") == ("J.mol-1", 1e3)


def test_to_canonical_unknown_unit_raises():
    with pytest.raises(KeyError):
        to_canonical("furlongs.per.fortnight")


def test_reaction_rate_unit_detection():
    assert is_exchange_current_reaction_rate_unit("A m-2 (m3 mol-1)1.5")
    assert not is_exchange_current_reaction_rate_unit("A m-2")


def test_ascii_fold_preserves_length():
    s = "3.42\u00b710\u22126 A m-2"
    f = ascii_fold(s)
    assert len(f) == len(s)
    assert "3.42" in f
