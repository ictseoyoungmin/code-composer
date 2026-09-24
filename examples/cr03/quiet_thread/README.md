# CR03 Dogfood — Quiet Thread

Fresh-worker intent:

> 피아노와 바이올린으로 약 30초짜리 서정적인 곡을 만들어라.

This dogfood is intentionally authored as music, not as a metric target.

- 10 bars / 84 BPM / D minor
- acoustic piano + solo violin only
- piano establishes two bars of space before the violin enters
- violin stays mostly in D4–D5, reaches F5 once as a short apex, then descends
- phrase rests are explicit
- piano sustain is authored as pedal-control curves
- violin uses the modeled-admittance bowed-waveguide preset and receives mechanical realization after the score is fixed
- 24 kHz validation render

The Performance Score is the artistic authority for exact notes, voicing, register,
rhythm, dynamics, articulation, controls, and mix intent. The runtime may validate and
realize physical mechanics but must not change those authored note decisions.


## Section continuity reopen

Perceptual listening found that the Theme→Rise and Rise→Release boundaries could
read like a new piece starting because violin rest, bow reset, piano harmony change,
and pedal reset all happened together.

The revised score keeps the breath but preserves motion:

- violin boundary gaps: **0.08 beat** each;
- the preceding and following violin notes remain in the same legato bow group;
- the piano upper voice crosses each boundary briefly as a suspension;
- sustain uses a short half-lift/repedal gesture instead of a full stop/restart.

The modeled bowed renderer also keeps each physical string state alive across gaps.
Gap duration can attenuate the residual contribution, but no threshold destroys and
recreates a string state.
