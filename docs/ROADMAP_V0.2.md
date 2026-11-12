# PARALLM v0.2 Roadmap — "Parameter Assembly" (proposal, 2026-11-08)

Status: **proposal for approval.** No code has been written for v0.2 yet. This
document defines the intent, scope, exit criteria and risks; the milestone plan
follows the repository's incremental rule (work one milestone at a time, only
after explicit assignment).

Audience: **battery researchers already using PyBaMM/PyBOP** (the group that
actually has the parameter problem today).

---

## 1. Why v0.2 exists — the gap, stated honestly

v0.1 (P0–P5) delivers the *evidence pipeline*: ingest → retrieve → extract with
provenance → deterministic validation → provenance-tracked registry → synthetic
estimation/identifiability → literature benchmark with retrieval ablation. What
it does **not** deliver is the step a modeller actually needs next:

> **"Given literature, which value should *my* cell use, why, what were the
> alternatives, and which of these can I ever measure?"**

Today the project can tell you *what a paper says* (with a verified quote). It
cannot tell you *which paper applies to your cell*, cannot *resolve conflicts*,
and cannot *say which parameters your planned experiment can ever identify*.
Those are the missing ingredients, and they are where the differentiation lies
(competitive scan: `docs/POSITIONING.md`).

The v0.1 numbers that motivate this: value extraction 0.946, provenance 0.928,
false extraction 0.000 — but **condition completeness 0.116** and **no
independent experimental validation**. Conditions are not a cosmetic field;
without them a value cannot be matched to a target cell, which is exactly the
decision the next layer must make.

## 2. The core concept: the Parameter Assembly layer

For a **target cell + model + protocol**, assemble a defensible parameter set in
which every field carries evidence and a decision.

### 2.1 Per-parameter dossier (the artifact)

```
Negative particle diffusivity [m2.s-1]
  decision:       FIX at 3.3e-14  (do not fit)
  basis:          literature_derived — GITT, 25 °C, 50 % SOC | quote verified ✔ | doc+page recorded
  conflicts:      Laue 2021: 9.35e-15 (NMC111/graphite) → NOT APPLICABLE (chemistry ≠ target)
                  Chen2020 set: 3.3e-14 (tuned at 1C) → applicable, method differs (tuned vs measured)
  observability:  |S| = 0.011–0.048 over 0.5C–2C → UNOBSERVABLE under this protocol
  action:         fix at literature value; if accuracy needed, measure via GITT
  approvals:      [pending human sign-off]
```

### 2.2 Decision taxonomy (fixed set, no free-form invention)

| decision | meaning | typical trigger |
|---|---|---|
| `USE` | adopt this value for the target | applicability matches, best available evidence |
| `FIX` | adopt and hold constant (do not fit) | literature value + unobservable under protocol |
| `CALIBRATE` | free parameter for estimation | observable under protocol + adequate prior |
| `MEASURE` | not identifiable now; specify the experiment | unobservable + accuracy-critical |
| `REJECT` | exclude this candidate | inapplicable conditions, implausible, unverifiable quote |

### 2.3 The applicability rubric (auditable by construction)

Hand-set, deterministic, **no learned weights in v0.2**. Every decision records
*which rules fired and with what inputs*, so any user can re-derive or contest
it. Dimensions scored per candidate value against the target specification:

| dimension | example signal | source |
|---|---|---|
| chemistry match | NMC811 vs NMC111 vs LFP | value `conditions` + registry |
| format / geometry match | 21700 vs pouch vs coin | value `conditions` |
| temperature match | 25 °C vs 60 °C | value `conditions` |
| state of charge | 50 % SOC vs pristine | value `conditions` |
| method class | measured / fitted / calculated / assumed / tuned | value `kind` + `method` |
| evidence integrity | quote verbatim-verified, locator present, page present | provenance check (P5) |
| cross-source agreement | agreement across independent sources | registry `conflicts[]` |
| model applicability | scalar-declarable in PyBaMM, unit-convertible | registry `mapping.py` |

Rubric outputs: an ordered candidate list with a *reason string per candidate*
(never a bare number), plus the decision and its fired rules.

### 2.4 Human gate (mandatory, non-negotiable)

The assembly engine produces **decision support**, never autonomous parameter
writes. Registry mutation requires deterministic validation + explicit approval
(AGENTS.md rule 10). The gate is part of the artifact: `approvals[]` records who
approved what, when, and against which rubric version.

### 2.5 LLM boundary (unchanged, restated)

The LLM reads evidence and proposes; it never decides values. Every numeric
decision path (unit conversion, applicability scoring, identifiability,
calibration) is deterministic. This is a deliberate scientific stance, and it is
the axis on which we differ from the closest neighbour (see
`docs/POSITIONING.md`).

## 3. Workstreams, exit criteria, dependencies

| ID | Workstream | Scope | Exit criterion (measurable) | Depends on |
|---|---|---|---|---|
| **V2.1** | **Applicability & conflict engine** | Condition schema for values, deterministic rubric, decision taxonomy, rule-firing recorder, conflict resolution with preserved alternatives | Decides ≥20 seeded conflict cases with rule-level rationale; **expert agreement ≥80 %** on the expert-labelled conflict set | v0.1 registry + provenance checks |
| **V2.2** | **Assembly report + CLI/API** | `parallm assemble --target <cell> --protocol <p>` → per-parameter dossier, set-level summary, JSON + Markdown + PyBaMM export | Reproducible report for the LG M50 target; **every field traceable to a verified quote or an explicit `assumed` flag** | V2.1 |
| **V2.3** | **Observability join** | Attach FIM/Sobol/profile-likelihood results per parameter; produce the fit/fix/measure action matrix | Report states per-parameter observability and action; reproduces the P2 finding (negative diffusivity unobservable ≤2C) | V2.2 + P2 artifacts |
| **V2.4** | **Synthetic end-to-end validation** | Protocol-faithful synthetic experiment with deliberate model/parameter mismatch: assemble → calibrate on one rate → validate on held-out rates; **negative control** (fit an unobservable parameter → validation degrades) | Held-out-rate error vs baseline reported; negative control reproduces as predicted. Labelled **synthetic**, never experimental | V2.2, V2.3, engine + calibration |
| **V2.5** | **Evidence engineering (P8′, replaces fine-tuning)** | Multi-window retrieval (top-k deduped passages, page ranges), table-aware chunking (header + body), condition-window expansion, optional verification pass gated by the deterministic quote checker | Condition completeness on the **private v4** benchmark materially above 0.116 (target ≥0.5) with false extraction still 0.000 | v0.1 retrieval + eval |
| **V2.6** | **Closed loop (P7)** | Parameter-targeted loop: assembly flags a field → targeted evidence request → retrieval → extraction → validation → approval → recalibrate → iteration log | Auditable end-to-end demo over ≥5 parameters, with a replayable iteration log | V2.2, V2.5 |
| **V2.7** | **Product & community** | PyPI publish (`parallm-pybamm`), CI matrix (3.10–3.12), docs site, examples gallery, positioning doc, **conflict-resolution mini-benchmark (v4a)** | `pip install parallm-pybamm` works; CI green on the matrix; v4a published | all above (continuous) |

Effort guidance (for the owner, one working week ≈ 1 unit): V2.1 ≈ 2 units,
V2.2 ≈ 1.5, V2.3 ≈ 1, V2.4 ≈ 2, V2.5 ≈ 2, V2.6 ≈ 2, V2.7 ≈ 1.5 spread over the
release. One milestone at a time; each ends with tests, docs, and a commit.

## 4. Sequencing and gates

```
V2.1 ──► V2.5 ──► V2.2 ──► V2.3 ──► V2.4 ──► V2.6 ──► V2.7 (continuous)
rubric   evidence  report  observ.  synth.   loop    product
                └── conditions feed applicability ──┘
```

Gate after each milestone: exit criterion met, tests added, docs updated, one
commit, explicit go/no-go from the scientific decision-maker.

**Order rationale:** conditions (V2.5) feed applicability (V2.1); the report
(V2.2) is what makes the rubric inspectable; observability (V2.3) and synthetic
validation (V2.4) are what make the decisions *scientifically* meaningful rather
than merely organised; the loop (V2.6) is last because it should be built over a
layer that is already correct.

## 5. Decisions taken (2026-11-08, by the project owner)

| # | Decision | Rationale | Revisit when |
|---|---|---|---|
| D1 | **Auditable, hand-set applicability rubric** (no learned weights in v0.2) | Determinism, reviewability, reproducibility; weights can be calibrated against the expert-labelled set later, with the rubric version recorded | v4a conflict set reaches a stable size |
| D2 | **LG M50 / Chen2020 only for v0.2** | Depth and honesty over breadth; multi-chemistry needs its own parameter sets and would dilute the assembly logic | v0.3 (see TODO below) |
| D3 | **No fine-tuning** (P8 → P8′ evidence engineering) | The bottleneck is evidence coverage/conditions, not model weights; no credible training corpus exists (37 expert items); fine-tuning is unauditable and risks the abstention safety property (v0.1 memory arm: 0.275 false extraction, 0.333 abstention) | a real labelled corpus (≥10³ extractions) **and** a private v4 exist |
| D4 | **No real-data-dependent claims** in v0.2 | Acquisition/licensing is unresolved; the audited LG M50 sample is ineligible (C/10 charge pOCV, ~32.3 °C, license UNRESOLVED) | an eligible dataset passes the T5 protocol + license audit |
| D5 | **Benchmark privacy** | v3 is public → it is a regression suite, not a held-out benchmark. v4 (and v4a answers) must be kept private until the corresponding release | release of each benchmark version |
| D6 | **Human gate mandatory** | Rule 10; assembly is decision support, never autonomous writes | never (unless the owner changes the project rules) |
| D7 | **LLM stays out of the numeric decision path** | Matches the project's identity and its closest-neighbour differentiation | never |

## 6. Explicitly out of scope for v0.2

- Fine-tuning / fine-tuned electrochemistry LLM (D3).
- Autonomous parameter writes without approval (D6).
- Multi-chemistry/format support beyond LG M50 (D2 → TODO).
- Claims of independent experimental validation (D4).
- Marketing language ("digital twin", "validated parameterization") before D4 is
  satisfied.

## 7. TODO (carried into the queue, not v0.2 scope)

1. **Multi-chemistry coverage (LFP/graphite, NMC811, Li-metal)** — needs its own
   parameter sets + applicability rules; highest-value v0.3 item.
2. **Experimental dataset acquisition & licensing** — Chen2020 traces (author
   request), public LG M50 multi-rate sets; blocks the experimental-validation
   claim.
3. **Observables beyond voltage** — forward EIS, OCV-vs-SOC, dQ/dV, GITT-D, to
   improve identifiability structurally.
4. **First-party parameter set** ("ParaLLM-Chen2020-ext") from the 16 documented
   discrepancy families, with per-field provenance.
5. **PyPI release + CI + docs site + examples gallery.**
6. **Experimentation with a small local model** (optional, only if D3's revisit
   condition is met).

## 8. Risk register

| risk | likelihood | impact | mitigation |
|---|---|---|---|
| Applicability rubric encodes our own bias | medium | high | rule-firing transcript + expert agreement metric (V2.1) + human override |
| Benchmark overfitting (v3 public) | high | medium | private v4; v4a answers withheld; report dev/eval separately (D5) |
| Scope creep into multi-chemistry | medium | medium | D2 gate; new chemistry requires a new milestone assignment |
| Synthetic validation mistaken for experimental | medium | high | labelled "synthetic" in every artifact; docs/SCIENTIFIC_LIMITATIONS updated at release |
| Assembly report becomes a "black box" | low | high | every field traceable to a quote; no unexplained decisions |
| v0.1 evidence quality limits everything upstream | medium | medium | V2.5 before the report; conditions become load-bearing |

## 9. Naming reconciliation (housekeeping)

Two phase vocabularies co-exist and confuse readers:

- **PRD phases** (`docs/DEVELOPMENT_ROADMAP.md`): P0…P8 — the original plan
  (P6 = literature extraction, P7 = closed loop, P8 = fine-tuning study).
- **Shipped milestones** (git history, v0.1 release notes): P0…P5 —
  baseline → ecosystem audit → estimation/identifiability → literature &
  provenance → LLM evaluation → reliability/v3 benchmark/ablation.

From v0.2 onward, releases are described as **v0.x feature sets**; PRD phase
names are retained only in `docs/internal/` archives. Mapping table:

| PRD phase | shipped as | v0.2 status |
|---|---|---|
| P0 baseline | milestone P0 | done (v0.1) |
| P1 registry | milestone P1/P3 | done (v0.1) |
| P2 synthetic | milestone P2 | done (v0.1) |
| P3 inverse estimation | milestone P2 | done (v0.1) |
| P4 identifiability/UQ | milestone P2 | done (v0.1) |
| P5 experimental validation | — | **blocked** (D4) |
| P6 literature extraction | milestones P3–P5 | done (v0.1) |
| P7 closed loop | **V2.6** | planned |
| P8 fine-tuning study | **P8′ = V2.5** (evidence engineering) | replanned (D3) |
