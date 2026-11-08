"""P5 Task 1: improved extraction prompts (P3's EXTRACTION_PROMPT_SYSTEM is
imported and reused as the baseline; it is never modified).

The P5 prompt targets the four weakest P4 metrics (condition completeness
0.0, qualifier 0.600, provenance 0.800, unit 0.880) with prompt-side
discipline only — the extraction JSON schema, the deterministic validators
and the scoring semantics are unchanged.

Hard rules carried over and sharpened:
- only evidence-grounded extraction (or, for the memory-permitted ablation,
  explicitly marked model knowledge with NO fabricated provenance);
- missing fields are marked UNRESOLVED, never inferred (rule 6);
- verbatim contiguous quotes only (P4 lessons: no ellipsis splices, no
  flattened table rows, no reordering).
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class _CompleteClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


# ---------------------------------------------------------------------------
# shared rubric blocks
# ---------------------------------------------------------------------------
_FIELD_RULES = """FIELD RULES (fill EVERY field; UNRESOLVED only when the evidence does not state it):
- parameter_name: descriptive name including electrode/side and any particle/phase qualifier.
- value: exactly the number(s) as printed (keep significant digits); for table rows keep the column header's scale implicit (print the value as shown). If the table header carries a scale (e.g. "1e-15 m2 s-1"), the value stays as printed (1.48) and the unit string carries the scale.
- unit: the unit EXACTLY as printed, including scale prefixes and typography ("10-15 m2 s-1", "mA cm-2", "A m-2 (m3 mol-1)^1.5", "%"). Do NOT convert units; do NOT re-express values in different units (a 33.5% stays 33.5 with unit %, not 0.335 with unit dimensionless).
- definition: 1-2 sentences describing the quantity (what it parameterizes).
- material: electrode/electrolyte material with composition if stated (e.g. "NMC 811 (LiNi0.80Mn0.08Co0.08Al0.04O2)"), else "UNRESOLVED".
- temperature: the temperature in Kelvin ONLY when the passage states it in any unit or as a stated condition ("room temperature", "ambient" = 298.15 K, "25 C" = 298.15 K). NEVER infer a temperature that is not stated (e.g. unless "isothermal" plus a stated temperature value, leave null). 298.15 K is acceptable ONLY for the explicitly stated conditions above.
- cell_config: cell/system description stated in the passage (chemistry, format, SOC, cycle state, full-cell vs half-cell), e.g. "LG M50 21700 full cell, 50% SOC". If the passage does not state it, "UNRESOLVED".
- measurement_method: the explicit technique used for THIS value (e.g. "four-point probe", "EIS charge-transfer resistance", "FIB-SEM reconstruction", "Sand-equation fit to GITT transients") or "UNRESOLVED".
- qualifier (choose exactly one, most specific that the text supports):
    * "measured": read directly from a stated measurement/experiment (instrument value, cell test read-out).
    * "calculated": computed from OTHER quantities via a stated expression or method (e.g. EIS impedance converted with a formula, capacity/thickness normalization, literature expression evaluated at stated concentrations).
    * "fitted": obtained by fitting a model to data (least squares, Sand-equation fit, calibration iterations; tuned/adjusted values in validation sections).
    * "assumed": chosen by assumption, convention, or theoretical reasoning without a measurement (e.g. "set to the theoretical value", manufacturer-cited values adopted as-is).
    * "unknown": ONLY when the passage gives the value but reveals nothing about its origin.
- context: 1-3 sentences of surrounding scientific context (why it matters; adjacent conditions).
- reported_uncertainty: the printed uncertainty/± as a plain number in the SAME unit as value (e.g. 1.05 for "+/- 1.05"); null when absent.
- source:
    * document_id: exactly the EVIDENCE document id (e.g. "chen2020_jes_167_080534"). NEVER fabricate ids.
    * page: the page number from the evidence header when one is shown; null otherwise. NEVER guess pages.
    * locator: the table/figure/equation/section label visible in or around the passage (e.g. "Table VII", "Figure S7 caption", "Eq. 5") or "UNRESOLVED".
    * quote: VERBATIM CONTIGUOUS copy of the source substring, copied character-for-character from the LOWERCASE-FREE original text (keep punctuation, dashes and unicode as printed; line breaks may be reproduced as spaces). QUOTE EXACTLY ONE CONTIGUOUS SPAN: never splice pieces with "...", never reorder, never summarize. The shortest span that contains the complete statement with the value's unit and qualifier context is preferred."""

_CONFLICT_RULES = """CONFLICTS: when the passage contains several values for the same quantity (different methods, SOC/temperature conditions, or main-text vs supplement), output ONE candidate per printed value, each with its own exact quote, conditions and qualifier; do not average, do not silently pick one."""

_MEMORY_DISCLAIMER = (
    "KNOWLEDGE MODE: the EVIDENCE block is intentionally empty. You may use "
    "your general knowledge of battery parameterization literature. Set "
    'source.document_id to "model_knowledge" and source.quote to null; do '
    "not fabricate quotes, pages or citations. Mark each value's "
    "measurement_method as 'model memory (unverified)' and prefer "
    '"unknown"/"assumed" for values whose provenance you are unsure of.'
)


def build_extraction_prompt_p5(memory_permitted: bool = False) -> str:
    """System prompt for P5 extraction runs.

    The evidence-grounded variant (default) targets all weakest P4 metrics.
    The memory-permitted variant is used ONLY for the Task 3 ablation
    condition 'no retrieval, model knowledge permitted' — same schema, same
    scoring semantics, different allowed knowledge source.
    """
    intro = (
        "You are a battery-parameter extraction assistant.\n"
        + (
            _MEMORY_DISCLAIMER
            if memory_permitted
            else "You may ONLY use the EVIDENCE passages provided in the user "
            "message. Nothing is known outside them."
        )
        + "\n\n"
    )
    outro = (
        "\nABSTENTION: if the evidence (or, in knowledge mode, your "
        "knowledge) does not support ANY parameter statement, respond with "
        "an empty JSON array. Never invent, average or silently substitute "
        "values (missing data stays UNRESOLVED).\n"
        "Respond with a JSON array of objects and nothing else."
    )
    return intro + _FIELD_RULES + "\n\n" + _CONFLICT_RULES + outro


# ---------------------------------------------------------------------------
# evidence-grounded extraction using a pluggable system prompt
# ---------------------------------------------------------------------------
def extract_with_prompt(
    client: _CompleteClient,
    system_prompt: str,
    user_block: str,
) -> tuple[list[dict[str, Any]], bool, str]:
    """Call the client with a chosen system prompt; return candidates,
    abstained flag and the RAW model output (always preserved verbatim).

    Filtering matches the P4 harness exactly (same parse_llm_json, same
    UNRESOLVED skipping, same schema validation) so scores are comparable
    across P4/P5 prompts.
    """
    from ..literature.extraction import parse_llm_json, validate_extraction_schema

    raw_content = client.complete(system_prompt, user_block)
    candidates: list[dict[str, Any]] = []
    try:
        payloads = parse_llm_json(raw_content)
    except (ValueError, json.JSONDecodeError):
        return [], True, raw_content
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        if payload.get("value") in ("UNRESOLVED", None) or payload.get(
            "parameter_name"
        ) == "UNRESOLVED":
            continue
        ok, _reason = validate_extraction_schema(payload)
        if ok:
            candidates.append(payload)
    return candidates, not candidates, raw_content
