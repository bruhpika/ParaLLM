# FINDINGS — code audit and hardening sprint (Nov 2026)

Branch: `audit/hardening` (merge base `5653fc6`, final reviewer-approved head `23b7b95`).
Scope: real bug fixes, security hardening, quality work, dependency/reproducibility docs.
**No scientific result changed.** Every numerical comparison below is against the
committed, pre-audit artifacts (`results/…`, `data/registry/…`), and the merge gate
was the characterization suite (`tests/characterization/`, baselines from pre-audit
code, verified deterministic in 3 consecutive runs per venv).

Method summary: 4 parallel worker agents in disjoint-file worktrees
(bugs / security / quality / deps), merge one-at-a-time with a full gate after each
merge, then a read-only skeptical reviewer (Agent E) over the whole diff, who
re-ran all gates and re-verified entry points, including adversarial probes.
`docs/ARCHITECTURE.md` gained the as-implemented data-flow, entry-point and
ownership map. `tests/baselines/generate_baselines.py` documents how to
regenerate baselines (only from pre-change code).

---

## 1. Fixed bugs (Agent A)

| # | File:line | What | Why | Test |
|---|---|---|---|---|
| A1 | `src/pybamm_closed_loop/calibration/fitting.py:168-171` | `run_fit_with_result` silently truncated a mismatched-length `initial_values` list via `zip` (3 sites) — later parameters silently kept pybop defaults and the report lost rows | wrong-number-of-start-values is a caller bug; failing loudly is the correct contract for a scientific fitting wrapper | `tests/unit/test_calibration_fitting_agentA.py` (mismatch raises; valid path unchanged) |
| A2 | `benchmarks/identifiability/run_identifiability.py:176-194` | `fim_multi` used the **single**-condition noise sigma for the multi-condition FIM block | dimensionally/correctness coupling; the wrong sigma would silently be used if the two configs ever diverge | none possible (closure-nested); verified instead: both committed configs use sigma=0.002 so this is a **bit-identical no-op today** — full benchmark re-run diffed 0 vs `results/p2/identifiability_volume_fractions/report.json` (beyond `runtime_s`) |
| A3 | `benchmarks/identifiability/diffusivity_feasibility.py:70-79` | `rel_perturbation <= 0` / non-finite produced 0/0 NaN sensitivities and then `json.dumps` wrote the invalid literal `NaN` into the report silently | garbage report + non-conforming JSON; guard fires before any output/is written | `tests/unit/test_diffusivity_feasibility_agentA.py` (3 tests, both venvs) |

Post-fix proof: all three P2 benchmark scripts re-run and diffed against the
committed gold reports — zero differences beyond `runtime_s` (and the
pre-existing `fixed_values` schema note, §6).

## 2. Security issues (Agent B)

### Fixed

| # | File | Issue | Severity | Fix | Test |
|---|---|---|---|---|---|
| S1 | `src/pybamm_closed_loop/literature/extraction.py` (`OpenAICompatibleClient.__init__`) | LLM `base_url` (env `PYCL_LLM_BASE_URL`) accepted any scheme — API key would be sent as `Authorization: Bearer …` over plaintext `http://remote` | high | `https` enforced; exact-`localhost`/loopback-IP `http` allowed (dev use); raises before any request | `tests/unit/test_llm_client_https_agentB.py` (12) |
| S2 | `extraction.py` (`complete`) | stdlib `urllib` `HTTPRedirectHandler` forwards the `Authorization` header to **any** 30x redirect target (and can downgrade POST→GET) — Bearer-key theft by a configured endpoint | high | `_NoAuthLeakRedirectHandler` + per-client opener; header kept only on identical origin (scheme, host, port) | `tests/unit/test_llm_redirect_agentB.py` (5, incl. a live multi-hop redirect probe; `bandit` B310 medium eliminated as a side effect) |
| S3 | `literature/ingest.py` (+ readers in `eval/benchmark.py`) | `document_id` interpolated into `raw/<id>.txt` / `segments/<id>.json` paths on **write**, manifest load and benchmark read — ids like `../../x` traverse the store root | med | `validate_document_id` (`[A-Za-z0-9][A-Za-z0-9._-]*`, no separators/leading dot) enforced at all three sites; corrupt-manifest error type hardened | `tests/unit/test_document_store_traversal_agentB.py` (11, incl. no-file-written assertion) |
| S4 | `.gitignore` | missing `.env`/`*.key`/`secrets/`/generic `.venv*/` patterns | low | added; verified nothing tracked collides | — |

Tool results: `bandit -r src scripts benchmarks -ll`: 1 medium / 0 high → **0 medium / 0 high** (remaining 11 low are flagged below). `pip-audit` on both lock files: **no known vulnerabilities**. Secrets scan (code, configs, docs, full `git log --all -p`): **zero hits** — no key rotation required. No notebooks exist.

### Flagged, not fixed

| File | Issue | Severity | Reason not fixed |
|---|---|---|---|
| `scripts/compat_probe/exp1..exp5` | 11× `assert` (B101) as scientific sanity checks | low | probe scripts are intentional exploratory tools, outside ownership; behavior must not change |
| `ingest.py:_flush` | predictable `.tmp` manifest name before atomic `replace` | low/informational | safe for a single-user local research tool; changing store layout touches git-tracked data |
| `datasets/pyprobe_link.py:16-20` | operator-supplied parquet path handed to Polars/PyProBE as-is (no upstream validation API) | low/informational | library limitation |
| audit tooling | `pip-audit` on CPython 3.14 cannot resolve the `PyProBE-Data==2.6.1` flat pin (Requires-Python <3.13) | informational | future audits should run pip-audit from a <3.14 tool python (was done via a throwaway 3.12 venv) |

## 3. Scientific concerns NOT changed (needs your judgment)

All flagged during the sprint; **none altered** because a fix would change
numerical results, a stored dataset, or the intent of a study.

1. **`calibration/synthetic.py:105`** — `np.random.seed(spec.seed)` seeds the *global legacy* numpy RNG before `pybop.add_noise` consumes it. Deterministic, but order-sensitive and leaks global interpreter state. Switching to `np.random.default_rng` **would change every P2 noise draw and all downstream numbers**. Same pattern in `identifiability.py` (Sobol wrapper) and the MCMC part of `run_identifiability.py`. Recommend a dedicated decision + regeneration of results if/when changed (would belong to a scientific change, not this audit).
2. **Synthetic data generation vs fitting solver tolerances** — generation solves with PyBaMM's default solver (`IDAKLUSolver` introspected at **rtol=1e-4, atol=1e-6** in 26.8.0.0) while `calibration/fitting.py:130` hard-codes fit-time `rtol=atol=1e-6`. A consistency question (generation noisier than fitting), not an error; equalising would change generated data.
3. **Same seed per condition** — `synthetic.py:129` re-seeds for every condition, so the 0.5C/1C/2C observation windows share identical noise statistics. Documented as deliberate (docstring + `docs/SYNTHETIC_RECOVERY_BENCHMARK.md`); scientifically you may prefer independent seeds.
4. **`pybamm_engine/outputs.py:104-125` latent limitation** — `X-averaged …particle concentration`-type variables carry only `(r,t)` axes; requesting one raises `ValueError` *outside* the guarded try and would crash `run()`. No current config requests such a variable (baseline uses non-averaged variables, verified). Supporting them would **add** output where today it crashes — a behavior addition, deferred.
5. **`benchmarks/identifiability/diffusivity_feasibility.py` bypasses `pybamm_engine/`** (calls PyBaMM APIs directly, contrary to the repo's one-boundary rule) and is tightly coupled to the pinned YAML (hardcoded subset indices, `"1C"` name, `"1800"/"900"` duration-string detection — currently aligned and verified, but silently wrong if the config is reordered). Restructure deferred: no provably-behavior-preserving mechanical drop-in exists.
6. **`run_identifiability.py:147-148`** — subset `[0,1,3,4]` (`diffusivities_vs_kinetics`) omits electrolyte diffusivity (idx 2). Ambiguous whether intentional; left untouched.
7. **`run_identifiability.py:131,134`** — the multi-condition study re-uses the single-config truth/bounds; differs only if the two recovery configs diverge (design assumption, not a bug).
8. **`run_recovery_benchmark.py:181`** — figure generation keys estimates by `list(synth.true_values)`; if a configured `true_values` entry is not among the fitted parameters, figures skip with the by-design caught message.
9. **Version-tied APIs** (Agent D, report only): pybop `Result.total_evaluations()` is a *method* in 26.10 (already handled with a call/getattr fallback — must re-verify on any pybop bump; method↔property flips are its historic churn pattern); pybop's FIM was removed in v25.10 and only the 2-parameter `classify_using_hessian` remains; `…electrode diffusivity` names are verified deprecated aliases of `…particle diffusivity` in installed pybamm 26.8.0.0; `CasadiSolver` is flagged deprecated — IDAKLU is pinned.
10. **Reduced except width in `registry/seed.py` (Agent C) is a deliberate semantic change**: spec-data bug classes (e.g. `KeyError` from a family dict missing `"match"`, `ZeroDivisionError`) now fail loudly instead of being swallowed. Verified zero behavioral difference on real data (96-record content-hash proof by Agent E); flagging so the intent is explicit in your review.

## 4. Quality changes summary (Agent C — zero behavior change)

- `pyproject.toml`: minimal permissive `[tool.ruff]` (E9/F, line-length 100, py310); `[project]` untouched by C.
- ruff `F401`/`F541`/`F841` fixes: unused imports, placeholder-less f-strings, single dead local — `src/pybamm_closed_loop/{registry,reporting,validation,literature,datasets}`, `scripts/compat_probe`.
- Dead code removed: unused constant, unused `_profile_times_label`, an always-`True` `or`-return, unused `None`-tuple padding (each grep-verified unreferenced).
- Docstrings added to public functions/dataclasses **with physical units stated**; one wrong module cross-reference fixed in a docstring.
- Light type hints on private seed helpers.
- `benchmarks/…` numeric scripts, `calibration/`, `pybamm_engine/` untouched by C.
- New tests: `tests/unit/test_quality_agentC.py` (narrowed except scopes, figure dispatch, sha256 helper).

## 5. Dependencies & reproducibility (Agent D)

- `pyproject.toml`: new optional `[project.optional-dependencies] ecosystem` extra (`pybop>=26.10,<27`, `pints>=0.6.1,<0.7`, `SALib>=1.6,<2`, `pypdf>=6.21,<7`, `polars>=1.44,<2`, `PyProBE-Data>=2.6.1,<3 ; python_version < '3.13'`); every bound resolves to exactly the versions verified installed & passing in `.venv-ecosystem312` (dry-run checked); polars capped at `<2` because 2.x is unverified here.
- `requirements*.lock`: header comment lines documenting role/python/date; **zero pin changes**.
- `README.md`: stale phase-status table fixed (P0–P3 accurate), real module layout, venv↔suite testing matrix, `pip install -e ".[ecosystem]"` snippet with the PyProBE <3.13 note.
- Deprecation-warning sweep of the main suite: zero findings.
- No CVE pin bumps needed (both locks clean).

## 6. Known remaining issues

1. `results/p2/**/report.json` gold files are one schema generation older than the report writer: they lack the `fit_spec.fixed_values` echo (pre-existing; not introduced by this audit). Regenerate if you want them current — flagged rather than rewritten (immutable-results rule).
2. Identifiability benchmark end-to-end not yet in the characterization suite (minutes-scale MCMC; Agent A + Agent E verified full runs manually). A reduced-config characterization test is a sensible follow-up.
3. Fresh git worktrees show exactly **1 environmental failure** (`test_neware_sample_is_incompatible_with_lgm50`) in the 312-venv gate because `data/external/` (gitignored upstream Neware sample) exists only per-machine. Documented in README; no code defect.
4. `python -m pybamm_closed_loop.registry.seed` re-runs append journal lines to `data/registry/revisions.jsonl` by design (append-first provenance journal).
5. `pyproject.toml` requires-python floor `>=3.10` is broader than what the venvs actually exercise (3.12/3.14); left untouched (possible decision: raise the floor).

## 7. Test results — before vs after

| Suite | Before (main `7bc13ec`) | After characterization added (`5653fc6`) | After all merges (`23b7b95`) |
|---|---|---|---|
| `.venv/bin/python -m pytest -q` (py3.14, pybamm only) | 84 passed, 4 skipped | 88 passed, 5 skipped (×3, deterministic) | **123 passed, 6 skipped** |
| `.venv-ecosystem312` full suite (py3.12, pybop/PyProBE) | 96 passed | 103 passed | **140 passed** |
| characterization gate (`tests/characterization`) | — | 7 passed (×3, deterministic) | **7 passed** |
| bandit (`-rl src scripts benchmarks`) | 1 med, 11 low | — | **0 med, 0 high**, 11 low flagged |
| pip-audit (both locks) | — | — | no known vulnerabilities |

Entry-point end-to-end (final verification, fresh writes to `/tmp`, never to `results/`):
`run_baseline.py` **bit-identical** vs `results/baseline`; `plot_baseline.py` regenerates all figures;
`run_recovery_benchmark.py` (full config) identical modulo the pre-existing `fixed_values` schema note;
`diffusivity_feasibility.py` identical modulo `runtime_s`; `run_extraction_benchmark.py --provider offline`
identical modulo `runtime`; identifiability full re-run diffed 0 vs gold (Agent A post-fix, Agent E re-verified).
