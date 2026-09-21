# S27-B R1 — Resonant Metal Hi-Hat Collision Rework

Status: ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN
Date: 2026-09-20

## Why S27-B was reopened
Production listening of S27-K R2 still exposed a felt/fabric/sandpaper-like layer. With the S27-K control-derived additive collision field already disabled, the remaining texture was traced to the original S27-B `_hat_collision_texture()` path used by stick hi-hat articulations themselves. The path emitted a peak-normalized 3.6–11.2 kHz broadband collision signal directly into the source.

## Scope
- Keep the accepted two-plate topology, plate-state hierarchy, persistent pedal state, S27-K explicit foot controls, shared room, snare/tom/cymbal sources and Composer-Agent authority.
- Reopen only the hi-hat collision radiation mechanism and dependent level calibration.
- Do not alter historical presets; add one new opt-in factory preset.

## New source model
`hi_hat_mechanics.model = two_plate_modal_contact_v2`
`hi_hat_mechanics.collision_model = modal_plate_excitation_v2`

Irregular edge re-contact events now create finite raised mechanical force pulses. Those forces excite a dense high-order inharmonic mode cloud. No collision pulse/noise train is normalized and emitted directly as sound. The audible collision contribution is therefore metal plate radiation.

## Engineering evidence
- New focused regressions: 8/8 PASS.
- Related S27-B/S27-K/factory regressions: 40/40 PASS during initial tuning; expanded hi-hat/factory/maintenance gate: 75/75 PASS.
- Half-open 3–11 kHz spectral flatness drops from the rejected broadband behavior (~0.82 in the selected seed) to a structured modal field while dominant-bin power remains bounded.
- Locked stick-hat whole-source RMS is preserved within the acceptance envelope rather than collapsing when broadband collision energy is removed.
- Open-state late decay remains longer than half-open chatter.
- Non-hi-hat drum sources remain byte-exact.
- S27-K R2 authored pedal chick/splash remains audible and bounded.

## Production gate
`Cobalt Pulse` is rerendered with the exact 24 kHz / 112 BPM / 7-bar / 15.000 s arrangement, global seed and mix used for S27-K R2. The production master RMS remains essentially unchanged; the intended audible difference is the hi-hat collision texture.

## Final engineering validation
- Full repository: **86 test files / 585/585 PASS** (partitioned due environment command-duration limits).
- standalone Skill self-check: PASS.
- `tools/validate_skill.py`: PASS.
- `tools/verify_plugin_distribution.py`: PASS.
- `compileall`: PASS.
- Skill/Codex/Claude builds: PASS.
- GitHub write: none.

## Closure
Do not mark CLOSED until user listening confirms that the felt/fabric friction quality is gone and the replacement still reads as a natural metal hi-hat rather than a bell or synthetic resonator.
