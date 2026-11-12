"""The per-parameter dossier — the central scientific artifact of v0.2.

A dossier must let a researcher **defend every number** in the resulting
PyBaMM parameter set. It therefore always carries these nine fields (a field
may say "not stated" or "not assessed"; it is never silently absent):

1. selected parameter and units
2. original literature value (as printed)
3. verified quotation and page
4. experimental conditions
5. alternative values and conflicts
6. applicability rationale (rules fired + score)
7. identifiability assessment
8. final recommendation (decision + next action)
9. human approval status

The CLI/report is a *rendering* of the dossier; the dossier is the product.
"""

from __future__ import annotations

from typing import Any

from .resolve import Resolution
from .schema import CandidateValue

# the nine mandatory fields, in dossier order
DOSSIER_FIELDS: tuple[str, ...] = (
    "selected",
    "literature_value",
    "evidence",
    "conditions",
    "alternatives",
    "applicability",
    "identifiability",
    "recommendation",
    "approval",
)


def dossier(
    resolution: Resolution,
    next_step: str | None = None,
    identifiability: dict[str, Any] | None = None,
    approval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured dossier for one parameter (all nine fields present)."""
    chosen = resolution.chosen
    identifiability = identifiability or {
        "status": "not_assessed",
        "note": "requires the identifiability assessment (V2.3)",
        "source": None,
    }
    approval = approval or {
        "status": "pending",
        "approver": None,
        "timestamp": None,
        "rubric_version": resolution.rubric_version,
    }

    d: dict[str, Any] = {
        "parameter": resolution.canonical_id,
        "decision": resolution.decision.value,
        "conflict": resolution.conflict,
        "conflict_class": resolution.conflict_class,
        "review_required": resolution.review_required,
        "rubric_version": resolution.rubric_version,
        # 1 — selected parameter and units
        "selected": {
            "parameter": resolution.canonical_id,
            "value": chosen.value if chosen else None,
            "unit": chosen.unit if chosen else None,
            "canonical_value": chosen.canonical_value if chosen else None,
            "canonical_unit": chosen.canonical_unit if chosen else None,
            "method_class": chosen.method_class.value if chosen else None,
        },
        # 2 — original literature value (as printed)
        "literature_value": {
            "as_printed": chosen.value if chosen else None,
            "as_printed_unit": chosen.unit if chosen else None,
            "status": chosen.status if chosen else None,
            "method": chosen.method if chosen else None,
        },
        # 3 — verified quotation and page
        "evidence": {
            "quote": chosen.quote if chosen else None,
            "quote_present": chosen.quote_present if chosen else None,
            "quote_verified": chosen.quote_verified if chosen else None,
            "document": chosen.source_document if chosen else None,
            "source_id": chosen.source_id if chosen else None,
            "locator": chosen.source_locator if chosen else None,
            "page": chosen.page if chosen else None,
        },
        # 4 — experimental conditions
        "conditions": chosen.conditions.to_dict() if chosen else {
            "cell_product": None,
            "format": None,
            "chemistry_families": [],
            "temperature_k": None,
            "soc": None,
            "protocol": None,
            "warnings": ["no candidate value selected"],
        },
        # 5 — alternative values and conflicts
        "alternatives": [_alternative(c) for c in resolution.alternatives],
        "rejected": [_alternative(c) for c in resolution.rejected],
        # 6 — applicability rationale
        "applicability": _applicability(resolution),
        # 7 — identifiability assessment
        "identifiability": identifiability,
        # 8 — final recommendation
        "recommendation": {
            "decision": resolution.decision.value,
            "next_step": next_step or _default_next_step(resolution),
            "rationale": list(resolution.rationale),
        },
        # 9 — human approval status
        "approval": approval,
    }
    return d


def _alternative(c: CandidateValue) -> dict[str, Any]:
    return {
        "value": c.value,
        "unit": c.unit,
        "method_class": c.method_class.value,
        "method": c.method,
        "status": c.status,
        "source_id": c.source_id,
        "source_document": c.source_document,
        "locator": c.source_locator,
        "page": c.page,
        "quote": c.quote,
        "conditions": c.conditions.to_dict(),
        "is_operative": c.is_operative,
    }


def _applicability(resolution: Resolution) -> dict[str, Any]:
    scored = [o for o in resolution.outcomes]
    best = max(scored, key=lambda o: o.total) if scored else None
    return {
        "rubric_version": resolution.rubric_version,
        "total_score": round(best.total, 6) if best else None,
        "dimension_scores": (
            {k: round(v, 4) for k, v in best.dimension_scores.items()} if best else {}
        ),
        "rules_fired": best.fired if best else [],
        "candidate_scores": [
            {
                "value": o.candidate.value,
                "unit": o.candidate.unit,
                "source": o.candidate.source_id,
                "operative": o.candidate.is_operative,
                "total": round(o.total, 6),
                "blockers": o.blockers,
            }
            for o in scored
        ],
    }


def _default_next_step(resolution: Resolution) -> str:
    if resolution.review_required:
        return "human review required before this parameter enters the approved set"
    if resolution.decision.value in ("USE", "FIX"):
        return (
            "adopt the assembled value; whether this parameter may be re-fitted under a "
            "given protocol requires the identifiability assessment (V2.3)"
        )
    if resolution.decision.value == "REJECT":
        return "no usable value; request targeted evidence or accept the parameter as unresolved"
    return "unresolved"


def to_markdown(dossiers: list[dict[str, Any]], title: str = "PARALLM parameter assembly") -> str:
    """Render dossiers as a Markdown report."""
    lines = [f"# {title}", ""]
    counts: dict[str, int] = {}
    for d in dossiers:
        counts[d["decision"]] = counts.get(d["decision"], 0) + 1
    lines.append("Decisions: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    lines.append("")
    for d in dossiers:
        sel = d["selected"]
        lines.append(f"## {d['parameter']}")
        lines.append("")
        lines.append(
            f"- **decision:** {d['decision']}" + (f" (conflict: {d['conflict_class']})" if d["conflict"] else "")
        )
        lines.append(f"- **selected value:** {sel['value']} {sel['unit'] or ''}".rstrip())
        lit = d["literature_value"]
        lines.append(f"- **literature value (as printed):** {lit['as_printed']} {lit['as_printed_unit'] or ''}".rstrip())
        if lit.get("method"):
            lines.append(f"- **basis:** {lit['method']}")
        ev = d["evidence"]
        quote = (ev.get("quote") or "").strip().replace("\n", " ")
        if quote:
            quote = quote[:200] + ("…" if len(quote) > 200 else "")
        lines.append(
            f"- **quotation / page:** \"{quote or 'not stated'}\" — "
            f"{ev.get('document') or ev.get('source_id') or 'unknown'}"
            + (f", {ev['locator']}" if ev.get("locator") else "")
            + (f", p.{ev['page']}" if ev.get("page") else "")
            + f" (verified: {ev.get('quote_verified')})"
        )
        c = d["conditions"]
        lines.append(
            "- **conditions:** cell={cell}, chemistry={chem}, format={fmt}, T={t} K, SOC={soc}".format(
                cell=c.get("cell_product"),
                chem=",".join(c.get("chemistry_families") or []) or None,
                fmt=c.get("format"),
                t=c.get("temperature_k"),
                soc=c.get("soc"),
            )
        )
        app = d["applicability"]
        lines.append(
            f"- **applicability:** total {app['total_score']} "
            f"({', '.join(f'{k}={v:.2f}' for k, v in (app.get('dimension_scores') or {}).items())})"
        )
        ident = d["identifiability"]
        lines.append(f"- **identifiability:** {ident.get('status')} — {ident.get('note')}")
        for r in d["recommendation"]["rationale"]:
            lines.append(f"- **rationale:** {r}")
        if d["alternatives"]:
            lines.append("- **alternative values / conflicts:**")
            for a in d["alternatives"]:
                lines.append(
                    f"  - {a['value']} {a['unit'] or ''} — {a['method_class']}"
                    f"{(' — ' + a['source_document']) if a.get('source_document') else ''}"
                    f"{(' [operative]') if a.get('is_operative') else ''}"
                )
        if d["rejected"]:
            lines.append("- **rejected candidates:**")
            for a in d["rejected"]:
                lines.append(f"  - {a['value']} {a['unit'] or ''} — {a['method_class']}")
        lines.append(f"- **recommendation:** {d['recommendation']['next_step']}")
        appr = d["approval"]
        lines.append(
            f"- **approval:** {appr.get('status')}"
            + (f" by {appr['approver']} ({appr.get('timestamp')})" if appr.get("approver") else "")
            + f" [rubric {appr.get('rubric_version')}]"
        )
        lines.append("")
    return "\n".join(lines)
