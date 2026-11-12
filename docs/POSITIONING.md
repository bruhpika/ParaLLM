# Positioning — who PARALLM is for, and how it differs

Scope: a **positioning scan performed 2026-11-08** (web search + reading of
abstracts) to check whether the v0.2 direction ("parameter assembly":
applicability + conflict resolution + identifiability-aware decisions) is
actually novel, and to state our differentiation honestly.

> **This is a preliminary scan, not a systematic literature review, and it is
> not evidence of novelty.** It covered public web sources found by a single
> search pass (English-language, mostly 2024–2026). Absence of a neighbour in
> this list is **not** evidence that none exists. No novelty claim is made
> anywhere in this project on the basis of this document; cite the sources
> below rather than repeating their claims, and read every "nobody does X"
> phrasing in this repository as "not found in this preliminary scan".

## 1. Audience

**Battery researchers who already use PyBaMM and/or PyBOP** and hit the
parameter wall: they need a defensible parameter set for their cell, and they
must justify every value to a reviewer or a lab.

Not the audience (yet): materials-informatics users who want a large literature
database for ML property prediction (different problem, different tooling —
see LLMB / ElectroChemLLM below).

## 2. Neighbouring work found in the scan

| work | what it does | overlap with us | what it does **not** do |
|---|---|---|---|
| **LLMB** — *AI Agent for Lithium Metal Battery Research* (ACS Central Science / PMC13107216, 2026; commentary PMC13344902) | LLM agent (hierarchical text mining + MatGD graph mining) over 3,606 papers → database of 8,074 Li-metal cells; ML capacity model; one experimental validation | LLM literature extraction at scale, per-cell composition + operating conditions | Not a physics-based **model parameterisation** workflow: no DFN/PyBaMM parameter sets, no applicability-to-a-target-cell decision, no identifiability, no conflict resolution for a model |
| **Battery-Sim-Agent** (KDD 2026, arXiv:2605.29560; code `opqrst-chen/Battery-Sim-Agent`) | LLM agent **in a closed loop with a PyBaMM simulator** to do inverse parameter estimation; base-perturbation-filter synthetic benchmark over 5 parameter sets; validated on real datasets | **Closest neighbour.** "LLM + PyBaMM + closed loop + parameter estimation" is *not* novel on its own | The LLM **proposes parameter values directly** as an optimizer. We keep the LLM out of the numeric decision path (deterministic rubric + validation + human gate). It does not resolve literature conflicts or assemble a parameter set with per-field applicability |
| **ElectroChemLLM** (arXiv:2611.00638) | Multimodal (text+tables+figures) extraction with explicit JSON schema, source grounding, chemistry-aware standardisation, expert review for ambiguous records; 232-paper benchmark; ElectroChemDB (15k articles) | Grounded, auditable extraction + standardisation + expert-in-the-loop — methodologically close to our P3–P5 | Targets a **materials/electrolyte property database** for ML; not a model parameterisation chain; no identifiability, no conflict-to-decision layer, no PyBaMM export |
| **pybamm-parameter-provenance** (Zenodo 23243371, 2026-10-08) | Per-entry provenance table for PyBaMM's Chen2020 set (18 measured / 8 fitted / 26 literature / 26 assumed / 14 setting) + SEI constant comparison across 16 sets, with regeneration scripts (PyBaMM 26.9.0.0) | **Same problem domain** (provenance for a PyBaMM set); our registry does the same for the set we use | **Static, hand-curated table for one parameter set.** No automated extraction from papers, no applicability scoring, no conflict resolution, no identifiability join, no closed loop |
| **LiionDB** (arXiv:2110.09879; liiondb.com) | Literature parameter database for continuum Li-ion models; 1000+ scalar/functional datasets, each with measurement method, applicable composition range, temperature and thermal-scaling info; explicitly warns against using values extracted under inconsistent assumptions; flags identifiability | **Already stores applicability metadata** and warns about assumption-consistency — the closest thing to our applicability idea in the literature | Metadata is *stored*, not *acted upon*: no deterministic applicability **decision** against a target cell+protocol, no conflict resolution, no fit/fix/measure action matrix, no LLM evidence pipeline, no PyBaMM export |

## 3. What is genuinely still open

Narrowed, defensible statement of the gap v0.2 targets:

> **No available tool closes the loop from "literature values with conditions" to
> "a parameter set for *this* cell and *this* experiment plan", where (a) the
> applicability match is decided by an auditable deterministic rubric, (b)
> conflicts are resolved with a recorded rationale and preserved alternatives,
> (c) identifiability decides whether a parameter may be fitted at all, (d) the
> LLM is structurally excluded from the numeric decision path, and (e) every
> field of the resulting set is traceable to a verified quote — with the
> evidence-acquisition loop closing back on the specific unresolved fields.**

Element by element: LiionDB has (a)-adjacent *metadata*; pybamm-parameter-provenance
has (e)-adjacent *curation*; Battery-Sim-Agent has the *loop* but not (a)/(b)/(c)/(d);
LLMB/ElectroChemLLM have (e)-adjacent *grounded extraction* at database scale.

## 4. How we differ (one line each)

| | PyBaMM | PyBOP | ChatGPT / LLM chat | LLMB / ElectroChemLLM | **PARALLM v0.2** |
|---|---|---|---|---|---|
| Gives you a parameter set | ✅ fixed (Chen2020) | — | ❌ flat numbers | ❌ DB rows | ✅ assembled for your cell |
| Per-field provenance + verified quote | ❌ | ❌ | ❌ | ✅ partial | ✅ deterministic |
| Conflict resolution for a target cell | ❌ | ❌ | ❌ | ❌ | ✅ auditable rubric + rationale |
| Tells you what to fit vs fix vs measure | ❌ | ❌ | ❌ | ❌ | ✅ observability join |
| LLM writes parameter values | ❌ | ❌ | ✅ (unverified) | n/a | ❌ **by design** |
| Identifiability-aware | ❌ | ✅ (per fit) | ❌ | ❌ | ✅ per parameter, up front |

## 5. Claims we make — and do not make

**Make:** "PARALLM v0.2 assembles a parameter set for a target cell from
literature-extracted, quote-verified values, using an auditable applicability
rubric and identifiability results, with a mandatory human approval gate."

**Do not make:** "first"/"only"/"novel" tool of this kind (a preliminary scan
cannot support such a claim); any claim of independent experimental
validation; any claim that the LLM produced correct electrochemistry; any
claim of automatic parameter discovery.

## 6. Scan limitations

- Web/abstract-level scan only; no systematic review; no non-English sources;
- preprints may change (Battery-Sim-Agent, ElectroChemLLM);
- `pybamm-parameter-provenance` and LiionDB may evolve into the direction we
  describe — hence v0.2 emphasises *automation + auditability + the loop*, not
  the mere existence of provenance or applicability metadata.

**Sources:** [LLMB](https://pmc.ncbi.nlm.nih.gov/articles/PMC13107216/) ·
[commentary](https://pmc.ncbi.nlm.nih.gov/articles/PMC13344902/) ·
[Battery-Sim-Agent](https://arxiv.org/html/2605.29560v1) ·
[code](https://github.com/opqrst-chen/Battery-Sim-Agent) ·
[ElectroChemLLM](https://arxiv.org/abs/2611.00638) ·
[pybamm-parameter-provenance](https://doi.org/10.5281/zenodo.23243371) ·
[LiionDB](https://ar5iv.labs.arxiv.org/html/2110.09879)
