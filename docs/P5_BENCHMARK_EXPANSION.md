# P5 Benchmark Expansion (benchmark v3)

Benchmark v3 extends P4's v2 fixture (20 items, chen2020-centric) to a
multi-source corpus while preserving every v2 item unchanged and every v2 dev
item in the dev split. P5 code paths (`eval/benchmark_p5.py`, `benchmarks/p5/`,
`scripts/p5/`) never modify P0–P4 implementations; the scorer reuses P4 item
loading and metric aggregation and adds only documented P5-local vocabulary
extensions.

## Sources (ingested, archived, provenance recorded)

| document_id | kind | license (verified) | role |
|---|---|---|---|
| `chen2020_jes_167_080534` | paper (text) | ECS © (text archive kept; P3) | same-doc held-out / conflict anchor |
| `chen2020_supplement_s1` | supplement (PDF) | ECS © (P4) | supplement items (retained) |
| `pybamm_parameter_sets_docs` | structured-dataset (text) | PyBaMM docs (P4) | conflict/abstention items (retained) |
| `dessantis2023_batteries9_0146` | paper (PDF, 16 pp) | **CC BY 4.0** (PDF text verified) | Li-metal/LFP + Arrhenius j0/Rct |
| `goussian2024_batteries10_00205` | paper (PDF, 12 pp) | **CC BY 4.0** (PDF text verified) | BV/reaction-rate convention conflicts |
| `laue2021_jappl_electrochem_51_1253` | paper (PDF, 13 pp) | **CC BY 4.0** (PDF text verified) | P2D identifiability + NMC111/graphite Table 3 |

Acquisition manifest with URLs and sha256:
`data/raw_documents/p5_sources/acquisition_manifest.json`. CC BY PDFs archived
at `data/raw_documents/<id>/<id>.pdf`; chen2020 remains text-only (©). Store
segments: chen2020 108, supplement 47, docs 135, dessantis 26, goussian 22,
laue 13 (6 documents total).

## Fixture

`data/eval/extraction_benchmark_v3.jsonl` — **37 items** (20 v2 + 17 new), schema
identical to v2 (P4 loader `load_items_v2` consumes it).

- splits: **8 dev / 29 eval** (v2's 6 dev preserved + `P5-D1`, `P5-L7`)
- tiers: same-doc-dev 6, same-doc-heldout 7, cross-document 5, other-cell-family 19
- abstention items: 6 (`V6`, `E7`, `E-docs-sei-abstain`, `P5-L8`, `P5-D6`, `P5-G3`)
- new ids: `P5-L1..L8`, `P5-D1..D6`, `P5-DRC`, `P5-G2`, `P5-G3`

The builder (`scripts/p5/build_benchmark_v3.py`) mechanically validates each
item: `resolve_passage(store, doc, probe)` resolves (unicode-folded substring,
±260 chars), gold `tokens` witness appears in the same window, ids unique,
split/tier valid, abstention↔gold consistent. `tokens` are stripped before
write (P4 loader is strict).

## Content coverage (new)

- **Laue 2021 Table 3** (P2D, NMC111/graphite, 25 °C reference system): thickness
  (55.25/20/60 µm), porosity (0.35/0.50/0.40), electrolyte diffusivity
  7.15e-9 m²/s, solid diffusivities 9.35e-15/1.10e-12 m²/s, particle radii
  11.5/5.5 µm, Δcmax 24.9/25.4 mol L⁻¹, conductivities 20.4/9.9 mS/m, i0
  1.47/198 A/m², t₊ 0.24, α 0.5, CDL 0.2 F/m². Qualifiers follow the table
  legend (m=measured, a=fitted via Ref.[20], l=assumed via Ref.[21]).
- **Dessantis 2023** (Li-metal/LFP): j0(T) 2.99–4.77 A/m² at 20–60 °C 50% SoC
  (measured; `P5-D1`); Rct(T) 47.83–34.04 Ω (`P5-DRC`); SEI Arrhenius
  `i0,SEI = 14.7×10^4 A m⁻²·exp(−86.2 kJ mol⁻¹/RT)` assumed (`P5-D2`); Table 2
  COMSOL-library c_s,max 21,190 mol m⁻³, σ 91 S m⁻¹, D 3.2e-13 m²/s, ε_s 0.195,
  A_cell 0.000177 m², R 1 µm, L 28/25/22 µm (`P5-D3–D5`).
- **Goussian 2024** (conventions, no numeric cell parameters; data
  confidential): symmetry-factor convention α≈0.5 (`P5-G2`), reaction-rate
  unit chain `k_i`→`k0,i`→`i0`, abstention on confidential capacity (`P5-G3`).

## Registered conflicts / discrepancies (fixture `conflict_note`s)

- Laue t₊ 0.24 vs chen2020 registry `cation_transference_number` 0.2594.
- Laue constant D_e 7.15e-9 m²/s vs chen2020 `electrolyte_diffusivity_Nyman2008`
  (function of c_e,T) — no single constant comparable.
- Laue i0 1.47/198 A/m² vs chen2020 j0 2.8–6.02 A/m² @50% SOC (different
  definition/material context).
- Dessantis j0 2.99 A/m² (20 °C, 50% SoC, LFP) is a different material/condition
  family from Chen2020 NMC811 — `P5-D1` is tagged other-cell-family.

## Reproducibility

```bash
.venv-ecosystem312/bin/python scripts/p5/ingest_literature.py
.venv-ecosystem312/bin/python scripts/p5/build_benchmark_v3.py
.venv-ecosystem312/bin/python -m pytest tests/unit/test_extraction_prompt_p5.py tests/unit/test_provenance_p5.py tests/unit/test_benchmark_p5.py -q
```

P5 scoring extends vocabulary **locally** (not P0–P4): groups
`symmetry_factor`/`activation_energy`/`cell_area`; units `J.mol-1.K-1`,
`kJ.mol-1.K-1`, `C.mol-1`/`s.A.mol-1`, `mol.L-1`, `mS.m-1`; positive
power-of-ten unit scales (`10^4 A.m-2`). P4 scorer and registry are unchanged.
