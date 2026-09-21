# S27-K — Hi-Hat Foot Gesture / Chick–Splash Coupling

Status: **R1 ENGINEERING CANDIDATE / perceptual gate OPEN**

## Why this slice exists

S27-I/J made pedal openness an explicit continuous and persistent left-foot state, but the accepted S27-B `hat_pedal` / `hat_foot_splash` sounds were still independent fixed events. A fast authored close therefore changed state without producing the cymbal-cymbal collision it physically implies, while an explicit splash could be triggered without any pedal motion. S27-K closes only that causal gap.

## Boundary

Locked: S19 kick, S27-A2 ride/crash, S27-B two-plate source family, S27-C snare, S27-D toms, S27-F limb validator, S27-G shared room, S27-H discrete choke, S27-I continuous residual-energy damping, S27-J persistent pedal-coupled stick excitation.

No groove generator, genre-specific foot pattern, hidden control trajectory, sample layer, or third-party audio is added.

## Implementation

The S27-K opt-in preset originally added `hi_hat_state.pedal_audio.model = authored_motion_collision_v1`; R1 advances the control-derived path to `authored_motion_microcontact_v2`. The existing `drum_control / hi_hat_pedal_openness` curve stays the authored performance source. Runtime derives only its physical acoustic consequences:

- fast close crossing the contact threshold -> `hat_pedal` two-cymbal chick excitation;
- fast reopen from a genuinely clamped state -> `hat_foot_splash` release excitation;
- slow close/reopen -> no standalone foot transient;
- partial motion that never reaches contact -> no standalone foot transient.

Velocity is bounded from authored openness speed in seconds, not from genre/style labels. Generated control audio uses its own deterministic control seed so later audible drum-hit RNG identity is unchanged.

## Preservation

- S27-J preset control events remain non-audio.
- Direct `hat_pedal` / `hat_foot_splash` / stick / kick / snare / ride sources are byte-exact to S27-J.
- Slow-close S27-J -> S27-K isolated render is sample-exact.
- S27-F still counts one authored `drum_control` as one left-foot action; the derived chick/splash consequence is not a second performance event.

## Dogfood

24 kHz / 116 BPM / 4 bars:

- 47 timeline events = 41 audible hits + 6 authored pedal controls;
- hands 26 / right foot 15 / left foot 6;
- playable=true / strained=false / HIGH/MEDIUM/LOW = 0/0/0;
- whole-room raw RMS S27-J `0.13401324` -> S27-K `0.13403392`; RMS-match gain `0.99984573`;
- fast-close standalone S27-K RMS `0.00418079` vs silent S27-J control;
- slow-close S27-J/S27-K max abs diff `0.0`;
- fast close/reopen splash late RMS 180-420 ms `0.00081389`.

Primary audition: `05_GROOVE_S27J_then_S27K_ROOM_RMS_MATCHED.wav`.

## Validation

- S27-K focused: 10/10 PASS.
- full repository: 85 test files / 575/575 PASS (partitioned).
- Skill self-check / validate_skill / plugin distribution / compileall / Skill·Codex·Claude build required before packaging.

## Provenance

Continues the same independently implemented causal reading of Sekiguchi & Samejima (2023), *Physical modeling and sound synthesis of the hi-hat*, DOI `10.1250/ast.44.352`: pedal-driven separation/contact can create cymbal-cymbal collision and release behavior. Code Composer does not copy or bundle the paper's solver, source code, numerical parameter table, shell geometry, meshes, figures, audio, or measurement data. `CREDITS.md` is current through S27-K.

## Perceptual closure gate

1. fast close sounds like a compact physical chick, not an extra sequenced sample;
2. fast close/reopen sounds like a foot splash with a freer plate release;
3. slow pedal pressure change does not create an artificial click/chick;
4. the control-derived sound sits inside the same S27-G shared kit/room rather than outside it;
5. S27-J persistent pedal/strike behavior remains intact.


## R1 reopen — user crackle report

The user reported a small `지직/틱` noise trailing the new foot gesture. Differential inspection isolated it to `_hat_collision_texture()`: sparse two-sample edge-contact impulses remained audible after the main chick/splash body decayed, especially in the longer splash collision window. This is treated as an artifact, not cymbal realism.

R1 preserves the historical collision path byte-exact when no profile is supplied and adds a **foot-control-only** micro-contact profile:

- short raised-sine contact pulses instead of two-sample bipolar impulses;
- moderately higher aperiodic contact density;
- lower collision gain;
- direct `hat_pedal` / `hat_foot_splash` sources remain byte-exact to the locked pre-R1 path.

Measured with the same 24 kHz / same-seed control gestures:

- chick 20–160 ms max sample step: `0.24936 -> 0.03877`; crest `16.89 -> 11.78`;
- splash 180–420 ms max sample step: `0.08415 -> 0.00342`; crest `28.81 -> 14.77`;
- slow-close remains silent;
- whole 4-bar room RMS: old S27-K `0.13403392` -> R1 `0.13401851`, RMS-match gain `1.000115`.

R1 regression adds two explicit crackle guards; full repository result: **85 test files / 577/577 PASS**.

## R2 reopen — production felt/fabric noise

The 15-second production gate exposed a different artifact after R1: the denser smoothed micro-contact field no longer clicked, but read as a soft felt/fabric/sandpaper stepping noise under the mix. This is treated as an implementation artifact, not physical hi-hat ambience.

R2 changes only control-derived foot audio:

- `pedal_audio.model = authored_motion_plate_contact_v3`
- control-derived chick/splash additive collision gain = `0`
- existing two-plate + contact-radiation response remains the audible source
- chick/splash output is calibrated with bounded gesture gains (`2.0` / `1.25`)
- direct `hat_pedal` / `hat_foot_splash` remain byte-exact
- authored gesture thresholds, motion semantics, persistent pedal state, and S27-F limb accounting are unchanged

Closure is again production-listening first. The same 112 BPM / 7-bar / exactly 15.0 s `Cobalt Pulse` arrangement is used so the only intended sonic difference is the control-foot contact path.
