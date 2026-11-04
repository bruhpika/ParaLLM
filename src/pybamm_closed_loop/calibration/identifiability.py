"""Identifiability diagnostics complementary to PyBOP.

PyBOP 26.10 provides only a 2-parameter Hessian classifier
(pybop.classify_using_hessian; its FIM was removed in v25.10). The functions
here add: finite-difference sensitivity/FIM diagnostics (any N), parameter
correlation from the FIM, coarse profile likelihood and parametric bootstrap,
plus a SALib Sobol wrapper.

Golden rule (scientific rule 7): optimiser convergence never demonstrates
identifiability. These tools quantify sensitivity, correlation and parameter
interference so that claims can be worded honestly.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


def finite_difference_jacobian(
    predict: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    rel_step: float = 1e-2,
    bounds: np.ndarray | None = None,
) -> np.ndarray:
    """Central finite-difference Jacobian of a vector-valued model.

    predict maps parameter vector -> 1D observation vector.
    bounds: optional (n,2) array to keep perturbations feasible.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    y0 = np.asarray(predict(x), dtype=float).reshape(-1)
    jac = np.zeros((y0.size, n))
    for j in range(n):
        step = rel_step * max(abs(x[j]), 1e-12)
        xp, xm = x.copy(), x.copy()
        xp[j] += step
        xm[j] -= step
        if bounds is not None:
            lo, hi = bounds[j]
            xp[j] = min(xp[j], hi)
            xm[j] = max(xm[j], lo)
            step = (xp[j] - xm[j]) / 2.0
        if step == 0:
            continue
        yp = np.asarray(predict(xp), dtype=float).reshape(-1)
        ym = np.asarray(predict(xm), dtype=float).reshape(-1)
        jac[:, j] = (yp - ym) / (2.0 * step)
    return jac


def normalized_sensitivity(jacobian: np.ndarray, x: np.ndarray,
                           y_scale: float) -> np.ndarray:
    """Dimensionless sensitivity S_ij = (x_j / y_scale) * d y_i / d x_j."""
    return jacobian * (np.asarray(x, dtype=float) / y_scale)[None, :]


def fim_diagnostics(jacobian: np.ndarray, sigma: float) -> dict[str, Any]:
    """Fisher-information diagnostics from a Jacobian and i.i.d. noise sigma.

    Returns FIM, parameter correlation (from pseudo-inverse covariance),
    eigenvalues and condition number. A large condition number or |corr| -> 1
    indicates the observations cannot separate the parameters well.
    """
    jac = np.asarray(jacobian, dtype=float)
    w = 1.0 / (sigma ** 2)
    fim = w * (jac.T @ jac)
    eigvals, eigvecs = np.linalg.eigh(fim)
    cov = np.linalg.pinv(fim)
    d = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = cov / np.outer(d, d)
    nonzero = eigvals[eigvals > 0]
    if nonzero.size and nonzero.size < fim.shape[0]:
        # Rank-deficient FIM: parameters are not jointly constrained
        cond = float("inf")
    elif nonzero.size:
        cond = float(nonzero.max() / nonzero.min())
    else:
        cond = float("inf")
    return {
        "fim": fim,
        "covariance": cov,
        "correlation": np.nan_to_num(corr, nan=0.0),
        "eigenvalues": eigvals,
        "eigenvectors": eigvecs,
        "condition_number": cond,
    }


def profile_likelihood(
    make_problem: Callable[[dict[str, float]], Any],
    run_fit_fn: Callable[..., dict[str, Any]],
    fixed_param: str,
    grid: np.ndarray,
    free_param: str,
    free_bounds: tuple[float, float],
    free_initial: float,
) -> dict[str, Any]:
    """Coarse profile likelihood for a 2-parameter problem.

    For each grid value of `fixed_param`, re-optimise `free_param` and record
    the best cost. make_problem(fixed_values) must return a fresh problem with
    the fixed parameter pinned; run_fit_fn is called on the free parameter.
    """
    costs, free_estimates = [], []
    for val in np.asarray(grid, dtype=float):
        problem = make_problem({fixed_param: float(val)})
        rep = run_fit_fn(problem, free_param, free_bounds, free_initial)
        costs.append(float(rep["final_cost"]))
        free_estimates.append(float(rep["estimate"]))
    return {
        "fixed_param": fixed_param,
        "free_param": free_param,
        "grid": np.asarray(grid, dtype=float).tolist(),
        "costs": costs,
        "free_estimates": free_estimates,
    }


def parametric_bootstrap(
    refit: Callable[[int], dict[str, Any]],
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """Parametric bootstrap over a refit callable.

    refit(replicate_index) must regenerate noisy data (seeded by the index),
    refit, and return {"estimates": {name: value}, "final_cost": float}.
    """
    reps = [refit(int(i)) for i in range(n_boot)]
    names = sorted(reps[0]["estimates"])
    est = np.array([[r["estimates"][n] for n in names] for r in reps], dtype=float)
    return {
        "names": names,
        "estimates": est.tolist(),
        "mean": est.mean(axis=0).tolist(),
        "std": est.std(axis=0, ddof=1).tolist() if n_boot > 1 else [0.0] * len(names),
        "bias_note": "compare mean to the data-generating truth in the caller",
        "n_boot": n_boot,
        "bootstrap_seed": seed,
    }


def sobol_indices(
    model_fn: Callable[[np.ndarray], np.ndarray],
    bounds: np.ndarray,
    param_names: list[str],
    n_samples: int = 64,
    seed: int = 0,
) -> dict[str, Any]:
    """Sobol sensitivity indices (SALib Saltelli) for a vector-valued model.

    model_fn maps parameter vector -> 1D observation vector; indices are
    computed per observation component (e.g. per time point).
    """
    from SALib.sample import saltelli
    from SALib.analyze import sobol

    problem = {
        "num_vars": len(param_names),
        "names": list(param_names),
        "bounds": np.asarray(bounds, dtype=float).tolist(),
    }
    np.random.seed(seed)
    param_values = saltelli.sample(problem, n_samples, calc_second_order=False)
    y = np.vstack([np.asarray(model_fn(p), dtype=float).reshape(-1) for p in param_values])
    n_obs = y.shape[1]
    s1 = np.zeros((n_obs, len(param_names)))
    st = np.zeros((n_obs, len(param_names)))
    for k in range(n_obs):
        si = sobol.analyze(problem, y[:, k], calc_second_order=False, print_to_console=False)
        s1[k] = si["S1"]
        st[k] = si["ST"]
    return {
        "names": param_names,
        "n_samples": n_samples,
        "seed": seed,
        "n_model_evals": int(param_values.shape[0]),
        "S1": s1,
        "ST": st,
    }


def hessian_classification(result: Any) -> dict[str, Any]:
    """Wrap pybop.classify_using_hessian (valid for exactly 2 parameters)."""
    import pybop

    out = pybop.classify_using_hessian(result)
    # Return a numpy-serialisable subset (the raw dict holds arrays). FD Hessians
    # can be slightly non-symmetric -> eigenvalues may carry tiny imaginary parts.
    return {
        "message": out.get("message"),
        "eigenvalues": np.real(np.asarray(out.get("eigenvalues"))).astype(float).tolist(),
        "eigenvectors": np.real(np.asarray(out.get("eigenvectors"))).astype(float).tolist(),
        "stationarity_confirmed": bool(out.get("stationarity_confirmed")),
        "names": list(out.get("names", [])),
        "best_cost": float(out.get("best_cost", float("nan"))),
    }
