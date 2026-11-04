#!/usr/bin/env python
"""Compatibility experiment 1: PyBOP wrapping a PyBaMM DFN with our P0 baseline config.

Question: can PyBOP use a PyBaMM model with our selected baseline configuration
(DFN + Chen2020 + IDAKLU)?

Run with: .venv-ecosystem/bin/python scripts/compat_probe/exp1_pybop_dfn_baseline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import pybamm
import pybop


def main() -> int:
    print(f"pybamm {pybamm.__version__} | pybop {getattr(pybop, '__version__', '?')}")
    # P0 baseline configuration: DFN + Chen2020 + IDAKLU (fixed-duration step:
    # pybop's Simulator removes voltage events by default, so event-terminated
    # protocols are not suitable for fitting workflows).
    model = pybamm.lithium_ion.DFN()
    parameter_values = pybamm.ParameterValues("Chen2020")
    solver = pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6)

    t_eval = np.linspace(0, 300, 60)
    solution = pybamm.Simulation(model, parameter_values=parameter_values, solver=solver).solve(
        t_eval=t_eval
    )
    print(f"forward solve OK: V {solution['Terminal voltage [V]'](t_eval)[0]:.4f} -> "
          f"{solution['Terminal voltage [V]'](t_eval)[-1]:.4f}")

    dataset = pybop.Dataset(
        {
            "Time [s]": t_eval,
            "Current [A]": solution["Current [A]"](t_eval),
            "Voltage [V]": solution["Terminal voltage [V]"](t_eval),
        }
    )
    print(f"pybop.Dataset OK: {dataset.check()}")

    # Fitted parameters must be declared as pybop.Parameter objects (API finding:
    # Problem.parameters is built only from declared fitting parameters; without
    # at least one, evaluation raises AttributeError in get_bounds_array()).
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
    simulator = pybop.pybamm.Simulator(
        model, parameter_values=parameter_values, protocol=dataset, solver=solver
    )
    cost = pybop.SumSquaredError(dataset)
    problem = pybop.Problem(simulator, cost)

    # API finding: Parameters.names is populated as a list attribute at runtime
    # (shadowing the method of the same name) - use it as a property.
    print("problem parameter names:", problem.parameters.names)
    print("bounds:\n", problem.parameters.get_bounds_array())

    # Evaluate at the true parameter values (data generated without noise from
    # the same model, so the cost must be finite and near zero).
    # Chen2020 ground truth (verified against the installed parameter set):
    truth = np.array([0.75, 0.665])
    evaluation = problem.evaluate(truth, calculate_sensitivities=True)
    # API finding: evaluate() returns pybop.costs.evaluation.Evaluation with
    # .values (ndarray) and .sensitivities (dict), not scalar accessors.
    cost_val = float(np.asarray(evaluation.values).reshape(-1)[0])
    print(f"cost at truth: {cost_val:.6e}")
    sens = evaluation.sensitivities
    print(f"sensitivities: { {k: np.shape(v) for k, v in sens.items()} }")
    assert np.isfinite(cost_val), "cost must be finite"
    print("EXP1 RESULT: PyBOP can wrap our DFN + Chen2020 baseline configuration. PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
