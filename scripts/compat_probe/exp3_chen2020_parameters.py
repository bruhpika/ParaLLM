#!/usr/bin/env python
"""Compatibility experiment 3: Chen2020 parameter-set usage under PyBOP.

Question: can the existing Chen2020 parameter set be used appropriately,
i.e. does pybop.Parameter update/inference interact correctly with the
PyBaMM ParameterValues we already use in P0?

Run with: .venv-ecosystem/bin/python scripts/compat_probe/exp3_chen2020_parameters.py
"""

from __future__ import annotations

import numpy as np

import pybamm
import pybop


def main() -> int:
    pv = pybamm.ParameterValues("Chen2020")
    before_neg = pv["Negative electrode active material volume fraction"]
    before_pos = pv["Positive electrode active material volume fraction"]
    before_capacity = pv["Nominal cell capacity [A.h]"]
    print(f"Chen2020 initial: neg eps={before_neg}, pos eps={before_pos}, Q={before_capacity} A.h")

    # Literature status check: every key we touch must already exist in Chen2020
    for key in ["Negative electrode active material volume fraction",
                "Positive electrode active material volume fraction"]:
        assert key in pv.keys(), f"{key} not a Chen2020 parameter"

    # API finding: transformations are distribution-dependent (verified in
    # pybop/parameters/distributions.py _transform tables): LogTransformation
    # is implemented only for LogNormal and LogUniform; ScaledTransformation for
    # Gaussian/Uniform/LogUniform. Any other pairing raises TypeError.
    pv.update(
        {
            "Negative electrode active material volume fraction": pybop.Parameter(
                distribution=pybop.Gaussian(before_neg, 0.05)
            ),
            "Positive electrode active material volume fraction": pybop.Parameter(
                distribution=pybop.LogUniform(0.4, 0.8),
                transformation=pybop.LogTransformation(),
            ),
        }
    )

    # Non-fitted Chen2020 values must be untouched (no silent substitution)
    assert pv["Nominal cell capacity [A.h]"] == before_capacity
    assert pv["Maximum concentration in negative electrode [mol.m-3]"] == 33133.0
    assert pv["Lower voltage cut-off [V]"] == 2.5

    # Parameter objects expose distributions/bounds as documented
    p_neg = pv["Negative electrode active material volume fraction"]
    p_pos = pv["Positive electrode active material volume fraction"]
    print("neg param type:", type(p_neg).__name__, "| dist:", type(p_neg.distribution).__name__)
    print("pos param type:", type(p_pos).__name__, "| bounds:", p_pos.bounds,
          "| transform:", type(p_pos.transformation).__name__)

    # API finding: a raw pybamm.Simulation CANNOT process a ParameterValues
    # containing pybop.Parameter objects (NotImplementedError during
    # process_model). Fitting declarations must run through
    # pybop.pybamm.Simulator, which substitutes values before the PyBaMM build.
    model = pybamm.lithium_ion.SPM()
    t_eval = np.linspace(0, 100, 5)
    simulator = pybop.pybamm.Simulator(model, parameter_values=pv, protocol=t_eval)
    # API finding: pybop Simulator.solve() requires explicit inputs (dict of
    # fitted-parameter name -> value); it will not fall back to initial values.
    inputs = {
        "Negative electrode active material volume fraction": before_neg,
        "Positive electrode active material volume fraction": before_pos,
    }
    sol = simulator.solve(inputs)
    v = sol["Terminal voltage [V]"](t_eval)
    assert np.all(np.isfinite(v)), "simulation with pybop.Parameters produced non-finite voltage"
    print(f"simulation via pybop.pybamm.Simulator OK (V: {v[0]:.4f} -> {v[-1]:.4f})")

    print("EXP3 RESULT: Chen2020 + pybop.Parameter declarations work correctly. PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
