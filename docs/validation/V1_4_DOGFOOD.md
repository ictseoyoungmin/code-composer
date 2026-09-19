# v1.4 Dogfood — Energy Calibration + Pre-Hook Build

## Result

The v1.3 canonical study had three remaining analyzer issues:
- Intro too strong
- Verse too strong
- Hook A abrupt transition

v1.4 closes all three.

### Section calibration
Intro and Verse use conservative `section_gain = 0.74`.

### Hook A build grammar
Hook A uses:
- outgoing drum withdrawal
- calibrated snare pickup
- pad swell
- one quiet melodic pickup

### State-model correction
Accepted v1.3 transition material keeps its own frozen source analysis.
New Hook A evaluation uses a separate `pre_hook_analysis`.

This avoids the recursion problem where a previously successful transition would
disappear on a later render merely because the latest analysis already showed it fixed.

## Final metrics

- energy correlation: 0.9270 → 0.9885
- analyzer issues: 3 → 0
- deterministic: True
