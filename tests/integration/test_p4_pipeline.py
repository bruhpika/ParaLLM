"""Integration test for the P4 benchmark pipeline (offline arm + rescore).

Deterministic, no network. Builds a fresh DocumentStore in a temporary
directory from the shipped article text and runs the offline arm over the
dev items, then re-scores the frozen "raw" outputs through the rescore path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pybamm_closed_loop.eval.benchmark_p4 import (
    load_items_v2,
    rescore_arm_from_raw,
    run_arm,
)
from pybamm_closed_loop.literature.extraction import OfflineDeterministicExtractor
from pybamm_closed_loop.literature.ingest import DocumentStore

REPO = Path(__file__).resolve().parents[2]
ARTICLE = REPO / "data/raw_documents/chen2020_jes_167_080534/chen2020_jes_167_080534_fulltext.txt"
FIXTURE = REPO / "data/eval/extraction_benchmark_v2.jsonl"


@pytest.fixture(scope="module")
def store_and_items(tmp_path_factory):
    store = DocumentStore(tmp_path_factory.mktemp("p4_store"))
    store.ingest_text(
        "chen2020_jes_167_080534",
        ARTICLE.read_text(),
        kind="paper",
        title="Chen2020",
        doi_or_url="10.1149/1945-7111/ab9050",
        retrieved="2026-11-08",
    )
    items = load_items_v2(FIXTURE)
    return store, [it for it in items if it.document_id == "chen2020_jes_167_080534"]


def test_offline_arm_dev_subset(store_and_items):
    store, items = store_and_items
    dev = [it for it in items if it.split == "dev"]
    assert len(dev) == 6
    report = run_arm(dev, store, arm="offline", client=OfflineDeterministicExtractor())
    m = report["metrics"]["dev"]
    # the six items were tuned during P3; the deterministic baseline keeps
    # identification at 1.0 and abstention perfect on the SEM item
    assert m["parameter_identification_accuracy"] == pytest.approx(1.0)
    assert m["abstention_accuracy"] == 1.0
    assert m["false_extraction_rate"] == pytest.approx(0.0)
    # every row records provenance even without an LLM (quotes verified)
    for row in report["per_item"]:
        if row["n_extracted"]:
            assert row["provenance_ok"] >= 1
            assert row["conditions_ok"] == 0  # deterministic extractor ignores conditions


def test_rescore_round_trip_preserves_metrics(store_and_items):
    store, items = store_and_items
    dev = [it for it in items if it.split == "dev"]
    report = run_arm(dev, store, arm="offline", client=OfflineDeterministicExtractor())
    # freeze raw rows to disk as the runner does
    raw_rows = report["raw_outputs"]
    rescored = rescore_arm_from_raw(dev, store, raw_rows, arm="offline")
    assert rescored["metrics"] == report["metrics"]


def test_fixture_probes_all_resolve_in_temp_store(store_and_items):
    store, items = store_and_items
    from pybamm_closed_loop.eval.benchmark import resolve_passage
    from pybamm_closed_loop.registry.textnorm import ascii_fold

    for it in items:
        passage = resolve_passage(store, it.document_id, it.passage_probe)
        assert ascii_fold(it.passage_probe) in ascii_fold(passage)
