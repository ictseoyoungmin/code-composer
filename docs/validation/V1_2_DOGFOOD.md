# v1.2 Adaptive Transition Dogfood

Study: `Sunlit Static`

## Before / after

Energy correlation:
- before: 0.9312
- after: 0.9272

Analyzer issues:
- before: 7
- after: 5

Transition discontinuity:

- hook_a: 0.9569 → 0.6025 (-37.0%)
- verse: 0.9993 → 0.9912 (-0.8%)
- hook_b: 0.7754 → 0.7526 (-2.9%)
- break: 0.9075 → 0.4888 (-46.1%)
- final: 0.8582 → 0.4704 (-45.2%)

## Finding

Symmetric transition dips failed because every measured boundary in this study was an
`up` transition: the pre-boundary window was much quieter than the incoming section.

v1.2 therefore uses direction-aware, one-sided automation:
- low → high: attenuate only the incoming side, then recover
- high → low: attenuate only the outgoing side, restore unity at the boundary

This materially improved Hook A, Break and Final.

The Verse transition remains extreme because its pre-boundary RMS is effectively silence.
Gain automation cannot create missing transition content. That should be addressed by a
future transition-fill / tail / pickup layer rather than by ever-stronger mastering.
