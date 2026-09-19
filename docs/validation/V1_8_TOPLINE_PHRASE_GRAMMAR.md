# v1.8 Topline Phrase Grammar

## Goal

Turn the topline from a repeated motif stream into phrase-level musical language while
preserving motif identity and deterministic rendering.

## Grammar

- call
- response
- tension call
- release response
- explicit breathing gaps
- response pickups
- scale-safe response variation
- tension lift
- cadence-preserving final phrase

## Dogfood QA

- topline events: 108
- call events: 25
- response events: 22
- tension-call events: 27
- release-response events: 26
- pickups: 8
- hook anchors: 11
- response variations: 6
- tension lifts: 9
- mean phrase gap: 1.151 beats
- call/response contour similarity: 0.369
- unique cadence endings: 4

## Melodic safety

- pitch range: 46 -> 46 semitones
- average leap: 4.222 -> 4.000 semitones
- large-leap ratio: 0.121 -> 0.112

The phrase grammar did not increase register instability.

## Whole-song QA

- analyzer issues: 0 -> 0
- energy correlation: 0.9886 -> 0.9886

## Determinism

SHA-256: `7c92eff7fb87d9fa871c385d06c8f9bab884c9c97c1e3ddc42e871f0f64a396e`

Repeated full-song render is byte-identical.
