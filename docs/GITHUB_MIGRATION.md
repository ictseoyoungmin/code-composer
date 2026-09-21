# GitHub source-first migration

The repository was migrated from ZIP-first development to a source-first GitHub workflow at the S24 stable baseline.

## Source of truth

- `skills/code-composer/` is the one canonical installable Skill.
- `.codex-plugin/`, `.claude-plugin/`, and `.agents/plugins/` are thin discovery adapters that route to the canonical `./skills/` tree. `tools/build_plugins.py` injects the canonical Skill into generated platform artifacts.
- `dist/`, rendered WAV dogfood, wheels, and ZIP releases are generated artifacts and are not committed.

## Baseline

- Stable GitHub packaging baseline: `main@2ee4d372c79b04bcc791c3ec42265438cdc576d3`.
- Local engine research lineage currently extends through S27-G as an engineering candidate.
- S27 engine work must be transplanted onto the stable source-first structure; the old ZIP-first plugin directories are not source authority.

## Workflow

1. Keep `main` stable.
2. Work in a feature branch.
3. Run canonical Skill self-check and full regression before merge.
4. Build release surfaces from source; do not persist generated plugin copies in source.
5. Publish large audio/release artifacts through GitHub Releases or CI artifacts when needed.
