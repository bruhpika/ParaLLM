"""Unit tests: extraction benchmark metrics (P3)."""

from pybamm_closed_loop.eval.benchmark import (
    BenchmarkItem,
    GoldEntry,
    canonical_of,
    groups_of,
    run_benchmark,
    unit_matches,
    value_matches,
)
from pybamm_closed_loop.literature.ingest import DocumentStore

_FILLER = (
    "General discussion of teardown procedures and microscopy analysis "
    "methods used for characterisation of commercial cells. "
) * 4

ARCHIVE = f"""{_FILLER}
The electrode conductivity values 0.18 S m-1 and 215 S m-1 were used for
the positive electrode and the negative electrode respectively after
four-point probe tests.
{_FILLER}
A closing paragraph.
{_FILLER}
"""


def test_canonical_of_converts_units():
    g = GoldEntry(parameter_name="p", value=33.5, unit="%")
    assert canonical_of(g) == (0.335, "fraction")


def test_unit_and_value_matching_rules():
    assert unit_matches("A.m-2", "A.m-2.(m3.mol-1)^1.5")
    assert unit_matches("m", "m")
    assert not unit_matches("m", "m2")
    assert value_matches(0.335, 0.335)
    assert not value_matches(0.34, 0.335)


def test_alias_group_membership():
    assert "conductivity" in groups_of("positive electrode conductivity")
    assert "particle_radius" in groups_of("mean particle radius")


def test_run_benchmark_metrics(tmp_path):
    store = DocumentStore(tmp_path)
    store.ingest_text("doc1", ARCHIVE)
    items = [
        BenchmarkItem(
            item_id="T1",
            document_id="doc1",
            passage_probe="values 0.18 S m-1 and 215 S m-1",
            facets={"parameter_names": ["electrode conductivity"]},
            gold=[
                GoldEntry("positive electrode conductivity", 0.18, "S m-1"),
                GoldEntry("negative electrode conductivity", 215, "S m-1"),
            ],
        ),
        BenchmarkItem(
            item_id="T2",
            document_id="doc1",
            passage_probe="A closing paragraph",
            facets={"parameter_names": ["tortuosity"]},
            gold=[],
            expect_abstain=True,
        ),
    ]
    report = run_benchmark(items, store)
    m = report["metrics"]
    assert m["parameter_identification_accuracy"] == 1.0
    assert m["value_extraction_accuracy"] == 1.0
    assert m["unit_correctness"] == 1.0
    assert m["provenance_accuracy"] == 1.0
    assert m["abstention_accuracy"] == 1.0
    assert m["false_extraction_rate"] == 0.0
    assert report["per_item"][0]["identified"] == 2
