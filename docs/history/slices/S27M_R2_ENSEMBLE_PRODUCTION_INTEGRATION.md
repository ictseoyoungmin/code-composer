# S27-M R2 — Ensemble / Production Integration

Status: CLOSED / PERCEPTUAL PASS

S27-M R2 was rebuilt on the complete S28-H source baseline after the earlier local S27-M working directory was found to contain only root documents. The incomplete historical prototype was not promoted or copied wholesale.

## Scope

Two explicit section-level performance surfaces extend S15:

- `role_velocity_scales`: authored role balance in `[0.5, 1.0]`.
- `targeted_onset_yields`: selector-scoped support-attack yielding around a chosen leader onset.

Targeted onset yield is not sidechain compression. Only support events whose own attacks fall inside the authored window are changed. Already-ringing sustain and all `*_control` events are untouched.

Realization order:

1. existing S15 timing offsets;
2. S27-M R2 role velocity scales;
3. S27-M R2 targeted onset yields;
4. existing S15 overlap-weighted yielding;
5. existing role pan offsets.

## Validation

- collection: 95 test files / 636 tests
- full partitioned regression: 636 / 636 PASS
- focused S15 + S27-M R2: 22 / 22 PASS
- maintenance/package/contract gate: 88 / 88 PASS
- standalone self-check: PASS
- skill validation: PASS
- plugin distribution validation: PASS
- compileall: PASS
- Skill / Codex / Claude build artifacts: PASS

## Production evidence

`Crossing Signal` is the existing 8-bar A/B listening artifact. A/B preserve score, instrument engines, seed, mix, and existing S15 timing/pan. B adds only authored section role scales and kick-selected targeted onset yields. No music-bus ducking is used.

## Perceptual closure

On 2026-09-22, the user completed production listening of the S27-M R2 full-song A/B and marked the perceptual gate **PASS**. S27-M R2 is therefore CLOSED. Engineering regression evidence remains supporting evidence; the closure authority is the user listening decision.
