#!/usr/bin/env python
"""Generate baseline figures from saved run output.

Usage:
    python scripts/plot_baseline.py --results results/baseline --figures results/figures

Reads solution_arrays.npz and extraction_metadata.json written by
scripts/run_baseline.py; produces voltage/current, concentration and
electrode-potential figures.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pybamm_closed_loop.reporting.figures import generate_all_figures
from pybamm_closed_loop.pybamm_engine.outputs import ProfileResult


def load_results(results_dir: Path) -> tuple[dict, dict]:
    """Load the series arrays and profile objects saved by run_baseline.py.

    Returns ``(series, profiles)``: series are the keyed arrays from
    ``solution_arrays.npz`` (times in seconds, matched by key suffix);
    profiles carry coordinates (metres), coordinates times (seconds) and
    values; profiles missing coordinate or value arrays are skipped.
    """
    npz = np.load(results_dir / "solution_arrays.npz")
    meta = json.loads((results_dir / "extraction_metadata.json").read_text())

    series = {}
    profiles = {}
    for key in npz.files:
        if key.startswith("series__"):
            series[key[len("series__"):]] = npz[key]

    for name, prof_meta in meta.get("profiles", {}).items():
        coords = npz.get(f"profile__{name}__coords")
        times = npz.get(f"profile__{name}__times")
        values = npz.get(f"profile__{name}__values")
        if coords is None or values is None:
            continue
        profiles[name] = ProfileResult(
            variable=name,
            coordinate_name=prof_meta.get("coordinate_name", "x [m]"),
            times_s=list(times) if times is not None else [],
            coordinates=coords,
            values=values,
            note=prof_meta.get("note", ""),
            metadata=prof_meta.get("metadata", {}),
        )
    return series, profiles


def main() -> int:
    """Render baseline figures from the saved run output (CLI entry)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, help="Directory written by run_baseline.py")
    parser.add_argument("--figures", required=True, help="Directory for PNG figures")
    args = parser.parse_args()

    results_dir = Path(args.results)
    series, profiles = load_results(results_dir)
    written = generate_all_figures(series, profiles, args.figures)
    for path in written:
        print(f"wrote {path}")
    if not written:
        print("no figures produced (no plottable variables found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
