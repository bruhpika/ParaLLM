# DECISIONS NEEDED — scientific & policy decisions awaiting your judgment

Everything here was flagged but **not changed** during the audit sprint, because
acting on it would change numerical results, stored data, or the intent of a
study (audit rules: no numeric drift without an explicit, reviewed decision).
Each item lists: context, options, what a "yes" would entail, and my current
recommendation. You are the scientific decision-maker (AGENTS.md); these are
not silent-fix candidates.

Status legend: `[ ]` open, `[x]` decided (fill in and consult me to implement).

---

## D1 [ ] RNG policy for synthetic noise — `calibration/synthetic.py:105`

- **Context:** `np.random.seed(spec.seed)` seeds the *global legacy* numpy RNG,
  then `pybop.add_noise` consumes it (`calibration/identifiability.py` Sobol
  wrapper and the MCMC part of `run_identifiability.py` use the same pattern).
  Deterministic and recorded in manifests, but order-sensitive and leaks global
  interpreter state (noise stream depends on every earlier consumer of the
  global RNG in the same process).
- **Options:**
  1. Keep the legacy global pattern (status quo).
  2. Migrate to `numpy.random.default_rng(seed)` (or the new seeding API) with
     the seed recorded per dataset.
- **Consequence of option 2:** the noise stream changes → **every P2 result
  changes** (recovery estimates, identifiability reports, figures). This is a
  scientific change: results must be regenerated and re-reviewed; the "same
  numbers" property of the committed `results/p2/**` gold files would break
  (deliberately).
- **Recommendation:** worth doing on the next planned P2 regeneration, never
  inside this audit sprint. If you prefer 1 permanently, add a docstring note
  "order-sensitive by design; regenerate with reproducibility manifests".

## D2 [ ] Generation vs fitting solver tolerances — `calibration/synthetic.py:102`

- **Context:** synthetic data generation solves with PyBaMM's default solver
  (introspected in installed pybamm 26.8.0.0: `IDAKLUSolver` with
  **rtol=1e-4, atol=1e-6**), while fitting hard-codes
  `IDAKLUSolver(rtol=atol=1e-6)` (`calibration/fitting.py:130`).
- **Question:** is the looser generation tolerance deliberate (faster
  benchmarking) or an oversight?
- **Consequence of aligning both to 1e-6:** generated observation arrays
  change → all downstream P2 numbers change (same regeneration cascade as D1).
- **Recommendation:** align on the next regeneration, and make the
  generation-side solver explicit/tolerances configurable rather than implicit.

## D3 [ ] Same seed for every condition — `calibration/synthetic.py:129`

- **Context:** `generate_datasets` re-seeds the identical seed per condition,
  so the 0.5C/1C/2C windows share identical noise statistics (documented in the
  docstring and docs/SYNTHETIC_RECOVERY_BENCHMARK.md).
- **Question:** intentional decorrelation trade-off or coincidental shortcut?
- **Consequence of independent seeds per condition:** changes noise in all
  multi-condition P2 artifacts (regeneration cascade).
- **Recommendation:** independent seeds (e.g. seed + condition index)
  documented via `seed_note` in the manifest, on the next regeneration.

## D4 [ ] `X-averaged …particle concentration` latent crash — `pybamm_engine/outputs.py:104-125`

- **Context:** those variables carry only `(r,t)` axes; `var(t, r, x=x_mid)`
  raises `ValueError` *outside* the guarded extraction try, crashing `run()`.
  No current config requests them (verified bug-free for all shipped configs).
- **Options:** (1) add support (2D surface sampled at x_mid or "x-averaged"
  slice), (2) degrade gracefully: report as `unavailable` instead of crashing.
- **Consequence:** (1) adds output where today it crashes; (2) changes the
  availability report semantics for hypothetical configs. Neither changes any
  existing artifact.
- **Recommendation:** option 2 at minimum (robustness), plus a test.

## D5 [ ] `benchmarks/identifiability/diffusivity_feasibility.py` PyBaMM boundary

- **Context:** this benchmark calls PyBaMM directly (bypasses `pybamm_engine/`,
  contrary to the repo's one-boundary rule) and is tightly coupled to its YAML
  (hardcoded subset indices, the `"1C"` condition name, `"1800"/"900"`
  duration-string detection — currently aligned and verified, silently wrong if
  the config changes).
- **Question:** restructure to route through `pybamm_engine/` (engine-layer
  refactor; risk of numerics drift must be proven with a full gold-report
  diff), or keep as an exempt "benchmark script" with a documented waiver?
- **Recommendation:** keep exempt for now (working, verified vs gold report)
  but add a `# NOTE: direct PyBaMM, benchmark-only` header and a waiver note in
  AGENTS.md; refactor only when this benchmark evolves.

## D6 [ ] Identifiability scope — `run_identifiability.py:147-148`

- **Context:** subset `diffusivities_vs_kinetics = [0,1,3,4]` omits
  electrolyte diffusivity (idx 2). Ambiguous whether intentional.
- **Question:** confirm the omission is deliberate (document why) or fix the
  subset to include idx 2 (changes the identifiability report's numbers).
- **Recommendation:** you decide the study design; I can implement either.

## D7 [ ] Multi-condition study reuses single-config truth/bounds — `run_identifiability.py:131,134`

- **Context:** if `recovery_multi_*.yaml` and `recovery_single_1C.yaml`
  ever diverge in truth/bounds, the multi study silently uses the single's.
- **Consequence of change:** only matters for future configs; no committed
  number changes today.
- **Recommendation:** read both explicitly and, if inconsistent, fail loudly.

## D8 [ ] Loud-failure semantics in `registry/seed.py` (audit change Agent C)

- **Context:** the audit narrowed `except Exception: continue` scopes so
  spec-data bug classes (missing `"match"` keys, ZeroDivisionError,…) now
  raise loudly instead of being silently swallowed. Verified zero behavioral
  difference on the real data (96-record content-hash proof).
- **Decision needed (policy):** confirm you accept loud failure for registry
  seeding spec bugs; otherwise revert commit `5445fb4`.
- **Recommendation:** accept — silent swallowing delayed error discovery.

## D9 [ ] Gold report schema drift — `results/p2/**/report.json` lack `fixed_values`

- **Context:** the report writer (pre-audit) echoes `fit_spec.fixed_values`,
  but the committed gold reports predate that field. Leave as is, or regenerate
  the P2 artifacts to the current schema (numbers unchanged, only the happy
  echo field added)?
- **Note:** regeneration rewrites `results/` — your call per the
  immutable-results rule.
- **Recommendation:** regenerate on the next P2 run; not a standalone rewrite.

## D10 [ ] `requires-python >=3.10` floor — `pyproject.toml`

- **Context:** venvs actually exercise only 3.12 / 3.14; behaviour below 3.12
  is untested and PyProBE needs <3.13 while several stack libs are newest-major.
  Options: keep >=3.10 (nominal), or raise to >=3.12 (honest, tested matrix).
- **Recommendation:** raise the floor to `>=3.12,<3.16` and mirror it in
  README; no numerical impact.

## D11 [ ] Characterization coverage for the identifiability pipeline

- **Context:** `run_identifiability.py` end-to-end is minutes-scale (MCMC);
  not in the characterization suite (covered indirectly via calibration +
  verified manually twice). A reduced config (tiny grids, 1 chain) snapshot
  would close the gap.
- **Recommendation:** add after any D6/D7 decision, so the baseline encodes
  the final study design.
