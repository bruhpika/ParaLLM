# Scientific Validation (P3 / Part E)

Code: `src/pybamm_closed_loop/validation/checks.py`.
Deterministic, LLM-independent checks over extraction proposals + registry +
document store (scientific rule 10: the LLM's extraction decision never
validates itself).

## 1. Checks implemented

| Check | Function | What it verifies |
|---|---|---|
| structured-output schema | `registry.model.validate_extraction_schema` | required keys, numeric value, qualifier enum, source presence |
| dimensional consistency / unit conversion | `check_value_unit` | unit token known to `registry/units.py`; conversion to canonical unit succeeds (unknown units are a fatal error, rule 6) |
| physical plausibility | `check_plausibility` | value within family ranges (e.g. volume fractions 0-1, diffusivities 1e-17..1e-9 m2/s, radii 1e-8..1e-3 m, T 150-450 K) in canonical units; unit-family mismatch is fatal |
| definition compatibility | `check_definition` | definition present (unresolved -> warning) |
| experimental-condition compatibility | `check_conditions` | temperature within the Chen2020 experimental range (273.15-333.15 K); cell configuration present; out-of-range temperature is fatal, missing fields warn |
| conflicting literature evidence | `detect_conflict` | extraction vs registry operative value (rel tol 5 %): disagreement warns and **preserves both values** |
| PyBaMM parameter mapping | `check_pybamm_mapping` | maps to a registry record; optionally verifies the name against the installed `ParameterValues` key list |
| provenance authenticity | `check_provenance` | source document exists in the document store and the **quote is found verbatim** in the archived source (fabrication guard) |
| measurement qualifier | `check_qualifier` | measured/fitted/calculated/assumed distinguished; `fitted` is accepted but flagged "must NOT be recorded as a direct experimental measurement"; `unknown` warns |

## 2. Review states

`review_candidate(...)` aggregates checks into `ReviewReport` with the
milestone's three states:

| State | Rule |
|---|---|
| `ACCEPTED` | all checks ok |
| `NEEDS_REVIEW` | any warning (conflict, missing conditions/definition, unknown qualifier) |
| `REJECTED` | any fatal finding (schema failure, unknown unit, implausible value, unverifiable/fabricated quote, out-of-range temperature) |

Fatal findings include a fabricated quote: an extraction whose `quote`
cannot be found in the archived source document is rejected regardless of
its numeric content.

## 3. Independence from the extraction decision

- All check functions are pure functions over payload dicts + store contents;
  they never consult the extractor or the LLM.
- Validation results are stored with each `ValueCandidate`
  (`validation_summary`); rejected candidates are audited in
  `rejected.jsonl` with actor (`proposed_by`), never silently dropped.
- The registry only changes via `RegistryStore.upsert` called after
  validation + explicit review (rule 10).

## 4. Known limitations

- Plausibility ranges are hand-specified per family (`PLAUSIBILITY_RANGES`);
  new parameter families start as warnings until a range is defined.
- Conflict tolerance (5 %) is configurable but global; parameter-specific
  tolerances (e.g. larger for fitted diffusivities) are future work.
- Condition checking only covers temperature and cell-config presence;
  protocol-level compatibility (C-rate, SOC window) is assessed in the
  dataset audit, not per extraction.

## 5. Tests

`tests/unit/test_validation_review.py`: clean candidate -> ACCEPTED;
fabricated quote / unknown document / unknown unit / implausible value ->
REJECTED; conflicting value / missing conditions -> NEEDS_REVIEW; fitted
qualifier flagged. `tests/integration/test_p3_pipeline.py` validates a real
registry evidence entry against the real archive (ACCEPTED).
