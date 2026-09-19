# v1.3 Transition Material Dogfood

The first all-sections trial improved Verse and Hook B but regressed Hook A.
The canonical policy therefore uses per-section ACCEPT / REJECT plus calibrated strength.

## Canonical material

- Verse: strength 0.045
- Hook B: strength 0.40

Rejected: Hook A, Break, Final.

## Before / after

- Energy correlation: 0.9272 -> 0.9270
- Analyzer issues: 5 -> 3
- Verse discontinuity: 0.9912 -> 0.3920
- Hook B discontinuity: 0.7526 -> 0.2029

## Rule

Transition material is not globally accepted just because a boundary is flagged.
Each section may be accepted, rejected, or strength-calibrated independently.
Rejected bridge material never enters canonical IR.
