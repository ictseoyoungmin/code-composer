# v1.16 E5 — Musical Transitions

Status: CLOSED

## Canonical order

```text
Motif Development
→ Musical Transitions
→ Register & Voicing
→ Orchestration Budget
→ Phrase Expression
→ Renderer
```

E5 authors musical material before E3/E4 final structural constraints. E4 therefore remains the final role-budget gate.

## Explicit transition contract

The old ambiguous `amount`/density-style transition surface is not the E5 authority. The Agent must write concrete transition content.

### Harmonic anticipation
Requires role, target degree, scale-degree chord intervals, velocity and gate.

### Pickup
Requires role, explicit scale degrees, rhythm, octave and velocity.

### Bass approach
Uses an explicit operation (`step`, `chromatic`, `scale`, `pedal`), bounded duration, and explicit direction/step count where applicable. It approaches an existing destination bass event; if there is no destination, E5 fails rather than inventing one.

### Cadence extension / subtraction / silence
Cadence extension targets named roles. Texture subtraction targets named roles in a bounded pre-boundary window. `silence_beats` creates actual silence from existing material; explicitly authored pickup/anticipation/fill can then intentionally occupy that space.

### Register preparation
Each role specifies exact semitone shift + destination beat window. E3 runs afterward and restores hard-range/voicing invariants using octave-equivalent allocation.

### Rhythm fill
Fill events are explicit drum events with boundary-relative offsets, durations and velocities.

## Dogfood — Three Ways Across

Same base composition, no volume fades required. Three structurally different boundaries:

1. A→B: subtraction + 0.5-beat silence
2. B→C: harmonic anticipation + lead pickup + chromatic bass approach + explicit drum fill
3. C→D: lead cadence extension + lead/pad register preparation

A→B last-0.5-beat RMS:
- before E5: `0.093787`
- after E5: `0.000000`

Transition event counts:
- B→C harmonic anticipation: `3`
- B→C pickup: `2`
- B→C bass approach: `2`
- B→C rhythm fill: `2`
- C→D cadence-extended events: `1`
- C→D register-prepared events: `4`

## Determinism

Two independent E5 renders:
`0ec34de91e31e80543639ad1786459a504aaf6e10318a0df6437ddde26e5e6af`

Byte-identical: `True`

## Backward compatibility

E4 orchestration dogfood under E5:
`f28efa91a4a5856fb0add56a2dae092f854aab34954bad9d36a488cb9d3101fe`

Byte-identical to E4: `True`

Representative direct Music IR:
`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

## Regression

- pytest: 178 / 178 PASS
- runtime modules: 112
- import edges: 129
- import cycles: 0
- import failures: 0

## Scope boundary

The legacy broad audio analyzer may still call intentional silence or transition energy changes a generic sparsity/discontinuity issue. E6 is the slice that makes QA aware of the authored expressive/transition plan.
