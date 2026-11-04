# Recovery benchmark: recovery_volume_fractions_multi_0p5_1_2C

- conditions: 0.5C, 1C, 2C
- noise sigma: 0.002 V | seed: 20261104
- cost: SumSquaredError | optimiser: L-BFGS-B (maxiter=100, jac=True)

| start | parameter | initial | estimate | truth | abs err |
|---|---|---|---|---|---|
| 0 | Negative electrode active material volume fraction | 0.620 | 0.74211 | 0.75000 | 0.00789 |
| 0 | Positive electrode active material volume fraction | 0.550 | 0.66828 | 0.66500 | 0.00328 |
| 1 | Negative electrode active material volume fraction | 0.850 | 0.74211 | 0.75000 | 0.00789 |
| 1 | Positive electrode active material volume fraction | 0.600 | 0.66828 | 0.66500 | 0.00328 |
| 2 | Negative electrode active material volume fraction | 0.700 | 0.74211 | 0.75000 | 0.00789 |
| 2 | Positive electrode active material volume fraction | 0.750 | 0.66828 | 0.66500 | 0.00328 |

Best start: 2 (final cost 7.357794e-04)
