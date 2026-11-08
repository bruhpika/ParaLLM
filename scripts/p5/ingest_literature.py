"""P5 literature acquisition: ingest newly downloaded open-access papers.

Adds three CC BY 4.0 papers spanning different chemistries/families beyond
Chen2020 (NMC811/graphite-SiOx) to the immutable document store:

  - dessantis2023_batteries9_0146  Li-metal / LFP, CC BY 4.0
  - goussian2024_batteries10_00205 reaction-rate conventions, CC BY 4.0
  - laue2021_jappl_electrochem_51_1253 identifiability, CC BY 4.0

Idempotent: identical content is re-ingested without change (immutable
store); different content under the same id aborts (never overwrite).

Usage:
  .venv-ecosystem312/bin/python scripts/p5/ingest_literature.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

STORE_DIR = REPO_ROOT / "data/literature_store"
RETRIEVED = "2026-11-08"

DOCS = [
    dict(
        document_id="dessantis2023_batteries9_0146",
        pdf=REPO_ROOT
        / "data/raw_documents/dessantis2023_batteries9_0146/dessantis2023_batteries9_0146.pdf",
        kind="paper",
        title=(
            "Aging of a Lithium-Metal/LFP Cell: Predictive Model and "
            "Experimental Validation"
        ),
        doi_or_url="10.3390/batteries9030146",
        source_url=(
            "https://mdpi-res.com/d_attachment/batteries/batteries-09-00146/"
            "article_deploy/batteries-09-00146.pdf"
        ),
        meta={
            "license": "CC BY 4.0 (verified in PDF text)",
            "venue": "Batteries 2023, 9(3), 146",
            "sha256_pdf": (
                "f8fa76da5923a7feff3cc9c0fa2ec9e780320884533623b2447fea5ba9c96e7f"
            ),
            "acquisition_manifest": (
                "data/raw_documents/p5_sources/acquisition_manifest.json"
            ),
        },
    ),
    dict(
        document_id="goussian2024_batteries10_00205",
        pdf=REPO_ROOT
        / "data/raw_documents/goussian2024_batteries10_00205/"
        "goussian2024_batteries10_00205.pdf",
        kind="paper",
        title=(
            "A Novel Reaction Rate Parametrization Method for Lithium-Ion "
            "Battery Electrochemical Modelling"
        ),
        doi_or_url="10.3390/batteries10060205",
        source_url=(
            "https://mdpi-res.com/d_attachment/batteries/batteries-10-00205/"
            "article_deploy/batteries-10-00205.pdf"
        ),
        meta={
            "license": "CC BY 4.0 (verified in PDF text)",
            "venue": "Batteries 2024, 10(6), 205",
            "sha256_pdf": (
                "5a22a09983edab954a256099bfaf45d8404c4c76b318beac621aff732054afeb"
            ),
            "acquisition_manifest": (
                "data/raw_documents/p5_sources/acquisition_manifest.json"
            ),
        },
    ),
    dict(
        document_id="laue2021_jappl_electrochem_51_1253",
        pdf=REPO_ROOT
        / "data/raw_documents/laue2021_jappl_electrochem_51_1253/"
        "laue2021_jappl_electrochem_51_1253.pdf",
        kind="paper",
        title=(
            "Practical identifiability of electrochemical P2D models for "
            "lithium-ion batteries"
        ),
        doi_or_url="10.1007/s10800-021-01579-5",
        source_url=(
            "https://link.springer.com/content/pdf/"
            "10.1007/s10800-021-01579-5.pdf"
        ),
        meta={
            "license": "CC BY 4.0 International (verified in PDF text)",
            "venue": "Journal of Applied Electrochemistry 2021, 51, 1253-1265",
            "sha256_pdf": (
                "434b8dd96bc59f46bfa26c4da801f3be18b78da9343ce4fc6a1f0435f10c0e50"
            ),
            "acquisition_manifest": (
                "data/raw_documents/p5_sources/acquisition_manifest.json"
            ),
        },
    ),
]


def main() -> int:
    store = DocumentStore(STORE_DIR)
    have = {d.document_id for d in store.documents()}
    for doc in DOCS:
        if doc["document_id"] in have:
            print(f"already present: {doc['document_id']} (idempotent skip)")
            continue
        rec = store.ingest_pdf(
            doc["document_id"],
            doc["pdf"],
            kind=doc["kind"],
            title=doc["title"],
            doi_or_url=doc["doi_or_url"],
            source_url=doc["source_url"],
            retrieved=RETRIEVED,
            meta=doc["meta"],
        )
        print(
            f"ingested: {rec.document_id} kind={rec.kind} "
            f"n_segments={rec.n_segments} sha256={rec.content_sha256[:12]}..."
        )
    docs = store.documents()
    print(f"\nstore now holds {len(docs)} documents:")
    for d in docs:
        print(f"  {d.document_id}: {d.n_segments} segments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
