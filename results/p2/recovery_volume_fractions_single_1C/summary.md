# Recovery benchmark: recovery_volume_fractions_single_1C

- conditions: 1C
- noise sigma: 0.002 V | seed: 20261104
- cost: SumSquaredError | optimiser: L-BFGS-B (maxiter=100, jac=True)

| start | parameter | initial | estimate | truth | abs err |
|---|---|---|---|---|---|
| 0 | Negative electrode active material volume fraction | 0.620 | 0.74116 | 0.75000 | 0.00884 |
| 0 | Positive electrode active material volume fraction | 0.550 | 0.66939 | 0.66500 | 0.00439 |
| 1 | Negative electrode active material volume fraction | 0.850 | 0.74116 | 0.75000 | 0.00884 |
| 1 | Positive electrode active material volume fraction | 0.600 | 0.66939 | 0.66500 | 0.00439 |
| 2 | Negative electrode active material volume fraction | 0.700 | 0.74116 | 0.75000 | 0.00884 |
| 2 | Positive electrode active material volume fraction | 0.750 | 0.66939 | 0.66500 | 0.00439 |

Best start: 1 (final cost 2.402859e-04)
