# CHANGES_SUMMARY — audit/hardening sprint (Nov 2026)

One row per non-merge commit on `audit/hardening` (merge-base `7bc13ec` → head `23b7b95`).
Risk: **none** = provably no executable-behavior change; **low** = behavior addition/strictness on paths that valid scientific usage never takes (guarded by tests); **medium** = semantic change reviewed and empirically verified identical on real data.

| Commit | Agent | Change | Risk |
|---|---|---|---|
| `1e475d4` | orchestrator | docs: as-implemented data flow, entry points, venv matrix, ownership map in `docs/ARCHITECTURE.md` | none |
| `5653fc6` | orchestrator | tests: characterization suite + committed baselines (safety net) | none |
| `2fc8a36` | B | literature/datasets/eval: remove unused imports, placeholder f-string (ruff F401/F541) | none |
| `8305ace` | B | `.gitignore`: add `.env`, `*.key`, `secrets/`, generic `.venv*/` | none |
| `dae7267` | B | extraction: require https (or loopback http) for LLM `base_url`; raises before any request | low (invalid-config path only) |
| `15f1651` | B | extraction: strip `Authorization` on cross-origin redirects (audit-probed live) | low |
| `20117a3` | B | ingest/eval: validate `document_id` (path traversal); corrupt-manifest error type | low (rejects ids that never occur in store) |
| `52911ae` | A | fitting: reject wrong-length `initial_values` instead of silent zip truncation | none (valid path unchanged) |
| `0d33532` | A | identifiability: `fim_multi` uses multi-config sigma (bit-identical no-op for committed configs; verified 0-diff vs gold report) | none for current data / medium-if-future-configs-differ (intended fix) |
| `1c6d231` | A | diffusivity_feasibility: reject degenerate `rel_perturbation` before study runs (prevented silent NaN report) | none (invalid configs only) |
| `a605f4f` | C | registry/scripts: ruff F401/F841 (unused imports/alias) | none |
| `1365f0d` | C | pyproject: add minimal `[tool.ruff]` config section | none |
| `9284153` | C | registry/reporting: remove dead code (grep-verified unused) | none |
| `6cb0aca` | C | docstrings on public functions/dataclasses, physical units stated | none |
| `ea577b5` | C | fix wrong docstring cross-reference in `units.py` | none |
| `ad1a74a` | C | light type hints on private seed helpers | none |
| `5445fb4` | C | registry/seed: narrow `except Exception` scopes; spec-bug classes now fail loudly (96-record seeding reproduced committed store exactly) | medium (semantic loud-failure change; verified identical on real data) |
| `cce18a8` | C | tests: `tests/unit/test_quality_agentC.py` | none |
| `a4be97d` | D | lockfiles: role header comments only (zero pin changes) | none |
| `3ce6166` | D | pyproject: optional `ecosystem` extra (bounds = verified installed versions; dry-run resolved) | none |
| `5cf7f6a` | D | README: refresh stale phases, testing matrix, ecosystem install, marker caveat | none |
| **Merges** | orchestrator | `6f40fbc` (B) → `521ccaa` (A) → `ca402f2` (C) → `23b7b95` (D); full gates green after each merge | — |

Gate history (main checkout, `.venv` / `.venv-ecosystem312`): 84/96 → 88/103 (characterization) → **123+6s/140** (post-merges; characterization 7 passed throughout). Agent E (read-only): **ACCEPT** on all four branches; adversarial probes found no numerics risk; entry-point replays bit-identical or runtime-only differences. See FINDINGS.md.
