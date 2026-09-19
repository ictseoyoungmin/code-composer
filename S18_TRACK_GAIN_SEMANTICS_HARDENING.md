# S18 — Track Gain Semantics / Mixer Predictability Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Make `track.gain` predictable across instrument engines. A track-level gain change must be a pure linear fader operation and must not rewrite authored note velocity, excitation, brightness, articulation, or other performance/timbre controls.

## Bottleneck discovered by post-S17 dogfood

The post-S17 flagship song exposed an engine-dependent legacy behavior. In non-graph rendering, `track.gain` was multiplied into event velocity before synthesis. For velocity-sensitive piano and modeled violin this changed timbre/excitation as well as level, while modeled bass/percussion happened to follow the requested level ratio much more closely.

The mix-graph path already applied route gain after instrument rendering. S18 closes the semantic mismatch by making legacy `track.gain` a post-instrument linear fader too.

## Implemented semantics

- Note/event `velocity` remains performance authority.
- Instrument expression remains timbre/excitation authority.
- Legacy `track.gain` is applied once after instrument rendering, engine track post-processing, and legacy per-track insert FX.
- Graph-mode route gain remains unchanged in `mix_graph()` and continues to be post-render.
- Track pan semantics are unchanged in this slice.
- `track.gain == 1.0` preserves the pre-S18 instrument render exactly.
- No notes, rhythms, articulation, arrangement, ensemble interaction, or instrument presets are changed.

## Focused regression

S18 focused tests cover:

- acoustic piano linear fader behavior;
- S13 articulated violin linear fader behavior;
- S16 modeled bass linear fader behavior;
- S17 modeled percussion linear fader behavior;
- legacy delay/reverb insert path followed by the linear fader;
- unity legacy gain matching graph-mode dry rendering before routing;
- normalized waveform identity when only track gain changes.

Result: **7 / 7 PASS**.

## Full regression

- Source regression: **460 / 460 PASS** across **71 isolated test files**.
- Clean-installed wheel regression: **460 / 460 PASS** across **71 isolated test files**.
- No S13–S17 engine behavior was reopened.

## Dogfood — September Window, 5:42 PM gain-only excerpt

A 24 kHz excerpt from beats 72–80 of the post-S17 flagship song was re-rendered. R2 and R3 retain identical track/event state except for `track.gain`.

| Track | R2 gain | R3 gain | Expected ratio | Observed RMS ratio | Error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Violin lead | 0.19 | 0.24 | 1.2631578947 | 1.2631578947 | 0 |
| Piano pad | 0.115 | 0.075 | 0.6521739130 | 0.6521739130 | 0 |
| Modeled bass | 0.155 | 0.38 | 2.4516129032 | 2.4516129032 | 0 |
| Modeled drums | 0.72 | 0.62 | 0.8611111111 | 0.8611111111 | 2.22e-16 |

The original post-S17 mismatch is therefore closed under the same real composition material.

## Compatibility boundary

S18 intentionally changes the legacy/non-graph meaning of non-unity `track.gain`: it is now a mixer fader rather than a performance-velocity multiplier. This is a semantic correction, not a byte-compatibility promise for legacy projects that depended on non-unity track gain altering timbre.

The following remain preserved:

- gain=1.0 instrument rendering;
- graph-mode route gain behavior;
- event velocity and instrument-expression semantics;
- S13 articulated violin engine;
- S14 piano release/resonance hardening;
- S15 ensemble interaction;
- S16 modeled bass;
- S17 modeled percussion.

## Next

Return to full-song listening. Do not preselect S19. The next slice should be opened only from the next reproducible audible or authoring bottleneck.
