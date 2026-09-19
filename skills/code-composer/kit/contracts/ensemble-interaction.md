# Ensemble Interaction Contract

S15 represents authored inter-player relationships; it is not an automatic arranger or random humanizer.

## Section surface

Within `performance_ir.orchestration_sections.<section>.ensemble_interaction`:

- `enabled`: optional boolean.
- `leader_role`: required when enabled; must be an active arrangement role with a track.
- `timing_offsets_ms`: optional role → milliseconds map, each value in `[-30, +30]`. Positive values place that role slightly behind the section reference; negative values place it ahead.
- `overlap_velocity_scales`: optional subordinate role → scale map in `[0.5, 1.0]`. The leader may not yield to itself. Runtime applies the authored scale only in proportion to the fraction of each note that actually overlaps the leader.

Multiple tracks may share one `arrangement_role`; all such tracks receive the role interaction.

## Song-level ensemble surface

Within `performance_ir.realization.ensemble`:

- `enabled`: optional boolean.
- `role_pan_offsets`: optional role → additive pan offset map in `[-0.5, +0.5]`. Offsets add to existing track/mix-graph pan and clamp to `[-1, +1]`.

## Authority and invariants

- Existing notes, harmony, form, register plans, orchestration budgets and instrument engines remain authoritative.
- S15 never chooses a leader, timing feel, dynamic yield or pan from a style/emotion keyword. The agent authors them.
- No S15 surface or `enabled=false` preserves the pre-S15 IR.
- Realization is deterministic and idempotent.
- Explicit dynamic yielding may be reported to expressive QA as managed overlap; QA does not mutate the arrangement.
