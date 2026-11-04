# Development Roadmap

Phased plan from the project PRD. The order is deliberate: prove the physics
and numerical workflow before adding LLM complexity. Each phase requires an
explicit user assignment before work starts.

| Phase | Work | Deliverable / exit criterion | Status |
|---|---|---|---|
| P0 — Baseline | Pin PyBaMM; run a verified DFN parameter set; reproduce voltage output | Working baseline simulation + environment manifest | ✅ done |
| P1 — Parameter registry | Schema, status categories, unit representation, provenance storage | Validated parameter records with round-trip export | ⬜ |
| P2 — Synthetic generator | Controlled synthetic observations from known parameter sets | Reproducible dataset with ground truth and noise settings | ⬜ |
| P3 — Inverse estimation | Fit 2–3 selected parameters with bounds and multiple initial guesses | Recovery benchmark with error and convergence report | ⬜ |
| P4 — Identifiability/UQ | Sensitivity, correlation, uncertainty diagnostics | Report of which parameters are/are not constrained | ⬜ |
| P5 — Experimental validation | Calibrate on one subset, test on held-out published data | Held-out prediction report and limitations | ⬜ |
| P6 — Literature extraction | Corpus ingestion, retrieval, evidence extraction | Expert-reviewed extraction benchmark | ⬜ |
| P7 — Closed-loop orchestration | Discrepancy diagnosis → targeted retrieval → controlled reruns | Auditable end-to-end closed-loop demonstration | ⬜ |
| P8 — Fine-tuning study | Dataset, fine-tune eligible model, compare A/B/C/D conditions | Ablation report (needs GPU/remote compute; see risks) | ⬜ |

## P0 completion notes (2026-11-04)

- PyBaMM pinned at **26.8.0.0** in `.venv` (proven on this machine; also the
  version already used in `cycling_aging_feedback`).
- Solver: **IDAKLU** (`pybamm.IDAKLUSolver`, rtol=atol=1e-6). Note:
  `pybamm.CasadiSolver` is deprecated in 26.8 and is ~100× slower for this
  problem (42 s vs 0.4 s wall time for the full discharge).
- Parameter set: **Chen2020** (commercial LG M50, 5 A.h).
- Full 1C discharge to 2.5 V: t ≈ 3555 s, ≈ 4.94 A.h, event-terminated.
- Tests: 23 passed (13 unit + 10 integration).
- Artifacts: `results/baseline/` (arrays, manifest, parameter snapshot,
  extraction metadata), `results/figures/` (3 figures).

## Open scientific decisions (from PRD §15)

1. First demonstrator chemistry/cell: Chen2020 chosen for P0; revisit before P3.
2. Which 2–3 parameters to estimate in P3 (scientific rationale required).
3. Which observables/conditions identify those parameters.
4. Which public experimental dataset (P5) has adequate metadata and protocol.
5. Literature corpus licensing for ingestion/training (P6).
6. Fine-tuning feasibility: open-weight model + license + compute (P8) —
   local machine is CPU-only, so this likely needs a remote runtime.

## Known risks

| Risk | Status |
|---|---|
| No GPU on dev machine | P8 fine-tuning likely needs remote compute |
| PyBaMM API drift | Mitigated: version pin enforced at runtime + integration tests |
| PyBaMM 26.8 deprecations | CasadiSolver deprecated → IDAKLU adopted |
| Python 3.14 ecosystem gaps | PyBaMM/NumPy/SciPy stack verified working |
