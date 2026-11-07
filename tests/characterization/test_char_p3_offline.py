"""Characterization tests, P3 offline extraction benchmark (gate:
.venv-ecosystem312).

Runs the real world offline benchmark over the expert-reviewed gold fixture
and snapshots every metric. Metrics are coarse fractions (0, 1, thirds...),
so exact equality is the right gate; the fixture is immutable data.

Needs pypdf-free offline path only (no pybop import required, but the module
imports polars transitively? — no, extraction is pull-based and stdlib only;
it does need the ingested literature store committed under data/).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pybamm")

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parents[1] / "baselines"


def test_p3_offline_metrics_match_baseline():
    from pybamm_closed_loop.eval.benchmark import load_items, run_benchmark
    from pybamm_closed_loop.literature.ingest import DocumentStore

    data_root = REPO_ROOT / "data"
    items = load_items(data_root / "eval" / "extraction_benchmark_v1.jsonl")
    store = DocumentStore(data_root / "literature_store")
    report = run_benchmark(items, store, client=None)

    expected = json.loads((BASE_DIR / "char_p3_offline.json").read_text())
    assert report["provider"] == expected["provider"]
    for metric, value in expected["metrics"].items():
        got = report["metrics"].get(metric)
        if value != value:  # NaN tolerance
            assert got != got
        else:
            assert got == pytest.approx(value, rel=1e-12)
    for e_item, a_item in zip(expected["per_item"], report["per_item"]):
        for key in (
            "item_id",
            "expect_abstain",
            "abstained",
            "n_extracted",
            "identified",
            "gold",
            "value_ok",
            "unit_ok",
            "conditions_ok",
            "provenance_ok",
            "false_extractions",
        ):
            assert a_item[key] == e_item[key], (
                f"{e_item['item_id']}.{key}: {a_item[key]} != {e_item[key]}"
            )
    assert report["totals"] == expected["totals"]
