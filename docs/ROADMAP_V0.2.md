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

### 2.1 Per-parameter dossier — **the central scientific artifact**

The dossier, not the CLI and not an extraction interface, is the artifact of
this project. **A researcher must be able to defend every number in the
resulting PyBaMM parameter set using the dossier alone.** Required fields (all
mandatory; "not stated" is an acceptable value, silence is not):

| # | field | content |
|---|---|---|
| 1 | **selected parameter and units** | canonical parameter id, selected value, unit (and canonical value/unit) |
| 2 | **original literature value** | the value exactly as printed in the source, before canonicalisation |
| 3 | **verified quotation and page** | verbatim quote + document id + locator + page (when the archive has a real page structure) + verification state |
| 4 | **experimental conditions** | cell product, chemistry, format, temperature, SOC, protocol, as stated by the source |
| 5 | **alternative values and conflicts** | every competing value with its own source, method and conditions; conflicts are preserved, never dropped |
| 6 | **applicability rationale** | the rubric rules that fired, with their inputs, and the resulting score |
| 7 | **identifiability assessment** | observability of this parameter under the stated protocol (V2.3), or an explicit "not assessed" |
| 8 | **final recommendation** | the decision (`USE / FIX / CALIBRATE / MEASURE / REJECT / REVIEW`) and the next action |
| 9 | **human approval status** | who approved what, when, against which rubric version (or "pending") |

```
Negative particle diffusivity [m2.s-1]
  decision:         FIX at 3.3e-14 m2.s-1  (do not fit)              [1, 8]
  literature value: 3.3e-14 m2 s-1 (as printed)                     [2]
  quote/page:      "..." (Table V) — chen2020_jes_167_080534 p.9 — verified ✔   [3]
  conditions:      LG M50 21700, half-cell (Li counter), 298.15 K, 50 % SOC    [4]
  alternatives:    Laue 2021: 9.35e-15 (NMC111/graphite) → NOT APPLICABLE    [5]
                   Chen2020 set: 3.3e-14 (tuned at 1C) → applicable, method differs
  applicability:   chemistry 1.00 (same cell), method 0.60 (calibrated),      [6]
                   temperature 1.00 (298.15 K) → total 0.884
  identifiability: |S| = 0.011–0.048 over 0.5C–2C → UNOBSERVABLE              [7]
  recommendation:  fix at literature value; if accuracy needed, measure via GITT [8]
  approval:        pending human sign-off (rubric-v1)                          [9]
```

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

## 2.9 Execution status (2026-11-08)

| item | status | evidence |
|---|---|---|
| **V2.5** evidence layer (condition-aware window + document-level setup sentences) | **implemented (first slice)**, LLM-side effect not yet measured | `literature/evidence.py`; deterministic coverage measurement `results/v2/condition_coverage/summary.md`: temperature availability **0.108 → 0.838**, SOC **0.108 → 0.757**, chemistry **0.243 → 0.838**, method **0.649 → 1.000** (share of the 37 v3 items whose evidence block contains each condition class). The LLM-side condition-completeness effect is measured on the **private v4** (not yet built) |
| **V2.1** applicability & conflict engine | **prototyped, acceptance pending V2.5** | `assembly/` package (rubric, resolution, dossier, gate); over the real 96-record registry: 96 dossiers, 7 same-source conflicts all resolved to the source's operative value with the alternative preserved, 0 spurious escalations. The expert-agreement case set (§3.1) is still to be built — **this is the V2.1 acceptance criterion** |
| **V2.2** dossier | **schema implemented** (all 9 fields) | `assembly/dossier.py`; rendering to Markdown/JSON implemented, CLI pending |
| **V2.3–V2.7** | not started | — |

Note the sequencing consequence: V2.1's rubric consumes the evidence produced by
V2.5, so V2.1 is not accepted until the expanded evidence mode is the one it is
evaluated with.

## 3. Workstreams, exit criteria, dependencies

### 3.1 Headline scientific metric for v0.2: expert agreement

The primary scientific evaluation of the assembly layer is **agreement with
expert decisions on applicability and conflict resolution** — not extraction
accuracy. Metric definition:

- A labelled case set of ≥20 conflict/applicability situations, each with
  candidates drawn from the real registry / corpus (no invented values), an
  **expert decision** (drafted by the assistant, reviewed and owned by the
  project owner) and a rationale.
- The rubric's decision is compared with the expert decision:
  **agreement rate = matched decisions / cases**, reported overall and split by
  case class (`USE/FIX` vs `REVIEW`), with every mismatch listed.
- Threshold: **≥ 80 % overall** (V2.1 exit criterion) and no systematic failure
  mode in any single rubric dimension.

The set must contain **ambiguous** cases whose expert answer is `REVIEW`; a
rubric that never abstains would score well while being useless. Agreement is
reported against *drafted* labels until the owner has reviewed them, and that
status is stated wherever the number appears.

| ID | Workstream | Scope | Exit criterion (measurable) | Depends on |
|---|---|---|---|---|
| **V2.5** | **Evidence engineering (P8′, replaces fine-tuning)** | Multi-window retrieval (top-k deduped passages, page ranges), table-aware chunking (header + body), condition-window expansion, optional verification pass gated by the deterministic quote checker | Condition completeness on the **private v4** materially above 0.116 (target ≥0.5) with false extraction still 0.000 | v0.1 retrieval + eval |
| **V2.1** | **Applicability & conflict engine** | Condition schema for values, deterministic rubric, decision taxonomy, rule-firing recorder, conflict resolution with preserved alternatives | Decides ≥20 conflict/applicability cases with rule-level rationale; **expert agreement ≥80 %** (headline metric, §3.1) | V2.5 evidence windows + v0.1 registry/provenance |
| **V2.2** | **Dossier & assembly report** | The per-parameter dossier (9 mandatory fields, §2.1) as the central artifact; set-level summary; JSON + Markdown + PyBaMM export | Reproducible report for the LG M50 target; **every field traceable to a verified quote or an explicit `assumed` flag**; every dossier contains all 9 fields | V2.1 |
| **V2.3** | **Identifiability assessment (observability join)** | Attach FIM/Sobol/profile-likelihood results per parameter; produce the fit/fix/measure action matrix | Dossier states per-parameter identifiability and action; reproduces the P2 finding (negative diffusivity unobservable ≤2C) | V2.2 + P2 artifacts |
| **V2.4** | **Synthetic end-to-end validation** | Protocol-faithful synthetic experiment with deliberate model/parameter mismatch: assemble → calibrate on one rate → validate on held-out rates; **negative control** (fit an unobservable parameter → validation degrades) | Held-out-rate error vs baseline reported; negative control reproduces as predicted. Labelled **synthetic**, never experimental | V2.2, V2.3, engine + calibration |
| **V2.6** | **Closed-loop refinement (P7)** | Parameter-targeted loop: dossier flags a field → targeted evidence request → retrieval → extraction → validation → approval → recalibrate → iteration log | Auditable end-to-end demo over ≥5 parameters, with a replayable iteration log | V2.2, V2.5 — **gated, see §4.2** |
| **V2.7** | **Productisation & community** | PyPI publish (`parallm-pybamm`), CI matrix (3.10–3.12), docs site, examples gallery, positioning doc, **applicability mini-benchmark (v4a)** | `pip install parallm-pybamm` works; CI green on the matrix; v4a published | all above (continuous) |

Effort guidance (for the owner, one working week ≈ 1 unit): V2.1 ≈ 2 units,
V2.2 ≈ 1.5, V2.3 ≈ 1, V2.4 ≈ 2, V2.5 ≈ 2, V2.6 ≈ 2, V2.7 ≈ 1.5 spread over the
release. One milestone at a time; each ends with tests, docs, and a commit.

## 4. Sequencing and gates

```
V2.5 ──► V2.1 ──► V2.2 ──► V2.3 ──► V2.4 ──► V2.6 ──► V2.7 (continuous)
evidence  applic.  dossier  identif.  synth.   loop    product
   └─ conditions feed applicability ┘
```

Gate after each milestone: exit criterion met, tests added, docs updated, one
commit, explicit go/no-go from the scientific decision-maker.

**Order rationale (corrected 2026-11-08):** **V2.5 comes first.** The
applicability rubric scores *conditions* (chemistry, temperature, SOC, format);
building it before the evidence layer reliably supplies those conditions would
encode incomplete inputs into the decision logic — the rubric would penalise
correct values for metadata that the retrieval layer should have supplied. So:
fix the evidence (V2.5), then decide applicability (V2.1), then expose the
decisions as the dossier (V2.2), then make them scientifically meaningful
(identifiability V2.3, synthetic validation V2.4), and only then close the loop
(V2.6).

### 4.2 The closed loop is gated on V2.1–V2.4 (hard gate)

**V2.6 may not start** until V2.1, V2.2, V2.3 and V2.4 have all met their exit
criteria, the synthetic validation is stable across repeats, and the dossier
has been reviewed by the scientific decision-maker on a real parameter set.

Rationale: an automated loop that repeatedly retrieves evidence and recalibrates
an incorrect parameter is not a scientific instrument — it is an automated way of
producing incorrect results, faster and with more confidence. The human approval
gate (D6) keeps the loop honest; without a reliable, reviewable decision layer
underneath, the loop would amplify the very errors the project exists to
prevent.

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
| D8 | **The per-parameter dossier is the central artifact** (9 mandatory fields, §2.1) | A researcher must be able to defend every number in the resulting PyBaMM parameter set from the dossier alone; the report/CLI is a rendering of the dossier, not the product | never |
| D9 | **V2.6 is hard-gated on V2.1–V2.4** (§4.2) | An automated retrieval/recalibration loop over an unreliable decision layer automates incorrect results | when V2.1–V2.4 exit criteria are met and the synthetic validation is stable |
| D10 | **Expert agreement is a headline metric**, not a footnote | The assembly layer's value is measured by agreement with expert judgement, always reported with the status of the label set (drafted vs owner-reviewed) | when the owner has reviewed the label set |

## 6. Explicitly out of scope for v0.2

- Fine-tuning / fine-tuned electrochemistry LLM (D3).
- Autonomous parameter writes without approval (D6).
- Multi-chemistry/format support beyond LG M50 (D2 → TODO).
- Claims of independent experimental validation (D4).
- Marketing language ("digital twin", "validated parameterization") before D4 is
  satisfied.
- Starting the closed loop before V2.1–V2.4 are reliable (D9).

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
