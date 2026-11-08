"""Unit tests for the P5 prompt module (no network; stub client)."""

from __future__ import annotations

import json

from pybamm_closed_loop.eval.extraction_prompt_p5 import (
    build_extraction_prompt_p5,
    extract_with_prompt,
)


def _valid_payload(**overrides):
    base = dict(
        parameter_name="separator porosity",
        value=0.5,
        unit="dimensionless",
        definition="porosity of the separator",
        material="UNRESOLVED",
        temperature=None,
        cell_config="UNRESOLVED",
        measurement_method="UNRESOLVED",
        qualifier="measured",
        context="context",
        reported_uncertainty=None,
        source={
            "document_id": "doc",
            "page": None,
            "locator": "UNRESOLVED",
            "quote": "quote",
        },
    )
    base.update(overrides)
    return base


class _Stub:
    def __init__(self, reply: str, name: str = "stub"):
        self.reply = reply
        self.name = name
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.reply


class TestPromptText:
    def test_strict_prompt_requires_evidence_only(self):
        prompt = build_extraction_prompt_p5()
        assert "ONLY use the EVIDENCE" in prompt
        assert "model_knowledge" not in prompt
        assert "VERBATIM CONTIGUOUS" in prompt
        assert "never splice" in prompt.lower()
        assert "CONFLICTS:" in prompt

    def test_memory_prompt_permits_knowledge_but_no_fabrication(self):
        prompt = build_extraction_prompt_p5(memory_permitted=True)
        assert "model_knowledge" in prompt
        assert "model memory (unverified)" in prompt
        assert "ONLY use the EVIDENCE" not in prompt

    def test_temperature_rule_forbids_inference(self):
        prompt = build_extraction_prompt_p5()
        assert "NEVER infer a temperature" in prompt


class TestExtractWithPrompt:
    def test_valid_payload_kept_and_raw_preserved(self):
        reply = json.dumps([_valid_payload()])
        client = _Stub(reply)
        candidates, abstained, raw = extract_with_prompt(client, "sys", "user")
        assert len(candidates) == 1
        assert abstained is False
        assert raw == reply
        assert client.calls == [("sys", "user")]

    def test_unresolved_value_dropped(self):
        reply = json.dumps([_valid_payload(value="UNRESOLVED")])
        candidates, abstained, _ = extract_with_prompt(_Stub(reply), "s", "u")
        assert candidates == []
        assert abstained is True

    def test_unresolved_parameter_name_dropped(self):
        reply = json.dumps([_valid_payload(parameter_name="UNRESOLVED")])
        candidates, abstained, _ = extract_with_prompt(_Stub(reply), "s", "u")
        assert candidates == []
        assert abstained is True

    def test_invalid_json_abstains_and_preserves_raw(self):
        raw_reply = "not json at all"
        candidates, abstained, raw = extract_with_prompt(_Stub(raw_reply), "s", "u")
        assert candidates == []
        assert abstained is True
        assert raw == raw_reply

    def test_empty_array_abstains(self):
        candidates, abstained, raw = extract_with_prompt(_Stub("[]"), "s", "u")
        assert candidates == []
        assert abstained is True
        assert raw == "[]"

    def test_schema_invalid_payload_dropped(self):
        reply = json.dumps([{"parameter_name": "x", "value": 1.0}])
        candidates, abstained, _ = extract_with_prompt(_Stub(reply), "s", "u")
        assert candidates == []
        assert abstained is True
