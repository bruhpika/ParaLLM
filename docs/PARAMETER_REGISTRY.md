# Parameter Registry (P3 / Part A)

Structured, provenance-first registry for every parameter the closed loop
touches. Seeded deterministically from the installed PyBaMM 26.8.0.0
Chen2020 (LG M50) set and the archived Chen2020 article; never written
directly by an LLM (scientific rule 10).

Code: `src/pybamm_closed_loop/registry/` (`model`, `store`, `sources`,
`seed`, `units`, `mapping`, `textnorm`).
Data: `data/registry/registry.json` (96 records), `revisions.jsonl`,
`rejected.jsonl`; regenerate with
`.venv-ecosystem312/bin/python -m pybamm_closed_loop.registry.seed`.

## 1. Record schema (milestone items 1-15)

Each `ParameterRecord` carries:

| # | Field | Content |
|---|---|---|
| 1 | `canonical_id` | stable slug (e.g. `neg_particle_diffusivity`) |
| 2 | `pybamm_names` | exact PyBaMM 26.8.0.0 parameter key(s) |
| 3 | `pybop_mapping` | PyBOP applicability (class, bounds, P2 verdicts) |
| 4 | `definition` | physical definition in DFN terms |
| 5 | `value` + `value_unit` | operative value as carried (PyBaMM or paper-only) |
| 6 | `normalized_value` + `normalized_value_unit` | SI-canonical conversion via `registry/units.py` |
| 7 | `status` | see below |
| 8 | `source_id` | DOI / identifier (or `pybamm-26.8.0.0:chen2020-defaults`) |
| 9 | `source_location` | table caption/section anchor, or the installed key path |
| 10 | `evidence` | `ValueEntry` with verbatim quote + exact char offsets in the archive |
| 11 | `conditions` | experimental conditions of the supporting evidence |
| 12 | `method` | measurement/estimation method |
| 13 | `reported_uncertainty` (+ `uncertainty_note`) | as printed in the source |
| 14 | `validation_state` | ACCEPTED / NEEDS_REVIEW / REJECTED |
| 15 | `compatibility` | definition/mapping flags (function-valued, naming inversions, embedded constants) |
| -- | `conflicts` | **all** disagreeing values, preserved (rule 4) |
| -- | `notes` | provenance notes incl. code-verified arithmetic checks |

## 2. Statuses (scientific rule 5)

| Status | Meaning | Count in seeded registry |
|---|---|---|
| `LITERATURE_DERIVED` | value reported by a source we retrieved | 31 |
| `CALCULATED` | derived from other values; derivation verified in code | 5 |
| `CALIBRATED` | fitted/tuned value (paper's own trial-and-error tuning) | 4 |
| `ASSUMED` | explicit documented assumption | 18 |
| `UNRESOLVED` | shipped value with untraced provenance | 38 |
| `USER_SUPPLIED` | reserved for user-approved values (none yet) | 0 |

## 3. Verified provenance findings (Chen2020, DOI 10.1149/1945-7111/ab9050)

The article full text is archived (immutable) at
`data/raw_documents/chen2020_jes_167_080534/`. All quotes in records are
extracted from that archive at seed time with exact char offsets (never
typed by hand). Verified facts:

1. **The PyBaMM set is not identical to the paper's published Table VII.**
   The paper's own "Comparison between the experimentally determined and the
   tuned parameter values" table shows eight tuned parameters; the registry
   preserves both values:

   | Parameter | paper measured | PyBaMM/tuned | paper variation |
   |---|---|---|---|
   | neg. particle diffusivity | 1.74e-15 (±4.10e-15) m2/s | 3.3e-14 | +1797 % |
   | pos. particle diffusivity | 1.48e-15 (±1.05e-15) m2/s | 4e-15 | +170 % |
   | neg. max concentration | 29583 mol/m3 | 33133 | +12 % |
   | pos. max concentration | 51765 mol/m3 | 63104 | +22 % |
   | pos. 100% SOC stoichiometry | 0.2661 | 0.27 | +1.47 % |
   | Bruggeman (pos/sep/neg) | 2.43/2.57/2.91 | 1.5 (theoretical) | 38/42/48 % |

   Status of the tuned values: `CALIBRATED` (trial-and-error against C/2/1C/
   1.5C discharge + relaxation); the measured values live in `conflicts[]`.

2. **Bruggeman exponents**: PyBaMM carries 1.5 by the paper's own explicit
   decision ("theoretical value of 1.5 for packed spheres ... Setting the
   values to those in Table VII provides unphysical simulation results").
   The FIB-SEM measured exponents are preserved as conflicts.

3. **Naming inversion (verified numerically)**: PyBaMM `Electrode width [m]`
   = paper "Electrode length" = 1.58 m; PyBaMM `Electrode height [m]` =
   paper "Electrode width" = 0.065 m.

4. **Embedded constants (code-verified)**: the paper's reaction-rate
   constants (3.42e-6 / 6.48e-7 A m-2 (m3 mol-1)^1.5) are embedded in the
   PyBaMM exchange-current functions (`compatibility.reaction_rate_embedded:
   true` — verified by source introspection).

5. **Arithmetic chains verified at seed time** (notes on records):
   - `Initial concentration in negative electrode` 29866 = 0.9014 x 33133;
   - `Initial concentration in positive electrode` 17038 = 0.27 x 63104
     (the *tuned* stoichiometry; the measured 0.2661 gives 16792 and does
     not match — recorded);
   - cell volume 2.42e-5 m3 and cooling area 0.00531 m2 consistent with the
     measured 70.00 x 21.00 mm cylinder.

6. **Definition-compatibility flags**: PyBaMM j0 docstrings say "EC:DMC"
   while the paper's electrolyte is EC:EMC (3:7) + 1% VC (R&D 281); recorded
   as a flag on the exchange-current records (numeric functions unaffected).

7. **Untraced defaults**: 38 records (SEI block, double-layer capacities,
   thermal/material properties, etc.) are marked `UNRESOLVED` — they are
   PyBaMM defaults not covered by the paper's 37-parameter set. Never use
   them in calibration without tracing their original sources.

## 4. Conflicts are preserved, never silently selected (rule 4)

7 conflicts exist in the seeded registry (2 diffusivities, 2 max
concentrations, 3 Bruggeman). Each is a full `ValueEntry` with its own
source/locator/quote/review state; the operative value is untouched.
`RegistryStore.upsert` writes a revision entry on every change;
`log_rejected` audits rejected proposals.

## 5. PyBOP mapping (Part A item 3, validated in P2)

`registry/mapping.py` emits PyBOP declaration specs. The P2-approved pair
(neg/pos active-material volume fractions) carries bounds [0.55, 0.90] /
[0.45, 0.80], the three P2 initial guesses, and `joint_reporting_required`
(the correlation ridge must be reported jointly). Positive particle
diffusivity is a recommended next candidate; negative particle diffusivity
is marked `recommended: false` (P2 TASK 5: unobservable from voltage-only
data at <=2C). Function-valued parameters (OCP, j0, electrolyte transport)
are never declared as scalar `pybop.Parameter`s.

## 6. Validation state policy

- `ACCEPTED`: provenance verified (quote located in archive), value matched,
  no conflicts (42 records).
- `NEEDS_REVIEW`: any conflict, tuned value, or untraced provenance
  (54 records).
- `REJECTED`: only for extraction proposals that fail deterministic
  validation (none at seed time).

## 7. Limitations

- Provenance anchors for the two validation tables cite exact caption text
  (the HTML-to-text conversion dropped their table labels; noted in every
  affected record — confirm printed table numbers against the PDF before
  external publication).
- Function-valued parameters carry the function name as `value`; their
  numeric data live in PyBaMM data files, not in the registry.
- Nyman2008 (electrolyte transport) is cited via the PyBaMM docstring; its
  DOI is recorded as UNRESOLVED (rule: never invent identifiers).
