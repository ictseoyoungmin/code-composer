# S27-G repository hygiene / source-first alignment

Status: **CLEAN ENGINEERING CANDIDATE**  
GitHub structural baseline: `main@2ee4d372c79b04bcc791c3ec42265438cdc576d3`  
Engine lineage: local S27-G Shared Kit / Room Final Integration engineering candidate.

## Purpose

Normalize the S27-G local engineering candidate to the current source-first GitHub repository structure **before further audio work**, without altering the S27 engine implementation.

## Structural changes

- Removed legacy duplicated plugin source trees: `.codex_plugins/`, `.claude_plugins/`.
- Added thin root discovery adapters: `.codex-plugin/`, `.claude-plugin/`, `.agents/plugins/`.
- Added `skills/code-composer/agents/openai.yaml` and canonical `assets/icon.svg`.
- Updated plugin build/distribution verification to use the single canonical `skills/code-composer/` source.
- Added current CI, repository structure, build, numerical-reproducibility, copyright/output-policy surfaces.
- Moved root slice reports/manifests to `docs/history/slices/`.
- Moved historical checksum lists to `docs/history/checksums/`.
- Moved version-era design status to `docs/history/status/`.
- Moved machine repository state to `docs/internal/REPOSITORY_STATUS.json` and refreshed it for S27-G.
- Externalized historical WAV files from Git source; identity remains in `docs/maintenance/GITHUB_SOURCE_FIRST_MIGRATION.json`.
- Removed generated build/cache residue from the source candidate.
- Updated stale repository-hygiene/legacy tests to the current source-first GitHub contracts.

## Engine preservation proof

Compared the pre-cleanup S27-G candidate against the cleaned tree for:

- `skills/code-composer/kit/src/**`
- `skills/code-composer/kit/presets/**`
- `skills/code-composer/kit/contracts/**`
- `skills/code-composer/kit/schemas/**`
- active S25–S27 test files

Result: **198/198 files byte-exact; 0 engine-scope changes**.

## Validation

- S27-F + S27-G focused: **16/16 PASS**.
- Repository/source hygiene subset: **22/22 PASS** after structural migration.
- Legacy cleanup L3/L4/L5 updated source-first contracts: **17/17 PASS**.
- v1.16 externalized-audio closure evidence: **6/6 PASS**.
- Full test collection: **81 test files / 537 tests**.
- Full regression executed in file batches because the environment's one-shot command limit interrupted the monolithic run; aggregate result: **537/537 PASS**.
- `tools/verify_plugin_distribution.py`: PASS.
- `tools/validate_skill.py`: PASS.
- canonical skill `self_check.py`: PASS.
- `compileall`: PASS.

## Current boundary

This cleanup does **not** close S27-G perceptually and does **not** write GitHub. The next work remains S27-G listening/audition closure from the preserved engine candidate.
