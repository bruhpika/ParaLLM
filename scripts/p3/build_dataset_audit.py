"""Build the P3 dataset-audit artifact (Part F).

Regenerates the deterministic local audit (Neware sample) and merges it
with web-researched candidate records (each carrying URL + retrieval date).
No dataset is selected here.

Usage:
    .venv-ecosystem312/bin/python scripts/p3/build_dataset_audit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.datasets.pyprobe_link import audit_neware_sample  # noqa: E402

RETRIEVED = "2026-11-06"

WEB_CANDIDATES = [
    {
        "dataset_id": "pyprobe-sample-lgm50-ndk-bol-rpt",
        "title": (
            "PyProBE sample data: NDK - LG M50 deg - exp 2,2 - rig 3 - 25degC - "
            "cell C - BoL - RPT0_short_CA4"
        ),
        "source_url": "https://github.com/ImperialCollegeLondon/PyProBE/tree/main/tests/sample_data/LGM50",
        "doi_or_identifier": "file name encodes: NDK source, LG M50 degradation series, rig 3, 25 degC, cell C, beginning-of-life RPT",
        "license": "repository code is BSD-3-Clause; explicit data license for this file UNRESOLVED (verify before use)",
        "chemistry": "LG M50 (graphite-SiOx / NMC 811) - name-verified; details per Chen2020 scope",
        "cell_format": "commercial cell (LG M50, 21700 implied by product name)",
        "nominal_capacity": "~5 A.h (product nominal; measured capacity in this RPT UNRESOLVED until file is processed)",
        "temperature": "25 degC (file name; recorded temperature channel UNRESOLVED until processed)",
        "c_rates": "RPT protocol contents UNRESOLVED until README.yaml (339 B) is processed",
        "voltage_limits": "UNRESOLVED until processed",
        "protocol": "reference performance test (RPT0_short_CA4) at beginning of life; full protocol in the accompanying README.yaml",
        "metadata_completeness": "file-name metadata + README.yaml present; source database (NDK) not locally documented",
        "observations": "processed parquet (2,185,238 bytes) in upstream repo; not present in the pip wheel",
        "requirements": [
            {"requirement": "cell identity matches LG M50 / Chen2020 scope", "observed": "LG M50 (per file name)", "status": "met", "evidence": "repo file name, verified 2026-11-06"},
            {"requirement": "nominal capacity ~5 A.h", "observed": "product nominal 5 A.h; measured capacity UNRESOLVED", "status": "unknown", "evidence": "file not processed yet"},
            {"requirement": "temperature 298.15 K recorded", "observed": "25 degC in file name", "status": "met", "evidence": "file name"},
            {"requirement": "0.5C/1C/2C discharge protocol", "observed": "RPT contents UNRESOLVED", "status": "unknown", "evidence": "README.yaml not yet processed"},
            {"requirement": "calibration/validation split possible", "observed": "single BoL RPT file; more cycles likely in the wider NDK series", "status": "unknown", "evidence": "repo listing"},
        ],
        "verdict": "CANDIDATE",
        "notes": [
            f"Web-researched candidate (retrieved {RETRIEVED}); content audit pending local download + PyProBE processing.",
            "This is the candidate named in docs/EXPERIMENTAL_DATA_REQUIREMENTS.md; NOT selected until the compliance table is complete.",
        ],
    },
    {
        "dataset_id": "chen2020-validation-discharge-relaxation",
        "title": "Chen et al. 2020 validation data (C/2, 1C, 1.5C discharge + relaxation, 3 cells, 25 degC)",
        "source_url": "https://iopscience.iop.org/article/10.1149/1945-7111/ab9050",
        "doi_or_identifier": "10.1149/1945-7111/ab9050",
        "license": "article CC BY-NC-ND 4.0 (verified on the article page)",
        "chemistry": "LG M50 (graphite-SiOx / NMC 811)",
        "cell_format": "21700 cylindrical (three cells for validation)",
        "nominal_capacity": "5 A.h",
        "temperature": "25 degC chamber (verified in article text)",
        "c_rates": "C/2, 1C, 1.5C discharge after C/3 CC-CV charge (verified in article text)",
        "voltage_limits": "2.5-4.2 V (verified in article text)",
        "protocol": "CC-CV charge, CC discharge, 2 h rests; relaxation included (paper stresses its importance)",
        "metadata_completeness": "protocol documented in the paper; raw trace deposit status UNRESOLVED",
        "observations": "Data availability statement (verified quote): the parameter set and measured OCVs are in PyBaMM; the experimental validation traces' deposit status is NOT stated -> UNRESOLVED",
        "requirements": [
            {"requirement": "cell identity matches LG M50 / Chen2020 scope", "observed": "exact demonstrator cell", "status": "met", "evidence": "article text"},
            {"requirement": "0.5C/1C/2C discharge protocol", "observed": "C/2, 1C, 1.5C (matches validation windows modulo naming)", "status": "met", "evidence": "article text"},
            {"requirement": "raw observations available", "observed": "UNRESOLVED", "status": "unknown", "evidence": "Data availability section does not state a raw-trace deposit"},
        ],
        "verdict": "CANDIDATE",
        "notes": [
            f"Web-researched candidate (retrieved {RETRIEVED}); would be the ideal validation set if raw traces can be obtained from the authors or supplementary material (stacks.iop.org/JES/167/080534/mmedia).",
        ],
    },
    {
        "dataset_id": "battery-archive-lg-m50",
        "title": "BatteryArchive.org LG M50 cycling records (if present)",
        "source_url": "https://www.batteryarchive.org/",
        "doi_or_identifier": "site based on https://github.com/battery-lcf",
        "license": "UNRESOLVED (per-record terms)",
        "chemistry": "UNRESOLVED",
        "cell_format": "UNRESOLVED",
        "nominal_capacity": "UNRESOLVED",
        "temperature": "UNRESOLVED",
        "c_rates": "UNRESOLVED",
        "voltage_limits": "UNRESOLVED",
        "protocol": "UNRESOLVED",
        "metadata_completeness": "UNRESOLVED (site indexes are JavaScript-rendered; not statically verifiable)",
        "observations": "UNRESOLVED",
        "requirements": [],
        "verdict": "UNRESOLVED",
        "notes": [
            f"Checked {RETRIEVED}: batteryarchive.org serves a JavaScript-driven index (data.html/list.html return a static shell); no LG M50 entry could be verified automatically.",
            "Requires manual browser verification against docs/EXPERIMENTAL_DATA_REQUIREMENTS.md before consideration.",
        ],
    },
]


def main() -> int:
    neware = audit_neware_sample(REPO_ROOT / "data/external/pyprobe_sample/neware")
    payload = {
        "generated": RETRIEVED,
        "purpose": (
            "P3 Part F dataset audit: candidate datasets for LG M50 experimental "
            "validation. NO dataset is selected here (selection requires a complete "
            "compliance table + user decision)."
        ),
        "candidates": [neware.to_dict()] + WEB_CANDIDATES,
    }
    out = REPO_ROOT / "data/registry/dataset_candidates.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"wrote {out} with {len(payload['candidates'])} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
