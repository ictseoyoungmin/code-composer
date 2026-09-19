# GitHub source-first migration

The repository was migrated from ZIP-first development to a source-first GitHub workflow at the S24 stable baseline.

## Source of truth

- `skills/code-composer/` is the one canonical installable Skill.
- `.codex-plugin/`, `.claude-plugin/`, and `.agents/plugins/` are thin discovery adapters that route to the canonical `./skills/` tree. `tools/build_plugins.py` injects the canonical Skill into generated platform artifacts.
- `dist/`, rendered WAV dogfood, wheels, and ZIP releases are generated artifacts and are not committed.

## Baseline

- Stable import baseline: S24 Cymbal Presence & Excitation Hardening — CLOSED.
- Regression baseline: 518/518 source and 518/518 clean-installed wheel tests passed before migration.
- Next planned work: S25 Non-Cymbal Drum Core Hardening (kick → snare → tom).

## Workflow

1. Keep `main` stable.
2. Work in a feature branch.
3. Run canonical Skill self-check and full regression before merge.
4. Build release surfaces from source; do not persist generated plugin copies in source.
5. Publish large audio/release artifacts through GitHub Releases or CI artifacts when needed.
