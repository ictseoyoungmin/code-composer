# v1.16 Final Integrated Closure Dogfoods

Each case retains:

- `base_ir.json`
- `plan_before.json` / `plan_after.json`
- compiled `performance_ir_before.json` / `performance_ir_after.json`
- unresolved `music_ir_before.json` / `music_ir_after.json`
- resolved IR and analysis for both states
- `before.wav` / `after.wav`
- `revision_comparison.json`
- `agent_revision.json`

`final_closure_manifest.json` is the machine-readable release gate.

The listening reel `v1.16_final_showcase_reel.wav` loudness-normalizes copies of the three final WAVs for convenient sequential listening. The individual `after.wav` files remain the canonical unmodified renders.

## L4 maintenance cleanup

This directory remains **historical release evidence** for closed v1.16.0. L4 removed only the 12 files authorized by the closed L3 classification: nine exact deterministic repeat duplicates and three derived before/after comparison WAVs.

Determinism evidence is still preserved in `final_closure_manifest.json`, the retained canonical `after.wav` hashes, and `docs/maintenance/L4_DEAD_TEST_REFERENCE_CLEANUP.json`. Structured before/after state and the original canonical WAVs remain untouched.
