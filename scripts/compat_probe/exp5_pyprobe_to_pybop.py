#!/usr/bin/env python
"""Compatibility experiment 5: PyProBE-processed data into a PyBOP workflow.

Question: can processed experimental data be passed into a PyBOP optimization
workflow?

SCIENTIFIC CAVEAT (read before interpreting any number from this script):
The upstream sample cell is a 40 mAh NMC622 commercial cell. Our baseline
parameter set (Chen2020) describes a 5 A.h LG M50 cell. They are NOT the same
cell or chemistry. Every model/data mismatch seen here is expected and
IRRELEVANT scientifically - this experiment verifies data plumbing only
(Dataset construction, cost evaluation, a few optimiser steps). No parameter
value produced here may be used or reported as an estimate.

Run with: .venv-ecosystem312/bin/python scripts/compat_probe/exp5_pyprobe_to_pybop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import pybamm
import pybop
import pyprobe

DATA_DIR = Path(__file__).resolve().parents[2] / "data/external/pyprobe_sample/neware"


def main() -> int:
    print(f"pybamm {pybamm.__version__} | pybop {getattr(pybop, '__version__', '?')} "
          f"| pyprobe {getattr(pyprobe, '__version__', '?')}")
    print("WARNING: interop smoke test only - sample cell (NMC622, 0.04 A.h) is "
          "NOT the Chen2020 LG M50 cell. No scientific claims from this run.")

    # --- PyProBE lane: ingest + filter (same as exp4) ---
    cell = pyprobe.Cell(info={"Name": "Sample cell", "Chemistry": "NMC622",
                              "Nominal Capacity [Ah]": 0.04})
    cell.import_from_cycler(
        procedure_name="Sample",
        cycler="neware",
        input_data_path=str(DATA_DIR / "sample_data_neware.xlsx"),
        readme_path=str(DATA_DIR / "README.yaml"),
    )
    discharge = cell.procedure["Sample"].experiment("Break-in Cycles").cycle(2).discharge()
    t, v, i = discharge.get("Time [s]", "Voltage [V]", "Current [A]")
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    i = np.asarray(i, dtype=float)
    t = t - t[0]  # relative time for the forward simulation
    print(f"PyProBE discharge arrays: {t.shape[0]} points, "
          f"V {v.min():.3f}..{v.max():.3f}, I {i.min():.4f}..{i.max():.4f}")

    # --- PyBOP lane: Dataset from processed arrays ---
    dataset = pybop.Dataset(
        {"Time [s]": t, "Current [A]": i, "Voltage [V]": v}
    )
    assert dataset.check(), "pybop.Dataset rejected PyProBE arrays"
    print("pybop.Dataset from PyProBE arrays: OK")

    # Placeholder model/params: documented mismatch, plumbing test only.
    model = pybamm.lithium_ion.SPM()
    parameter_values = pybamm.ParameterValues("Chen2020")
    parameter_values.update(
        {
            "Negative electrode active material volume fraction": pybop.Parameter(
                bounds=(0.5, 0.9)
            ),
            "Positive electrode active material volume fraction": pybop.Parameter(
                bounds=(0.4, 0.8)
            ),
        }
    )
    simulator = pybop.pybamm.Simulator(model, parameter_values=parameter_values,
                                       protocol=dataset)
    cost = pybop.SumSquaredError(dataset)
    problem = pybop.Problem(simulator, cost)

    inputs = {
        "Negative electrode active material volume fraction": 0.75,
        "Positive electrode active material volume fraction": 0.665,
    }
    evaluation = problem.evaluate(list(inputs.values()))
    cost_val = float(np.asarray(evaluation.values).reshape(-1)[0])
    print(f"cost of placeholder model vs sample-cell data: {cost_val:.4e} "
          f"(large is EXPECTED - different cell)")

    options = pybop.SciPyMinimizeOptions(maxiter=3, method="L-BFGS-B")
    optim = pybop.SciPyMinimize(problem, options=options)
    result = optim.run()
    print(f"3 optimiser steps completed, cost {result.best_cost:.4e} "
          f"(values deliberately NOT reported - mismatched cell)")

    assert np.isfinite(cost_val)
    print("EXP5 RESULT: PyProBE output flows into a PyBOP optimisation loop. PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
