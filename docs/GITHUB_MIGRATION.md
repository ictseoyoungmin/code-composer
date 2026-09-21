# GitHub source-first migration

The repository was migrated from ZIP-first development to a source-first GitHub workflow at the S24 stable baseline.

## Source of truth

- `skills/code-composer/` is the one canonical installable Skill.
- `.codex-plugin/`, `.claude-plugin/`, and `.agents/plugins/` are thin discovery adapters that route to the canonical `./skills/` tree. `tools/build_plugins.py` injects the canonical Skill into generated plugin artifacts.
- `dist/`, rendered WAV dogfood, wheels, release ZIPs, caches, and build residue are generated artifacts and are not committed.

## Recovery and synchronization baseline

- Pre-sync source-first packaging baseline: `main@2ee4d372c79b04bcc791c3ec42265438cdc576d3`.
- ZIP-first engine development was recovered and validated through the S27 authenticated drum chain and the accepted S28 piano-naturalism source chain through S28-H.
- S27-M R2 Ensemble / Production Integration was then rebuilt on that complete S28-H source baseline.
- S27-M R2 source validation reached **95 test files / 636/636 PASS** before GitHub history-preservation reconciliation.
- The GitHub synchronization preserves existing source-first plugin layout, historical S20-S24 evidence/tests/examples, and compatibility presets instead of treating omissions from a clean ZIP package as deletions.

## Current gate

S27-M R2 remains **ENGINEERING CANDIDATE / perceptual gate OPEN**.

The full-song flagship is **Crossing Meridian** (24 kHz / 112 BPM / 12 bars / 27.91425 s). Treatment changes only explicit section `role_velocity_scales` and selector-scoped `targeted_onset_yields`; it does not use automatic music-bus sidechain ducking and does not attenuate already-ringing sustain or `*_control` events.

## Workflow

1. Keep `main` source-first and free of generated release/audio artifacts.
2. Work in feature branches.
3. Run full regression plus canonical Skill self-check, Skill validation, plugin-distribution validation, compileall, and release-surface builds before merge.
4. Preserve historical compatibility evidence unless a deletion is an explicit reviewed cleanup slice.
5. Build release surfaces from source; do not persist generated plugin copies in source.
6. Publish large audio/release artifacts through GitHub Releases, CI artifacts, or the external artifact store when needed.
