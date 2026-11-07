"""Quality-focused tests added by agentC (code-quality audit).

Covers behavior-preserving refactors: narrowed exception scopes in
registry.seed and the reshaped figure-generator dispatch. Fast and
deterministic; no scientific benchmarks here.
"""

from __future__ import annotations

from pathlib import Path

from pybamm_closed_loop.registry import seed as seed_mod
from pybamm_closed_loop.registry.model import sha256_text
from pybamm_closed_loop.reporting.figures import generate_all_figures


def test_reaction_rate_probe_handles_builtin_typeerror():
    # inspect.getsource raises TypeError for builtins; the narrowed
    # (OSError, TypeError) handler must still degrade gracefully.
    out = seed_mod._check_reaction_rate_embedded(len, "pos_reaction_rate")
    assert out["reaction_rate_probe"] == "3.42"
    assert out["reaction_rate_embedded"] == "unknown (source unavailable)"


def test_reaction_rate_probe_on_plain_function():
    def j0(x, y):
        return 3.42

    out = seed_mod._check_reaction_rate_embedded(j0, "pos_reaction_rate")
    assert out["reaction_rate_probe"] == "3.42"
    assert out["reaction_rate_embedded"] is True

    def j0_other(x, y):
        return 0.0  # no reaction-rate constant embedded in this body

    out_neg = seed_mod._check_reaction_rate_embedded(j0_other, "neg_reaction_rate")
    assert out_neg["reaction_rate_probe"] == "6.48"
    assert out_neg["reaction_rate_embedded"] is False


def test_sha256_text_is_stable_hex():
    assert sha256_text("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_generate_all_figures_empty_input_writes_nothing(tmp_path: Path):
    figures_dir = tmp_path / "figs"
    written = generate_all_figures(series={}, profiles={}, figures_dir=figures_dir)
    assert written == []
    assert not figures_dir.exists()
