# S28-H — Piano Naturalism Production Closure

## Accepted chain

- S28-A R2: explicit continuous acoustic-piano sustain pedal state.
- S28-B: deterministic per-strike hammer/string excitation identity.
- S28-C: Composer-authored chord hand attack (`piano_attack_offset_ms`).
- S28-D: Composer-authored phrase timing/gate curves; random microtiming remains disabled in the closure dogfood.
- S28-G: subtle treble-unison decoherence while preserving 3 strings and the existing mean detune.
- S28-F production decision: the canonical source-piano baseline is **no automatic music-bus ducking**. Light ducking remains an explicit later ensemble/mix choice.

S28-E coupled-unison sustain is rejected and must not be reintroduced into this closure baseline.

## Closure dogfood

`Quiet Mechanics of Light` is a 16-bar / 24 kHz piano-only piece spanning low 1-string, middle 2-string and treble 3-string registers. It includes wide chords, repeated treble notes, pedal up/repedal and two directional phrase-timing/gate shapes.

The purpose is not to hide source artifacts with EQ, reverb, compression or sidechain ducking. It verifies the accepted piano source/performance chain in one coherent musical passage before ensemble work resumes.

## Authority

Composer Agent authors pedal timing, chord attack offsets and phrase timing/gate. The engine executes them deterministically. There is no genre keyword inference or blind random humanization.
