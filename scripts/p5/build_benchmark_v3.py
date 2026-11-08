"""Build benchmark v3 = P4 benchmark v2 (unchanged) + P5 expansion items.

Expansion covers three new CC BY 4.0 documents ingested in P5:

  - dessantis2023_batteries9_0146  (Li-metal / LFP half cell)
  - goussian2024_batteries10_00205 (Butler-Volmer rate conventions)
  - laue2021_jappl_electrochem_51_1253 (NMC111 / graphite, Table 3)

Every new item is mechanically validated before the file is written:

  1. ``passage_probe`` resolves in the archived raw text (P3 resolve_passage,
     unicode-folded substring match; +/-260-char window);
  2. every ``gold_printed_token`` declared below appears inside that window,
     i.e. the gold value is genuinely printed in the passage the model sees;
  3. item ids are unique across v2 + v3;
  4. (split, tier) are one of the documented values.

No gold value is re-typed from memory: tokens are checked against the
archive, and the values themselves are the numeric readings of those
tokens. Items whose evidence is absent by design are ``expect_abstain``
(no gold). v2 items are copied byte-for-byte as parsed JSON.

Usage:
  .venv-ecosystem312/bin/python scripts/p5/build_benchmark_v3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pybamm_closed_loop.eval.benchmark import resolve_passage  # noqa: E402
from pybamm_closed_loop.literature.ingest import DocumentStore  # noqa: E402

V2 = REPO_ROOT / "data/eval/extraction_benchmark_v2.jsonl"
OUT = REPO_ROOT / "data/eval/extraction_benchmark_v3.jsonl"
STORE = DocumentStore(REPO_ROOT / "data/literature_store")

D = "dessantis2023_batteries9_0146"
L = "laue2021_jappl_electrochem_51_1253"
G = "goussian2024_batteries10_00205"

VALID_TIERS = {"same-doc-dev", "same-doc-heldout", "cross-document", "other-cell-family"}
VALID_SPLITS = {"dev", "eval"}


def _gold(name, value, unit, qualifier=None, alt=None, canonical_value=None, canonical_unit=None):
    g = {
        "parameter_name": name,
        "value": value,
        "unit": unit,
        "qualifier": qualifier,
        "qualifier_alt": alt,
    }
    if canonical_value is not None:
        g["canonical_value"] = canonical_value
    if canonical_unit is not None:
        g["canonical_unit"] = canonical_unit
    return g


# ---------------------------------------------------------------------------
# P5 expansion items. `tokens` are printed-text witnesses for mechanical
# verification (not written to the fixture).
# ---------------------------------------------------------------------------
NEW_ITEMS: list[dict] = [
    # ------------------------- Laue 2021 (Table 3) -----------------------
    dict(
        item_id="P5-L1-thickness-table",
        document_id=L,
        passage_probe="Layer thicknessm",
        tokens=["55.25", "20.0", "60.0", "μm"],
        facets={
            "parameter_names": ["electrode thickness", "separator thickness"],
            "materials": ["NMC111", "graphite"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": ["measured"],
        },
        gold=[
            _gold("negative electrode thickness", 55.25, "um", "measured"),
            _gold("separator thickness", 20.0, "um", "measured"),
            _gold("positive electrode thickness", 60.0, "um", "measured"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Laue Table 3 columns are Anode | Separator | Cathode; legend letter "
            "'m' = Measured. Values must be mapped to columns, not read left-to-right "
            "blindly."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-L2-porosity-table",
        document_id=L,
        passage_probe="Porositym",
        tokens=["0.35", "0.50", "0.40"],
        facets={
            "parameter_names": ["porosity", "electrode porosity"],
            "materials": ["NMC111", "graphite", "separator"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": ["measured"],
        },
        gold=[
            _gold("negative electrode porosity", 0.35, "dimensionless", "measured"),
            _gold("separator porosity", 0.50, "dimensionless", "measured"),
            _gold("positive electrode porosity", 0.40, "dimensionless", "measured"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Separator column is the middle value (0.50); dash-marked cells mean "
            "not applicable, not zero."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-L3-exchange-current-table",
        document_id=L,
        passage_probe="1.47",
        tokens=["1.47", "198"],
        facets={
            "parameter_names": ["exchange current density"],
            "materials": ["NMC111", "graphite"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": ["parameter estimation", "C-rate test"],
        },
        gold=[
            _gold("negative electrode exchange current density", 1.47, "A.m-2", "fitted"),
            _gold("positive electrode exchange current density", 198.0, "A.m-2", "fitted"),
        ],
        split="eval",
        tier="cross-document",
        evidence_format="table",
        expert_note=(
            "Legend 'a' = Estimated in Ref. [20] (multi-start parameter estimation, "
            "PE step 2), hence qualifier fitted. Unit printed as 'Am -2'."
        ),
        conflict_note=(
            "Cross-document spread for i0 at comparable SOC: Chen2020 Table VI "
            "reports 2.80e-1..6.02e-1 mA cm-2 (2.8..6.02 A m-2) at 50% SOC over "
            "25-60 C for NMC811/graphite; Laue reports 1.47 (graphite) and 198 "
            "(NMC111) A m-2. Different cells/techniques - both preserved, neither "
            "is a correction of the other."
        ),
    ),
    dict(
        item_id="P5-L4-solid-diffusivity-table",
        document_id=L,
        passage_probe="9.35",
        tokens=["9.35", "1.10"],
        facets={
            "parameter_names": ["solid phase lithium diffusivity", "particle diffusivity"],
            "materials": ["NMC111", "graphite"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": ["parameter estimation", "C-rate test"],
        },
        gold=[
            _gold("negative electrode solid diffusivity", 9.35e-15, "m2.s-1", "fitted"),
            _gold("positive electrode solid diffusivity", 1.10e-12, "m2.s-1", "fitted"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Separator cell is dash (no solid diffusivity). Legend 'a' = estimated "
            "in Ref. [20] -> fitted."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-L5-transference-literature",
        document_id=L,
        passage_probe="Transference number",
        tokens=["0.24"],
        facets={
            "parameter_names": ["cation transference number"],
            "materials": [],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {"temperature": 298.15},
            "techniques": ["literature value"],
        },
        gold=[
            _gold("cation transference number", 0.24, "dimensionless", "assumed"),
        ],
        split="eval",
        tier="cross-document",
        evidence_format="table",
        expert_note=(
            "Legend 'l' = Taken from Ref. [21]: the document adopts the value "
            "without describing its measurement -> rubric 'assumed'. A reader who "
            "follows Ref. [21] could argue 'measured'; that ambiguity is retained "
            "here and documented rather than silently resolved."
        ),
        conflict_note=(
            "Chen2020 measures/computes t+ = 0.2594 for its electrolyte; Laue's "
            "reference system uses 0.24 from Ref. [21]. Both preserved."
        ),
    ),
    dict(
        item_id="P5-L6-electrolyte-diffusivity-table",
        document_id=L,
        passage_probe="7.15",
        tokens=["7.15", "10−9"],
        facets={
            "parameter_names": ["electrolyte diffusivity", "electrolyte diffusion coefficient"],
            "materials": [],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": ["parameter estimation"],
        },
        gold=[
            _gold("electrolyte diffusivity", 7.15e-9, "m2.s-1", "fitted"),
        ],
        split="eval",
        tier="cross-document",
        evidence_format="table",
        expert_note=(
            "Single value shared by all three columns (anode/separator/cathode). "
            "Legend 'a' = estimated in Ref. [20] -> fitted."
        ),
        conflict_note=(
            "Chen2020 uses a concentration-dependent electrolyte diffusivity "
            "(Nyman2008 function), so no single cross-document constant exists to "
            "compare; the constant is a modelling choice of Laue's reference set."
        ),
    ),
    dict(
        item_id="P5-L7-reference-system-temperature",
        document_id=L,
        passage_probe="chamber at 25",
        tokens=["25", "EL-Cells GmbH"],
        facets={
            "parameter_names": ["temperature", "reference temperature"],
            "materials": ["NMC111", "graphite"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {"chamber": "25 C"},
            "techniques": ["three-electrode cell"],
        },
        gold=[
            _gold("reference temperature", 298.15, "K", "measured"),
            _gold("charge-transfer coefficient", 0.5, "dimensionless", "assumed"),
        ],
        split="dev",
        tier="other-cell-family",
        evidence_format="paper-text",
        expert_note=(
            "Temperature: 'temperature chamber at 25 °C' -> 298.15 K. The 0.5 "
            "charge-transfer coefficient is the Table 3 'l' entry (adopted from "
            "Ref. [21]) and is the standard symmetry-factor hypothesis."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-L8-abstain-tortuosity-exponent",
        document_id=L,
        passage_probe="Quasi-static C-rate",
        tokens=["Quasi-static C-rate"],
        facets={
            "parameter_names": ["tortuosity exponent", "bruggeman exponent"],
            "materials": ["separator"],
            "cell_chemistry": ["NMC111", "graphite"],
            "conditions": {},
            "techniques": [],
        },
        gold=[],
        expect_abstain=True,
        split="eval",
        tier="other-cell-family",
        evidence_format="paper-text",
        expert_note=(
            "The PE-step table names electrode tortuosities tau_a/tau_c as fitted "
            "parameters but gives no Bruggeman/tortuosity exponent value anywhere; "
            "the correct behaviour is abstention."
        ),
        conflict_note=None,
    ),
    # ---------------------- Dessantis 2023 (Li-metal/LFP) -----------------
    dict(
        item_id="P5-D1-lfp-j0-vs-temperature",
        document_id=D,
        passage_probe="reference exchange current density for the cathode was made equal",
        tokens=["2.99", "4.77", "50% SoC"],
        facets={
            "parameter_names": ["exchange current density"],
            "materials": ["LFP", "lithium metal"],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {"soc": "50%", "temperature": [293.15, 333.15]},
            "techniques": ["EIS", "PEIS", "equivalent circuit fit"],
        },
        gold=[
            _gold("positive electrode exchange current density", 2.99, "A.m-2", "calculated", "measured"),
            _gold("positive electrode exchange current density", 4.77, "A.m-2", "calculated", "measured"),
        ],
        split="dev",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Table 1 gives j0 at 20-60 °C, measured at 50% SoC; the model uses "
            "2.99 A m-2 (20 °C). j0 is computed from measured Rct via Eq. (21) "
            "(i0 = RT/(Rct*S*F)) -> calculated; 'measured' accepted as alt."
        ),
        conflict_note=(
            "Same order of magnitude as Chen2020 j0 values (2.8-6.02 A m-2 at "
            "50% SOC) but different chemistry (LFP vs NMC811); not a conflict."
        ),
    ),
    dict(
        item_id="P5-D2-sei-j0-arrhenius",
        document_id=D,
        passage_probe="86.2",
        tokens=["14.7", "86.2", "Kindermann"],
        facets={
            "parameter_names": ["SEI exchange current density", "activation energy"],
            "materials": [],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {},
            "techniques": ["literature Arrhenius model"],
        },
        gold=[
            _gold("SEI exchange current density", 1.47e5, "A.m-2", "assumed"),
            _gold("SEI activation energy", 86.2, "kJ.mol-1", "assumed"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="equation",
        expert_note=(
            "Eq. (18): i0,SEI = 14.7x10^4 A m-2 * exp(-86.2 kJ mol-1 / RT), 'the "
            "same Arrhenius behaviour hypothesized by Kindermann et al.' -> "
            "literature-adopted (assumed). Printed '14.7x 104' is 1.47e5, not 14.7: "
            "a unit-scale trap."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-D3-lfp-cs-max-comsol",
        document_id=D,
        passage_probe="cs,max",
        tokens=["21,190"],
        facets={
            "parameter_names": ["maximum concentration", "saturation concentration"],
            "materials": ["LFP"],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {"temperature": 293.15},
            "techniques": ["COMSOL library"],
        },
        gold=[
            _gold("positive electrode maximum concentration", 21190.0, "mol.m-3", "assumed", "unknown"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Table 2 footnote 2 marks this value 'COMSOL Multiphysics Library', "
            "i.e. a library default with no measurement described -> assumed; "
            "'unknown' accepted because the table gives no further basis."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-D4-lfp-sigma-D-comsol",
        document_id=D,
        passage_probe="Kinetic and transport properties",
        tokens=["91", "3.2", "COMSOL"],
        facets={
            "parameter_names": ["electronic conductivity", "solid phase lithium diffusivity"],
            "materials": ["LFP"],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {"temperature": 293.15},
            "techniques": ["COMSOL library"],
        },
        gold=[
            _gold("positive electrode electronic conductivity", 91.0, "S.m-1", "assumed", "unknown"),
            _gold("positive electrode solid diffusivity", 3.2e-13, "m2.s-1", "assumed", "unknown"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Table 2 footnote 2 (COMSOL library) applies to both row entries. "
            "Cathode only; the lithium-metal anode is a boundary, not an intercalation "
            "electrode."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-D5-radius-and-cell-area",
        document_id=D,
        passage_probe="Acell",
        tokens=["0.000177", "Ri (µm) 1"],
        facets={
            "parameter_names": ["particle radius", "cell area"],
            "materials": ["LFP"],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {"temperature": 293.15},
            "techniques": ["FESEM", "coin cell"],
        },
        gold=[
            _gold("positive particle radius", 1.0, "um", "measured"),
            _gold("cell area", 0.000177, "m2", "calculated", "measured"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Table 2 R_i = 1 um; text 4.1.1 measures LFP particle morphology by "
            "FESEM (measured). A_cell = 0.000177 m2 matches pi*(7.5 mm)^2 for the "
            "15 mm discs described in 3.1, so 'calculated' is the better qualifier; "
            "'measured' is the nominal disc area."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-DRC-rct-vs-temperature",
        document_id=D,
        passage_probe="47.83",
        tokens=["47.83", "34.04"],
        facets={
            "parameter_names": ["charge transfer resistance"],
            "materials": ["LFP"],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {"soc": "50%", "temperature": [293.15, 333.15]},
            "techniques": ["EIS", "PEIS", "ZView equivalent circuit"],
        },
        gold=[
            _gold("charge transfer resistance", 47.83, "Ohm", "measured"),
            _gold("charge transfer resistance", 34.04, "Ohm", "measured"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="table",
        expert_note=(
            "Table 1 Rct row at 20 °C and 60 °C (50% SoC). Fitted Rct from EIS "
            "with equivalent circuit (R3) -> measured. Values must not be conflated "
            "with the j0 row above them."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-D6-abstain-transference",
        document_id=D,
        passage_probe="1.0 M solution of LiPF6",
        tokens=["LiPF6"],
        facets={
            "parameter_names": ["cation transference number", "transference number"],
            "materials": [],
            "cell_chemistry": ["Li-metal", "LFP"],
            "conditions": {},
            "techniques": [],
        },
        gold=[],
        expect_abstain=True,
        split="eval",
        tier="other-cell-family",
        evidence_format="paper-text",
        expert_note=(
            "The electrolyte is named (1.0 M LiPF6 in EC:DEC 1:1) and t+ appears "
            "only as a model symbol; no numeric transference number is reported. "
            "Correct behaviour is abstention."
        ),
        conflict_note=None,
    ),
    # ------------------------ Goussian 2024 (conventions) -----------------
    dict(
        item_id="P5-G2-symmetry-factor-assumption",
        document_id=G,
        passage_probe="commonly assumed that these charge transfer coefficients",
        tokens=["0.5"],
        facets={
            "parameter_names": ["charge transfer coefficient", "symmetry factor"],
            "materials": [],
            "cell_chemistry": [],
            "conditions": {},
            "techniques": ["Butler-Volmer"],
        },
        gold=[
            _gold("charge transfer coefficient", 0.5, "dimensionless", "assumed"),
        ],
        split="eval",
        tier="other-cell-family",
        evidence_format="paper-text",
        expert_note=(
            "'In the literature, it is commonly assumed that these charge transfer "
            "coefficients are equal to 0.5' -> assumed (not measured here)."
        ),
        conflict_note=None,
    ),
    dict(
        item_id="P5-G3-abstain-capacity-confidential",
        document_id=G,
        passage_probe="Data Availability Statement",
        tokens=["confidential"],
        facets={
            "parameter_names": ["cell capacity", "nominal capacity"],
            "materials": [],
            "cell_chemistry": [],
            "conditions": {},
            "techniques": [],
        },
        gold=[],
        expect_abstain=True,
        split="eval",
        tier="other-cell-family",
        evidence_format="paper-text",
        expert_note=(
            "The paper reports reaction-rate identification methodology only; no "
            "cell capacity appears anywhere and the supporting data are stated to "
            "be confidential. Correct behaviour is abstention."
        ),
        conflict_note=None,
    ),
]


def main() -> int:
    v2_rows = [json.loads(line) for line in V2.read_text().splitlines() if line.strip()]
    ids = {r["item_id"] for r in v2_rows}

    problems: list[str] = []
    for item in NEW_ITEMS:
        if item["item_id"] in ids:
            problems.append(f"duplicate item id {item['item_id']}")
        ids.add(item["item_id"])
        if item["split"] not in VALID_SPLITS:
            problems.append(f"{item['item_id']}: bad split {item['split']}")
        if item["tier"] not in VALID_TIERS:
            problems.append(f"{item['item_id']}: bad tier {item['tier']}")
        try:
            window = resolve_passage(STORE, item["document_id"], item["passage_probe"])
        except ValueError as exc:
            problems.append(f"{item['item_id']}: probe does not resolve: {exc}")
            continue
        for token in item["tokens"]:
            if token not in window:
                problems.append(
                    f"{item['item_id']}: gold witness token {token!r} not inside "
                    f"passage window for probe {item['passage_probe']!r}"
                )
        if item.get("expect_abstain") and item.get("gold"):
            problems.append(f"{item['item_id']}: abstain item must not carry gold")
        if not item.get("expect_abstain") and not item.get("gold"):
            problems.append(f"{item['item_id']}: non-abstain item lacks gold")

    if problems:
        print("FIXTURE VALIDATION FAILED:")
        for p in problems:
            print("  -", p)
        return 1

    rows = v2_rows + [{k: v for k, v in item.items() if k != "tokens"} for item in NEW_ITEMS]
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n" for r in rows))

    print(f"wrote {OUT.relative_to(REPO_ROOT)}: {len(rows)} items "
          f"({len(v2_rows)} v2 preserved + {len(NEW_ITEMS)} new)")
    for split in ("dev", "eval"):
        ids_s = [r["item_id"] for r in rows if r["split"] == split]
        print(f"  split {split}: {len(ids_s)} items")
    tiers: dict[str, int] = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    for t in sorted(tiers):
        print(f"  tier {t}: {tiers[t]}")
    n_abstain = sum(1 for r in rows if r.get("expect_abstain"))
    print(f"  abstention items: {n_abstain}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
