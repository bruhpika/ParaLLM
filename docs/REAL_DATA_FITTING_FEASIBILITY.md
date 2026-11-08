# P4 — Real-data fitting feasibility assessment (Part E)

**Conclusion: no fitting was performed in P4, and the assessment recommends
against fitting on the currently available data until the license and
protocol gaps are resolved.**

## What we have

- Genuine LG M50 cell data (PyProBE sample, audited —
  `EXPERIMENTAL_DATA_AUDIT.md`): one C/10 pOCV cycle (discharge 4.814 Ah,
  charge 4.732 Ah), CC-CV charge to 100% SOC, rests, 24–32 °C range.
- Licenses/permissions: dataset license UNRESOLVED; Chen2020 raw
  validation traces UNRESOLVED (author-request path only).

## Feasibility blocks, in order of severity

1. **Protocol mismatch with the P2 campaign.** P2's estimation protocols
   (0.5C/1C/2C discharge recovery, ridge/multistart, MCMC) were designed
   for multi-rate discharge data. The real dataset has exactly one rate
   (C/10). Single-rate terminal-voltage fitting cannot separate
   diffusivity/kinetic contributions that were only marginally identified
   in the synthetic study.
2. **Observability collapse at C/10.** P2 measured that negative particle
   diffusivity is unobservable at ≤2C (|S| < 0.05); C/10 is worse. The
   parameters most safely estimable from this dataset are effective
   capacity, OCV shape, and (weakly) diffusivity ratios — all of which are
   already fixed by the Chen2020 parameter set within a few percent.
3. **Initial-condition ambiguity.** The dataset starts pre-charged
   (3.62 V entering rest, 32.3 °C residual heat). Simulation-from-step-4
   (post CC-CV, 2 h rest) is well-defined and is the only clean initial
   condition; anything earlier carries float/thermal history from outside
   the file.
4. **Isothermal assumption.** C/10 segments are near-isothermal (≤2.8 K
   drift); a P0 isothermal fit is defensible for those segments but should
   not touch the CC-CV temperature-rising section.
5. **Validation impossibility.** With no multi-rate traces there is no
   held-out experimental condition for validation. Calibrating on this
   dataset would, again, be self-validation (AGENTS.md rule 9).

## What CAN be responsibly done next (proposals, not commitments)

- Resolve the sample dataset license (README/catalog inspection or
  Imperial/NDK contact) before any external use.
- Author-request for Chen2020 validation traces; if obtained, re-run the P2
  multi-rate recovery using REAL voltage data as the observation set — the
  P2 harness exists and is reusable.
- OCV-curve extraction from the C/10 pOCV discharge (relaxation-corrected)
  for a registry cross-check of Chen2020's OCP functions (low value: the
  paper's OCPs come from half-cell measurements; but a numeric
  consistency check is cheap and safe).

## Non-recommendations recorded explicitly

- Do NOT fit against the C/10-only profile and report parameter "recovery":
  a successful optimization would yet again not demonstrate identifiability
  (rule 7), and multi-rate rest effects make the single-fit output fragile.
- Do NOT use the calibration dataset as independent validation data
  (rule 9).
- Do NOT reduce P2's synthetic-only conclusions based on this dataset: the
  synthetic parameter recovery remains a synthetic-demonstration property,
  not an experimental validation (rule 8).
