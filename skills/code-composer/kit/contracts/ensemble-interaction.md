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

## S27-M R2 production-integration extensions

Within the same section-level `ensemble_interaction` object, two optional authored surfaces extend S15 without adding automatic arranging:

- `role_velocity_scales`: role → scale in `[0.5, 1.0]`. This is a section-wide performance-balance decision applied only to audible velocity-bearing events. `*_control` events are never rewritten.
- `targeted_onset_yields`: an array of explicit attack-ownership rules. Each rule contains:
  - `leader_role`: active role that owns the selected attack.
  - `leader_event_selector`: optional selector with `event_type` and, for drum events, `drums`.
  - `window_ms`: onset window in `[10, 250]` ms.
  - `support_velocity_scales`: support role → minimum scale in `[0.5, 1.0]`.

At exact onset coincidence the authored minimum scale applies. The yield fades linearly back to unity at the edge of the window. Only support events whose *own attacks* occur inside the window are changed; an already-ringing piano/bass sustain is never bus-ducked or gain-ridden by this surface.

S27-M R2 ordering is deterministic: S15 timing offsets → section role velocity scales → targeted onset yields → legacy overlap-weighted yielding → optional role pan offsets. Realization remains idempotent.
