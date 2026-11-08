#!/usr/bin/env python
"""Compatibility experiment 2: PyBOP optimizing selected parameters of a DFN model.

Question: can PyBOP optimize selected parameters of a DFN model using the
Chen2020 parameter set?

Fit the two electrode active-material volume fractions (the canonical PyBOP
example pair) to synthetic noisy data generated with the true Chen2020 values.

Run with: .venv-ecosystem/bin/python scripts/compat_probe/exp2_pybop_dfn_optimization.py
"""

from __future__ import annotations


import numpy as np

import pybamm
import pybop


def main() -> int:
    print(f"pybamm {pybamm.__version__} | pybop {getattr(pybop, '__version__', '?')}")
    rng_seed = 20261104
    np.random.seed(rng_seed)

    model = pybamm.lithium_ion.DFN()
    parameter_values = pybamm.ParameterValues("Chen2020")
    solver = pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6)

    # Synthetic observations from the true parameter values (P2-style ground truth)
    t_eval = np.linspace(0, 300, 40)
    solution = pybamm.Simulation(model, parameter_values=parameter_values, solver=solver).solve(
        t_eval=t_eval
    )
    sigma = 2e-3
    dataset = pybop.Dataset(
        {
            "Time [s]": t_eval,
            "Current [A]": solution["Current [A]"](t_eval),
            "Voltage [V]": pybop.add_noise(solution["Terminal voltage [V]"](t_eval), sigma),
        }
    )

    true_values = {
        "Negative electrode active material volume fraction":
            parameter_values["Negative electrode active material volume fraction"],
        "Positive electrode active material volume fraction":
            parameter_values["Positive electrode active material volume fraction"],
    }
    print("true values:", true_values)

    # Declare fitted parameters with explicit bounds (independent of any LLM)
    parameter_values.update(
        {
            "Negative electrode active material volume fraction": pybop.Parameter(
                bounds=(0.5, 0.9), initial_value=0.60
            ),
            "Positive electrode active material volume fraction": pybop.Parameter(
                bounds=(0.4, 0.8), initial_value=0.55
            ),
        }
    )

    simulator = pybop.pybamm.Simulator(
        model, parameter_values=parameter_values, protocol=dataset, solver=solver
    )
    cost = pybop.SumSquaredError(dataset)
    problem = pybop.Problem(simulator, cost)

    options = pybop.SciPyMinimizeOptions(maxiter=30, method="L-BFGS-B", jac=True)
    optim = pybop.SciPyMinimize(problem, options=options)
    result = optim.run()

    x = np.asarray(result.x, dtype=float)
    print("initial guess :", [0.60, 0.55])
    print("recovered     :", x)
    print("true          :", [true_values["Negative electrode active material volume fraction"],
                              true_values["Positive electrode active material volume fraction"]])
    print("abs error     :", np.abs(x - np.array(list(true_values.values()))))
    # API finding: Result.cost is a per-iteration list attribute (not a method);
    # best_cost holds the final value.
    print("final cost    :", result.best_cost)
    print(f"seed recorded : {rng_seed} (numpy RNG; SciPyMinimize has no seed option)")

    assert np.all(np.isfinite(x)), "optimiser returned non-finite values"
    print("EXP2 RESULT: PyBOP optimised DFN parameters end-to-end. PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
