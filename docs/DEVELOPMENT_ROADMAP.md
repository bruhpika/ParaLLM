# Development Roadmap

**Two vocabularies exist here — read this first.** The table below uses the
**PRD phase names** (P0…P8). The *shipped* work is tracked in the git history
and release notes as **milestones P0…P5** (v0.1 feature set), where "P2" means
"estimation & identifiability", not the PRD's "P2 synthetic generator". The
mapping is at the bottom of this file, and from v0.2 onward releases are
described as **v0.x feature sets** (PRD phase names are archived in
`docs/internal/`).

Current forward plan: **`docs/ROADMAP_V0.2.md`** (Parameter Assembly — proposal,
2026-11-08). Each phase requires an explicit user assignment before work starts.

| Phase | Work | Deliverable / exit criterion | Status |
|---|---|---|---|
| P0 — Baseline | Pin PyBaMM; run a verified DFN parameter set; reproduce voltage output | Working baseline simulation + environment manifest | ✅ done (milestone P0) |
| P1 — Parameter registry | Schema, status categories, unit representation, provenance storage | Validated parameter records with round-trip export | ✅ done (milestones P1/P3) |
| P2 — Synthetic generator | Controlled synthetic observations from known parameter sets | Reproducible dataset with ground truth and noise settings | ✅ done (milestone P2) |
| P3 — Inverse estimation | Fit 2–3 selected parameters with bounds and multiple initial guesses | Recovery benchmark with error and convergence report | ✅ done (milestone P2) |
| P4 — Identifiability/UQ | Sensitivity, correlation, uncertainty diagnostics | Report of which parameters are/are not constrained | ✅ done (milestone P2) |
| P5 — Experimental validation | Calibrate on one subset, test on held-out published data | Held-out prediction report and limitations | ⛔ **blocked** — no eligible dataset (license/protocol audit unresolved; see `docs/P5_DATA_ACQUISITION.md`) |
| P6 — Literature extraction | Corpus ingestion, retrieval, evidence extraction | Expert-reviewed extraction benchmark | ✅ done (milestones P3–P5) |
| P7 — Closed-loop orchestration | Discrepancy diagnosis → targeted retrieval → controlled reruns | Auditable end-to-end closed-loop demonstration | ⏳ planned as **V2.6** (parameter-targeted loop) |
| P8 — Fine-tuning study | Dataset, fine-tune eligible model, compare A/B/C/D conditions | Ablation report (needs GPU/remote compute; see risks) | 🔁 **replanned as P8′ = V2.5 evidence engineering** (no fine-tuning; decision D3) |

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
6. Fine-tuning feasibility: **closed** — replaced by P8′ evidence engineering
   (v0.2 decision D3: the bottleneck is evidence coverage and conditions, not
   model weights; no credible training corpus exists; a fine-tuned checkpoint is
   less auditable than a rubric plus deterministic checks).

## Decisions recorded 2026-11-08 (v0.2 planning; full table in `docs/ROADMAP_V0.2.md`)

| # | Decision | Rationale |
|---|---|---|
| D1 | Applicability rubric is **auditable and hand-set** (no learned weights in v0.2) | Determinism, reviewability, reproducibility; weights can be calibrated later against an expert-labelled set, with the rubric version recorded |
| D2 | **LG M50 / Chen2020 only** for v0.2 | Depth over breadth; multi-chemistry carried as TODO (v0.3+) |
| D3 | **No fine-tuning** (P8 → P8′ evidence engineering) | See decision 6 above |
| D4 | **No real-data-dependent claims** in v0.2 | Acquisition/licensing unresolved; LG M50 sample ineligible (C/10 pOCV, ~32.3 °C, license UNRESOLVED) |
| D5 | **Benchmarks stay private** (v4, v4a) | v3 is public → regression suite, not a held-out benchmark |
| D6 | **Human approval gate mandatory** | AGENTS.md rule 10; assembly is decision support, never autonomous writes |
| D7 | **LLM stays out of the numeric decision path** | Core identity; the clearest difference from the closest neighbour (`docs/POSITIONING.md`) |

## Known risks

| Risk | Status |
|---|---|
| No GPU on dev machine | moot for v0.2 (no fine-tuning planned); revisit only if D3's revisit condition is met |
| PyBaMM API drift | Mitigated: version pin enforced at runtime + integration tests |
| PyBaMM 26.8 deprecations | CasadiSolver deprecated → IDAKLU adopted |
| Python 3.14 ecosystem gaps | PyBaMM/NumPy/SciPy stack verified working |

## PRD phase → shipped milestone mapping (v0.1)

| PRD phase | shipped as | v0.2 status |
|---|---|---|
| P0 baseline | milestone P0 | done (v0.1) |
| P1 registry | milestones P1/P3 | done (v0.1) |
| P2 synthetic | milestone P2 | done (v0.1) |
| P3 inverse estimation | milestone P2 | done (v0.1) |
| P4 identifiability/UQ | milestone P2 | done (v0.1) |
| P5 experimental validation | — | **blocked** (D4) |
| P6 literature extraction | milestones P3–P5 | done (v0.1) |
| P7 closed loop | — | planned as V2.6 |
| P8 fine-tuning | — | replanned as P8′ = V2.5 |
