#!/usr/bin/env python
"""Compatibility experiment 4: PyProBE ingestion and processing of sample data.

Question: can PyProBE ingest and process an example experimental dataset?

Uses the upstream PyProBE sample Neware dataset (tests/sample_data/neware)
downloaded to data/external/pyprobe_sample/ (not committed).

Run with: .venv-ecosystem312/bin/python scripts/compat_probe/exp4_pyprobe_ingest.py
(Python 3.12 required: PyProBE-Data declares Requires-Python >=3.11,<3.13.)
"""

from __future__ import annotations

from pathlib import Path

import pyprobe

DATA_DIR = Path(__file__).resolve().parents[2] / "data/external/pyprobe_sample/neware"


def main() -> int:
    print(f"pyprobe {getattr(pyprobe, '__version__', '?')}")

    info = {
        "Name": "Sample cell",
        "Chemistry": "NMC622",
        "Nominal Capacity [Ah]": 0.04,
        "Cycler number": 1,
        "Channel number": 1,
    }
    cell = pyprobe.Cell(info=info)
    cell.import_from_cycler(
        procedure_name="Sample",
        cycler="neware",
        input_data_path=str(DATA_DIR / "sample_data_neware.xlsx"),
        readme_path=str(DATA_DIR / "README.yaml"),
    )
    print("procedures:", list(cell.procedure.keys()))

    procedure = cell.procedure["Sample"]
    print("experiments:", procedure.experiment_names)
    print("pybamm experiment strings:", procedure.pybamm_experiment)

    break_in = procedure.experiment("Break-in Cycles")
    cycle3 = break_in.cycle(2)  # zero-indexed: third cycle
    discharge = cycle3.discharge()

    # API: .data is a property returning a polars DataFrame; .get() returns numpy
    df = discharge.data
    print(f"discharge rows: {df.height}, columns: {df.columns}")
    voltage, current, time = discharge.get("Voltage [V]", "Current [A]", "Time [s]")
    print(f"arrays: t {time.shape}, V {voltage.shape} ({voltage.min():.3f}..{voltage.max():.3f} V), "
          f"I {current.shape} ({current.min():.4f}..{current.max():.4f} A)")

    # pandas conversion (bridge to PyBOP/others)
    pdf = discharge.df.to_pandas()
    print(f"pandas conversion OK: {type(pdf).__name__} {pdf.shape}")

    # Cycle summary helper (API finding: pyprobe.analysis is a submodule and is
    # not re-exported at the package root - import it explicitly)
    from pyprobe.analysis import cycling

    summary = cycling.summary(procedure)
    print("cycle summary columns:", summary.data.columns)

    assert voltage.size > 0 and abs(current).max() > 0
    print("EXP4 RESULT: PyProBE ingested and filtered cycler data. PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
