"""Agent B (security): document ids must not traverse the store root when
used as raw/segments filenames (ingest write path, _load read path, and
the eval benchmark readers)."""

import json

import pytest

from pybamm_closed_loop.eval.benchmark import raw_text
from pybamm_closed_loop.literature.ingest import DocumentStore

TEXT = "Some plain text body for the document."


@pytest.mark.parametrize(
    "bad_id",
    ["../evil", "../../etc/passwd", "a/b", "a\\b", "./dot", ".hidden", "..", ""],
)
def test_ingest_rejects_traversing_ids(tmp_path, bad_id):
    store = DocumentStore(tmp_path / "store")
    with pytest.raises(ValueError, match="document id"):
        store.ingest_text(bad_id, TEXT)
    raw_files = list((tmp_path / "store" / "raw").iterdir())
    assert raw_files == [], "no file may be written for a rejected id"
    assert (tmp_path / "evil").exists() is False and not list(tmp_path.glob("*.txt"))


def test_valid_document_ids_still_accepted(tmp_path):
    store = DocumentStore(tmp_path)
    doc = store.ingest_text("chen2020_jes_167_080534", TEXT)
    assert doc.document_id == "chen2020_jes_167_080534"
    assert (store.raw_dir / "chen2020_jes_167_080534.txt").exists()


def test_benchmark_reader_rejects_traversing_id(tmp_path):
    store = DocumentStore(tmp_path)
    store.ingest_text("docA", TEXT)
    with pytest.raises(ValueError, match="document id"):
        raw_text(store, "../docA")
    with pytest.raises(ValueError, match="document id"):
        raw_text(store, "docA/../docB")


def test_corrupt_manifest_with_traversing_id_rejected(tmp_path):
    root = tmp_path / "store"
    (root / "segments").mkdir(parents=True)
    (root / "documents.json").write_text(
        json.dumps(
            [
                {
                    "document_id": "../../outside",
                    "kind": "paper",
                    "raw_path": "outside.txt",
                    "content_sha256": "0" * 64,
                    "retrieved": "2026-11-07",
                    "page_structure": False,
                    "source_url": None,
                    "doi_or_url": None,
                    "title": None,
                    "n_segments": 0,
                }
            ]
        )
    )
    with pytest.raises(ValueError, match="document id"):
        DocumentStore(root)
