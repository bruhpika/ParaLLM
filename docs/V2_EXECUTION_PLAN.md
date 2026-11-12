# v0.2 Execution Plan (Parameter Assembly)

Companion to `docs/ROADMAP_V0.2.md` (scope, exit criteria, decisions). This file
is the **how**: milestone-by-milestone task breakdown, acceptance checks and the
working protocol. One milestone at a time; each ends with tests, docs, one
commit, and an explicit go/no-go from the scientific decision-maker.

Status legend: `[ ]` open · `[~]` in progress · `[x]` done

---

## Protocol (applies to every milestone)

1. **Announce scope first** — state the plan, dependencies, failure modes before
   writing code (AGENTS.md "Before implementing a major module").
2. **One milestone at a time.** No opportunistic refactors of P0–P5 code.
3. **No invented science.** Every value in every artifact traces to the
   registry, the ingested store, or the benchmark fixtures. New labels
   (expert decisions) are *drafted* and marked pending owner review.
4. **Determinism.** Every decision is reproducible from (rubric version,
   candidate records, target spec). No randomness, no learned weights in v0.2.
5. **Rule-firing transcript.** Every decision records which rules fired, with
   the inputs they used. A user must be able to re-derive or contest it.
6. **Tests + docs + commit + gate.** Then stop for the go/no-go.

---

## V2.5 — Evidence engineering (P8′)  *[in progress — first slice landed]*

**Landed:** condition-aware evidence window (±900 chars around the probe, plus
nearby condition-bearing sentences) and **document-level experimental-setup
retrieval** (greedy class coverage over setup sentences, verbatim), wired into
the P5 harness as `--evidence-mode {compact,expanded}` (default `compact`, so
the committed v3 results stay reproducible).

**Deterministic evidence-side measurement** (`benchmarks/v2/measure_condition_coverage.py`,
`results/v2/condition_coverage/`), share of the 37 v3 items whose evidence block
contains each condition class:

| condition class | compact (v0.1) | expanded window | + document conditions |
|---|---:|---:|---:|
| temperature | 0.108 | 0.162 | **0.838** |
| SOC | 0.108 | 0.216 | **0.757** |
| C-rate | 0.054 | 0.081 | 0.432 |
| cell | 0.081 | 0.270 | 0.514 |
| chemistry | 0.243 | 0.595 | **0.838** |
| method | 0.649 | 0.946 | **1.000** |

**Still to do in V2.5:** table-aware chunking (header row + body), multi-window
(top-k deduped) retrieval, the optional verification pass, and the **LLM-side**
measurement (condition completeness on the **private v4**, target ≥ 0.5, false
extraction still 0.000) — which requires the private v4 fixture.
*Depends on:* a private v4 fixture (built in this milestone, kept unpublished).

## V2.1 — Applicability & conflict engine  *(first milestone)*

**Goal.** For a target cell + protocol, rank and decide among candidate values
for one parameter, with a recorded rationale, preserving conflicts.

**Deliverables**
- `src/pybamm_closed_loop/assembly/` package:
  - `lexicon.py` — auditable chemistry/format/cell-product keyword table used
    to parse free-text `conditions` (registry stores conditions as text).
  - `schema.py` — `TargetSpecification`, `ConditionFacts`, `CandidateValue`,
    `Decision`, `MethodClass`.
  - `rubric.py` — hand-set weighted dimensions + blocking rules;
    `evaluate(candidate, target) -> RubricOutcome` (per-dimension scores, fired
    rules, blockers).
  - `resolve.py` — conflict classification (same-source vs cross-source),
    resolution, decision, alternatives, rationale.
  - `dossier.py` — per-parameter dossier (dict + Markdown).
  - `gate.py` — approval record (who/when/what/rubric version) + gate check.
  - `report.py` — `assemble(records, target, rubric)` over the real registry.
- `configs/v2/target_lgm50.yaml` — target specification (LG M50 / Chen2020).
- `configs/v2/rubric_v1.yaml` — rubric definition + weights + version.
- `scripts/v2/build_applicability_cases.py` → `data/eval/applicability_cases_v1.jsonl`
  — ≥20 labelled conflict/applicability cases **derived from** the registry and
  the v3 fixture (no hand-typed values); expert labels drafted, `reviewed_by`
  pending owner sign-off.
- `benchmarks/v2/run_applicability.py` — agreement of the rubric with the
  labelled set + rule-firing statistics.
- `tests/unit/test_assembly_*.py`, `tests/integration/test_assembly_report.py`.

**Rubric dimensions (v1, hand-set weights, sum 1.00)**
chemistry 0.28 · temperature 0.14 · method 0.20 · evidence integrity 0.14 ·
SOC 0.10 · format 0.04 · cross-source agreement 0.05 · model applicability 0.05.
Blocking rules: chemistry-family mismatch, failed quote verification.

**Conflict classes**
- **Same-source** (all candidates share a source): adopt the source's
  *operative* value (we parameterise the paper's model), preserve the
  alternatives with their method. Rationale recorded.
- **Cross-source**: rank by rubric score; margin below `review_margin`
  (0.10) → `REVIEW` for a human, with ranked alternatives.

**Decisions emitted in V2.1**: `USE`, `FIX`, `REJECT`, `REVIEW`.
`CALIBRATE` / `MEASURE` require observability inputs and are introduced with
V2.3 (the taxonomy in the roadmap is unchanged; V2.1 emits a subset).

**Acceptance checks**
- [ ] Unit tests: each dimension, each blocker, same-source policy,
      cross-source ranking, margin→REVIEW, dossier/gate round-trip.
- [ ] Integration test: assembly over the real 96-record registry produces a
      report with no exceptions and every field traceable.
- [ ] Benchmark: agreement with the drafted labelled set **≥ 80 %**
      (exit criterion), with per-case failures listed.
- [ ] Report states decisions for all parameters; no silent defaults.
- [ ] Docs updated (`ROADMAP_V0.2.md` status, `ARCHITECTURE.md` planned
      modules → implemented, `CHANGELOG.md`).

**Failure modes to watch**
- Free-text condition parsing mislabels a chemistry → mitigate with explicit
  "unknown" scores (never silently 0) and a `parse_warnings` field.
- The rubric "agrees" with drafted labels by construction → the labelled set
  must include **ambiguous** cases expecting `REVIEW`; report agreement
  separately for `USE/FIX` and `REVIEW` cases.
- Same-source policy could hide a genuine paper error → the preserved
  alternative stays visible in the dossier and the set-level summary counts
  preserved conflicts.

---

## V2.2 — Dossier & assembly report

The **per-parameter dossier is the central artifact** (9 mandatory fields,
roadmap §2.1): selected parameter and units · original literature value ·
verified quotation and page · experimental conditions · alternative values and
conflicts · applicability rationale · identifiability assessment · final
recommendation · human approval status.

`parallm assemble --target configs/v2/target_lgm50.yaml --out reports/` renders
the dossiers as JSON + Markdown + PyBaMM export.
**Acceptance:** reproducible report; every dossier contains all 9 fields; every
field traces to a verified quote or carries an explicit `assumed` flag.

## V2.3 — Identifiability assessment (observability join)

Attach FIM/Sobol/profile-likelihood results per parameter → fit/fix/measure
action matrix; upgrades decisions to include `CALIBRATE`/`MEASURE`.
**Acceptance:** reproduces the P2 finding (negative diffusivity unobservable
≤2C) inside the report.

## V2.4 — Synthetic end-to-end validation

Protocol-faithful synthetic experiment with deliberate mismatch: assemble →
calibrate on one rate → validate on held-out rates; negative control (fit an
unobservable parameter → validation degrades). Labelled **synthetic**, never
experimental.

## V2.6 — Closed-loop refinement (P7) — **gated on V2.1–V2.4**

Parameter-targeted loop: flagged field → targeted evidence request → retrieval
→ extraction → validation → approval → recalibrate → iteration log.
**Gate:** may not start until V2.1–V2.4 exit criteria are met, the synthetic
validation is stable across repeats, and the dossier has been reviewed by the
scientific decision-maker on a real parameter set.

## V2.7 — Product & community

PyPI (`parallm-pybamm`), CI (3.10–3.12), docs site, examples gallery,
positioning doc, conflict-resolution mini-benchmark (v4a, private answers).

---

## Sequencing

```
V2.5 ──► V2.1 ──► V2.2 ──► V2.3 ──► V2.4 ──► V2.6 ──► V2.7 (continuous)
```

**V2.5 comes first** (corrected 2026-11-08): the applicability rubric scores
conditions, so the evidence layer must supply those conditions before the
decision logic is built on top of them.

**V2.6 is hard-gated** on V2.1–V2.4 (§4.2 of the roadmap): an automated
retrieval/recalibration loop over an unreliable decision layer is an automated
way of producing incorrect results.

**TODO carried (not v0.2 scope):** multi-chemistry (LFP/graphite, NMC811,
Li-metal); experimental dataset acquisition + licensing; observables beyond
voltage (EIS/OCV/dQ/dV/GITT-D); first-party parameter set; PyPI/CI/docs site.
