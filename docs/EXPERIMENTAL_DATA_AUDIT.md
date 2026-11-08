# P4 — Experimental data audit (Part D)

Artifact: `data/registry/dataset_audit_lgm50.json`, built read-only by
`scripts/p4/build_dataset_audit.py` from
`data/external/pyprobe_sample/lgm50/LGM50_BoL_RPT0_short_CA4.parquet` (81,661
rows × 7 cols) + its `README.yaml`. No experiment data was modified.

## What this dataset actually is

- Source: Imperial College London PyProBE sample data (`LGM50 … BoL …
  RPT0_short_CA4`, cell C, rig 3, 25 °C chamber), retrieved 2026-11-08
  (sha256 recorded in the artifact, 2,185,238 B).
- Protocol (README): Initial Charge (rest 2 min → CC 1.5 A → CV hold 4.2 V
  to 0.05 A → rest 2 h) + pOCV (rest 30 s → discharge 0.5 A to 2.5 V →
  rest 6 h → rest 30 s → charge 0.5 A to 4.2 V → rest 10 min).
- Step 0–9 observed semantics match the README order exactly (CC currents
  ±1.5/±0.5 A, CV plateau at 4.200 V, rest lengths), recorded per-step in
  the artifact; mapping treated as assumption until cross-checked with
  PyProBE's protocol parser.

## Key measurements (from the artifact, not restated by hand)

- Duration 30.06 h; sampling 10 s; no nulls.
- pOCV C/10 discharge (step 5): **4.8137 Ah**, 2.500–4.169 V, 9.6 h.
- pOCV C/10 charge (step 8): **4.7321 Ah** → CE ≈ 0.983 at C/10 without a
  final CV hold (intake-limited observation, not a health claim).
- Temperature: 24.0 °C rest/ambient; **32.3 °C during the 1.5 A CC charge**;
  C/10 segments stay 24.7–26.8 °C.
- Rest voltage noise: per-step σ from 0.0025 V (short rests) to 0.061 V (the
  6 h OCV relaxation step, σ dominated by relaxation drift, not sensor
  noise).

## Compatibility verdicts

- **Cell**: LG M50 21700 — the Chen2020 characterization target; voltage
  window 2.5–4.2 V matches the paper's chemistry.
- **Protocol coverage**: C/10 pOCV (discharge + charge) only. NO 0.5C/1C/2C
  validation traces, no pulse/HPPC, no GITT — nothing comparable to
  Chen2020's validation experiments.
- **P3 Neware sample stays excluded** (its P3 audit verdict is unchanged).
- **Non-isothermal**: the charge section violates isothermal assumptions;
  C/10 segments are near-isothermal with a small bias.
- **Licensing**: UNRESOLVED. Repo code is BSD-3-Clause; the sample dataset's
  redistribution conditions are unverified. No re-distribution beyond this
  sample is implied.
- **Chen2020 validation traces**: still UNRESOLVED — the paper's
  data-availability statement covers the parameter set and OCVs only;
  supplement (S1–S6) contains no raw traces. Remaining path: author request.

## Consequences for the project (see REAL_DATA_FITTING_FEASIBILITY.md)

No fitting was performed in P4 (per milestone scope). The audited dataset
can support OCV-curve extraction and C/10-only model checks but cannot
replicate the paper's multi-rate validation. Any use requires first
resolving the data license.
