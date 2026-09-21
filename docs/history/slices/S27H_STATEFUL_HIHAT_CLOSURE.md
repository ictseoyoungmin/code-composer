# S27-H — Stateful Hi-Hat Closure / Choke

Status: **CLOSED / USER PROCEEDED TO S27-I — 2026-09-20**

## Why this slice exists

S27-B closed the sound of six explicit hi-hat articulations, but each hit was still rendered independently. An `hat_open` tail therefore continued to ring even after an explicitly authored pedal chick or later closed state. S27-H closes only that time-domain state gap.

## Boundary

Locked: S19 kick, S27-A2 ride/crash, S27-B hit synthesis, S27-C snare, S27-D toms, S27-F limb validator, S27-G shared room.

New: opt-in `drum_graph.hi_hat_state` / `authored_closure_damping_v1`.

No continuous pedal trajectory, no inferred groove grammar, no automatic choke event, no global mix gate.

## Causal behavior

An earlier `hat_open`, `hat_half_open`, or foot-splash tail owns its own residual energy. A later authored state that is physically more closed applies a smooth exponential loss envelope to that earlier event only. Half-open retains a substantial residual; closed/tight/pedal dissipate progressively more. Since the envelope starts at unity there is no sample discontinuity at the transition.

The closure event itself is synthesized unchanged, and all non-hi-hat voices bypass the state layer. Shared-room integration is applied after the stateful dry mix, so the room can decay naturally even when the source plates are quickly choked.

## Preset

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat@1.0.0`

It is byte-identical to the S27-G patch except for the new `hi_hat_state` block.

## Closure gate

1. open -> pedal sounds like physical contact stopping already-moving plates, not a fader automation;
2. open -> half-open is partial rather than full choke;
3. open -> closed/tight is fast but click-free;
4. the closure hit itself keeps its accepted S27-B timbre;
5. kick/snare/ride/tom are not ducked when the hat closes;
6. shared room retains plausible short ambience without reviving the rejected long cymbal smear;
7. actual groove passes S27-F and sounds more like one continuously operated hi-hat instrument.

## Closure

User proceeded to the next slice on 2026-09-20 after the S27-H audition package. S27-H is CLOSED and becomes the discrete authored closure baseline for S27-I.
