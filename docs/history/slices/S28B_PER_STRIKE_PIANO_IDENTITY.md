# S28-B — Deterministic Per-strike Acoustic-Piano Identity

Status: **ENGINEERING CANDIDATE / LISTENING GATE OPEN**

## Bottleneck

Repeated notes of the same MIDI pitch and similar duration were too close to replaying one finished acoustic model. Historical phase and hammer-noise identity were strongly tied to pitch / note geometry.

## Design

A new opt-in factory preset `piano.concert_grand_natural@1.0.0` enables bounded deterministic strike identity. The renderer derives a per-note strike seed from project seed + track identity + note ordinal + MIDI pitch. Non-note controls do not consume ordinals.

The strike seed only perturbs physical initial conditions within preset-authored bounds:

- global string phase;
- unison-string phase;
- partial phase;
- hammer-noise realization blend;
- small hammer gain / decay variation.

It does **not** alter authored pitch, onset, duration, velocity, form, harmony, or tempo. Same project + seed replays byte-identically. Historical piano presets keep all strike-identity controls at zero.

## Evidence

Eight identical C4 strikes with static identity have mean first-vs-later attack correlation ~`0.9999998`; the opt-in natural preset is ~`0.99219` while preserving bounded attack level and spectral centroid.

## Validation

S28-B focused tests cover legacy byte identity, same-seed determinism, bounded repeated-strike difference, pitch stability, control-insertion ordinal neutrality, factory control bounds, and seed sensitivity without score mutation.
