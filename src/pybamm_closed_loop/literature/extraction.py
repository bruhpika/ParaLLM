"""Structured LLM extraction with validated output (P3, Part D).

Design constraints (scientific rules 4, 5, 10):
- the extractor only sees the RAG context passages (never the raw corpus);
- every extraction must carry source provenance (document id + page/offsets);
- the qualifier field distinguishes measured / fitted / calculated / assumed
  quantities, so a fitted literature parameter is never recorded as a direct
  measurement;
- if evidence is unavailable the extractor abstains and the field resolves
  to UNRESOLVED (it never invents values, units, pages or citations);
- extraction output is a *proposal* (ValueCandidate); only deterministic
  validation + explicit review can move it into the registry.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ..registry.model import SourceRef, validate_extraction_schema
from ..registry.textnorm import ascii_fold
from .index import SYNONYMS
from .retrieval import RAGContext, RetrievedSegment

VALID_QUALIFIERS = ("measured", "fitted", "calculated", "assumed", "unknown")

EXTRACTION_PROMPT_SYSTEM = (
    "You are a battery-parameter extraction assistant. You may ONLY use the "
    "EVIDENCE passages provided in the user message. Extract parameter "
    "statements as JSON objects with exactly these keys: parameter_name "
    "(str), value (float), unit (str), definition (str), material (str), "
    "temperature (float, Kelvin, or null), cell_config (str), "
    "measurement_method (str), qualifier (one of: measured, fitted, "
    "calculated, assumed, unknown), context (str), source (object with keys "
    "document_id, page (int or null), locator (str or null), quote (str or "
    "null)), reported_uncertainty (float or null). If a field is not "
    "supported by the evidence, use the string \"UNRESOLVED\" (or null for "
    "temperature/reported_uncertainty). Never invent page numbers, table "
    "numbers or citations. Distinguish measured values from fitted "
    "(calibrated) ones via the qualifier field. Respond with a JSON array "
    "of objects and nothing else."
)


@dataclass
class ExtractionCandidate:
    payload: dict[str, Any]
    schema_ok: bool
    schema_reason: str
    segment_ids: list[str]
    proposed_by: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionBatch:
    candidates: list[ExtractionCandidate] = field(default_factory=list)
    abstained: bool = False
    abstain_reason: str | None = None
    provider: str = "unknown"

    def valid(self) -> list[ExtractionCandidate]:
        return [c for c in self.candidates if c.schema_ok]


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:  # pragma: no cover
        ...


class OpenAICompatibleClient:
    """HTTP client for any OpenAI-compatible chat-completions endpoint.

    Configuration via environment (or constructor args):
      PYCL_LLM_BASE_URL  (default https://api.openai.com/v1)
      PYCL_LLM_API_KEY   (required)
      PYCL_LLM_MODEL     (required)

    The endpoint must be https (the Authorization header carries the API
    key in plaintext otherwise); http is only accepted for localhost /
    loopback endpoints (e.g. a local vLLM/Ollama server).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        self.base_url = (base_url or os.environ.get("PYCL_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("PYCL_LLM_API_KEY")
        self.model = model or os.environ.get("PYCL_LLM_MODEL")
        self.timeout = timeout
        self.name = f"llm:openai-compatible:{self.model or 'unconfigured'}"
        if not self.api_key or not self.model:
            raise RuntimeError(
                "PYCL_LLM_API_KEY and PYCL_LLM_MODEL must be set to run LLM "
                "extraction (no key is ever stored in this repository)"
            )
        _validate_base_url(self.base_url)
        self._opener = urllib.request.build_opener(_NoAuthLeakRedirectHandler())

    def complete(self, system: str, user: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.0,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with self._opener.open(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


class _NoAuthLeakRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that refuses to forward the Authorization header.

    Hardening: urllib forwards all non-content headers (including
    Authorization) to redirect targets; a compromised/attacking endpoint
    could 30x the request anywhere and harvest the Bearer API key. The
    header is kept only when scheme, host and port are identical.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        modified_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(modified_req.full_url)
        same_origin = (old.scheme.lower(), old.hostname.lower(), old.port) == (
            new.scheme.lower(),
            new.hostname.lower(),
            new.port,
        )
        if not same_origin:
            modified_req.headers.pop("Authorization", None)
        return modified_req


def _validate_base_url(url: str) -> None:
    """Reject non-https endpoints (except loopback) before any key is sent.

    Hardening: the chat-completions request carries the API key in the
    Authorization header; an operator pointing ``PYCL_LLM_BASE_URL`` at an
    ``http://`` remote would leak the key in plaintext. Only exact
    ``localhost`` and loopback IPs (127.0.0.0/8, ::1) may use http.
    """
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme == "https":
        return
    host = parts.hostname
    is_loopback = False
    if host == "localhost":
        is_loopback = True
    else:
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
    if scheme == "http" and is_loopback:
        return
    raise ValueError(
        "LLM base_url must use https (http only allowed for "
        "localhost/loopback); refusing to send the API key over a "
        f"non-https endpoint: {url!r}"
    )


_NUMBER_UNIT_RE = re.compile(
    r"(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\s*[.x\u00b7\u00d7]\s*10\s*(?P<exp>[-\u2212]\d+))?\s*"
    r"(?P<unit>%|m2\s*s-1|m2\.s-1|m3\.mol-1|mol\s*m-3|mol\.m-3|S\s*m-1|S\.m-1|"
    r"A\s*m-2|A\.m-2|mA\s*cm-2|V|K|Ah|A\.h|A|m|um|\u03bcm|cm|g\s*cm-3|dimensionless|-)"
    r"(?![A-Za-z0-9])"
)


def _parse_matched_value(m: re.Match) -> float:
    value = float(m.group("value"))
    exp = m.group("exp")
    if exp:
        value *= 10.0 ** int(exp.replace("\u2212", "-"))
    return value

_QUALIFIER_PATTERNS = (
    (re.compile(r"\b(fit(?:ted)?|tuned|optimis|optimiz|calibrat)", re.I), "fitted"),
    (re.compile(r"\b(measur|determin|ascertain|recorded|observ)", re.I), "measured"),
    (re.compile(r"\b(calculat|deriv|computed)", re.I), "calculated"),
    (re.compile(r"\b(assum|approximat|neglect)", re.I), "assumed"),
)


class OfflineDeterministicExtractor:
    """Non-LLM pattern extractor for tests/CI and the offline baseline.

    It mines numeric unit-bearing statements from retrieved passages only,
    tags them with method-keyword qualifiers, and abstains when no numeric
    evidence exists. Clearly labelled ``proposed_by="deterministic"``: its
    output is never presented as an LLM result.
    """

    name = "deterministic:offline-pattern-extractor"

    def complete(self, system: str, user: str) -> str:  # pragma: no cover
        raise RuntimeError("OfflineDeterministicExtractor has no chat interface")

    def extract_from_segments(
        self,
        segments: list[RetrievedSegment],
        target_names: list[str] | None = None,
    ) -> ExtractionBatch:
        batch = ExtractionBatch(provider=self.name)
        seen: set[tuple[str, str, float]] = set()
        for seg in segments:
            folded = ascii_fold(seg.text)
            for m in _NUMBER_UNIT_RE.finditer(folded):
                value = _parse_matched_value(m)
                unit = re.sub(r"\s+", " ", m.group("unit")).strip()
                param = _match_parameter_name(folded, target_names)
                if param is None:
                    continue
                key = (param, unit, value)
                if key in seen:
                    continue
                seen.add(key)
                qualifier = "unknown"
                for pat, q in _QUALIFIER_PATTERNS:
                    if pat.search(folded):
                        qualifier = q
                        break
                sentence = _sentence_around(folded, m.start(), m.end())
                payload = {
                    "parameter_name": param,
                    "value": value,
                    "unit": unit,
                    "definition": "UNRESOLVED",
                    "material": "UNRESOLVED",
                    "temperature": None,
                    "cell_config": "UNRESOLVED",
                    "measurement_method": "UNRESOLVED",
                    "qualifier": qualifier,
                    "context": sentence,
                    "source": {
                        "document_id": seg.document_id,
                        "page": seg.page,
                        "locator": seg.heading,
                        "quote": sentence,
                    },
                    "reported_uncertainty": None,
                }
                ok, reason = validate_extraction_schema(payload)
                batch.candidates.append(
                    ExtractionCandidate(
                        payload=payload,
                        schema_ok=ok,
                        schema_reason=reason,
                        segment_ids=[seg.segment_id],
                        proposed_by="deterministic",
                    )
                )
        if not batch.candidates:
            batch.abstained = True
            batch.abstain_reason = "no numeric parameter evidence in retrieved passages"
        return batch


def _match_parameter_name(
    folded_text: str, target_names: list[str] | None = None
) -> str | None:
    """Pick the parameter name for a passage.

    If retrieval-facet target names are provided and one of their alias
    groups is supported by the passage text, the target name is used
    (RAG-consistent labelling); otherwise the longest alias found in the
    passage wins.
    """
    best: tuple[int, str] | None = None
    matched_groups: set[str] = set()
    for group, aliases in SYNONYMS.items():
        for alias in aliases:
            a = ascii_fold(alias.lower())
            if a in folded_text:
                score = len(a)
                if best is None or score > best[0]:
                    best = (score, alias)
                matched_groups.add(group)
                break
    if target_names:
        for name in target_names:
            name_groups = _groups_of_name(name)
            if name_groups & matched_groups:
                return name
    return best[1] if best else None


def _groups_of_name(name: str) -> set[str]:
    low = ascii_fold(name.lower())
    out = set()
    for group, aliases in SYNONYMS.items():
        for alias in aliases:
            a = ascii_fold(alias.lower())
            if a in low or low in a:
                out.add(group)
                break
    return out


def _sentence_around(text: str, start: int, end: int) -> str:
    lo = start
    hi = end
    for j in range(start, max(0, start - 200), -1):
        if text[j] in ".!?\n":
            lo = j + 1
            break
    for j in range(end, min(len(text), end + 200)):
        if text[j] in ".!?\n":
            hi = j + 1
            break
    return text[lo:hi].strip()


def parse_llm_json(content: str) -> list[dict[str, Any]]:
    """Parse a JSON array/object from LLM output (code fences tolerated)."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    i = min([x for x in (text.find("["), text.find("{")) if x >= 0], default=-1)
    if i < 0:
        raise ValueError("no JSON object/array found in LLM output")
    j = max(text.rfind("]"), text.rfind("}"))
    if j < i:
        raise ValueError("unbalanced JSON in LLM output")
    data = json.loads(text[i : j + 1])
    return data if isinstance(data, list) else [data]


def run_extraction(client: LLMClient, context: RAGContext) -> ExtractionBatch:
    """Run extraction over a RAG context with an LLM client.

    Every produced candidate is schema-validated here; invalid candidates are
    kept for auditing with ``schema_ok=False`` and must be rejected later.
    """
    if isinstance(client, OfflineDeterministicExtractor):
        targets = (context.facets or {}).get("parameter_names") or []
        return client.extract_from_segments(context.segments, target_names=targets)
    batch = ExtractionBatch(provider=getattr(client, "name", "llm"))
    user = context.to_prompt_block()
    content = client.complete(EXTRACTION_PROMPT_SYSTEM, user)
    try:
        payloads = parse_llm_json(content)
    except (ValueError, json.JSONDecodeError) as exc:
        batch.abstained = True
        batch.abstain_reason = f"unparseable LLM output: {exc}"
        return batch
    seg_ids = [s.segment_id for s in context.segments]
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        if payload.get("value") in ("UNRESOLVED", None) or payload.get("parameter_name") == "UNRESOLVED":
            continue
        ok, reason = validate_extraction_schema(payload)
        batch.candidates.append(
            ExtractionCandidate(
                payload=payload,
                schema_ok=ok,
                schema_reason=reason,
                segment_ids=seg_ids[:1],
                proposed_by=getattr(client, "name", "llm"),
            )
        )
    if not batch.candidates:
        batch.abstained = True
        batch.abstain_reason = batch.abstain_reason or "no extractable evidence (all UNRESOLVED)"
    return batch


def candidate_to_source_ref(payload: dict[str, Any]) -> SourceRef | None:
    src = payload.get("source")
    if not isinstance(src, dict) or not src.get("document_id"):
        return None
    return SourceRef(
        document_id=src["document_id"],
        doi_or_url=src.get("doi_or_url"),
        locator=src.get("locator"),
        page=src.get("page"),
        quote=src.get("quote"),
    )
