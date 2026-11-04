#!/usr/bin/env python
"""Run the P0 baseline DFN simulation from a YAML config.

Usage:
    python scripts/run_baseline.py --config configs/baseline_dfn.yaml --out results/baseline

Writes solution arrays, parameter snapshot, extraction metadata and the
reproducibility manifest. Does not create figures (see scripts/plot_baseline.py).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pybamm_closed_loop.pybamm_engine import BaselineRunConfig, run, save_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to run config YAML")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    config = BaselineRunConfig.from_yaml(args.config)
    print(f"run_id            : {config.run_id}")
    print(f"pybamm pinned     : {config.pybamm.required_version}")
    print(f"model             : {config.pybamm.model.family}.{config.pybamm.model.name}")
    print(f"parameter set     : {config.pybamm.parameter_set}")
    print(f"solver            : {config.pybamm.solver.name} "
          f"(rtol={config.pybamm.solver.rtol:g}, atol={config.pybamm.solver.atol:g})")
    print(f"experiment steps  : {config.experiment.steps}")

    result = run(config)
    paths = save_result(result, args.out)

    summary = result.manifest["solution_summary"]
    print(f"termination       : {summary['termination']}")
    print(f"simulated span    : {summary['t_start_s']:.1f} -> {summary['t_end_s']:.1f} s "
          f"({summary['n_steps']} points)")
    avail = result.extraction.availability_report
    print(f"series extracted  : {len(avail['series_extracted'])}, "
          f"unavailable: {avail['series_unavailable'] or 'none'}")
    print(f"profiles extracted: {len(avail['profiles_extracted'])}, "
          f"unavailable: {avail['profiles_unavailable'] or 'none'}")
    for key, path in paths.items():
        print(f"{key:17s}: {path}")

    if avail["series_unavailable"] or avail["profiles_unavailable"]:
        print("NOTE: some requested variables were not available in the model "
              "and were NOT fabricated (recorded in extraction_metadata.json).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
