# S27-F — Drummer Limb / Performance Validator

Status: **CLOSED / USER PROCEEDED TO S27-G — 2026-09-20**

S27-D closed the last currently justified dry-source drum family. S27-F therefore does **not** reopen sound synthesis. Its job is to test whether a resolved drum performance can plausibly be produced by one drummer with two hands and two feet.

## Why this slice exists

A musically plausible drum score is not just a set of independent instrument lanes. Kick, snare, hi-hat, ride, crash and tom events compete for one performer's limbs and physical reach. Earlier Code Composer rhythm logic could emit or accept events without ever asking whether one drummer could actually execute the combination.

S27-F adds that missing evidence layer while preserving the Code Composer architecture rule:

`Composer Agent authors → deterministic runtime executes → analyzer reports evidence → Composer Agent revises`

The analyzer never rewrites notes, deletes hits, changes timing or invents sticking.

## Causal / physical model

Default compact kit model:

- right foot: kick;
- left foot: hi-hat pedal chick / foot splash;
- left + right hands: all stick-driven snare, tom, hi-hat, ride and crash events;
- hi-hat is on the left side of the reach proxy;
- snare / high tom / mid tom occupy the center region;
- floor tom / ride occupy the right side;
- a generic crash may be mounted left or right and is assigned to the lower-travel side.

The positions are normalized reach proxies, not measured drum dimensions and not audio pan values.

## Evidence classes

### Structural capacity — HIGH

- `DRUM_HAND_CAPACITY`: more than two exact-simultaneous stick events;
- `DRUM_RIGHT_FOOT_CAPACITY`: multiple exact-simultaneous kick-foot events;
- `DRUM_LEFT_FOOT_CAPACITY`: multiple exact-simultaneous hi-hat-foot events.

These mean the default one-drummer / four-limb model cannot execute the authored instant as written.

### Technique / strain — MEDIUM or LOW

- `DRUM_HAND_BURST_STRAIN`: 3+ hand attacks packed into a short near-simultaneous window; may be an intentional drag/ruff/rebound;
- `DRUM_HAND_RATE_EXTREME` / `DRUM_HAND_RATE_STRAIN`: demanding same-hand repeat interval after deterministic sticking assignment;
- `DRUM_HAND_TRAVEL_STRAIN`: large left↔right kit movement in a short interval;
- `DRUM_FOOT_RATE_EXTREME` / `DRUM_FOOT_RATE_STRAIN`: demanding same-foot repeats.

These do **not** automatically make the performance invalid. Advanced drummers can use rebound, doubles, heel-toe/slide pedal techniques, cross-handed layouts and nonstandard kit placement. S27-F therefore returns evidence rather than enforcing one player's skill ceiling.

## Research basis

- Scott, *Injury Prevention Considerations for Drum Kit Performance*, Frontiers in Psychology 2022: real drum-set upper-limb motion has been studied with 3D motion capture, supporting explicit movement/reach evidence.
- Fujii & Moritani, *Rise rate and timing variability ... world's fastest drummer*, J. Electromyography and Kinesiology 2012: single-hand repetition capacity varies strongly with expertise; this is why rate limits are strain evidence rather than a universal hard ban.
- Miksza et al., *The effect of musical groove on drum set performance accuracy*, 2025: drum-set performance is multi-effector motor coordination, supporting independent hand/foot occupancy analysis.

No motion-capture, EMG, participant timing, recordings or code from those studies are included.

## API

```python
from code_composer.analysis import analyze_drummer_performance

report = analyze_drummer_performance(resolved_ir)
```

Returned report includes:

- event and limb counts;
- deterministic hand/foot assignment trace;
- `playable` = no HIGH capacity contradiction;
- `strained` = MEDIUM/LOW technique evidence exists;
- sorted machine-readable issues;
- the thresholds used by the compact validator.

`pipeline.service.render_to_files(..., analysis_path=...)` automatically adds `analysis["drummer_performance"]` whenever resolved drum events exist and mirrors issues into the main analysis issue list with `source="drummer_performance"`.

## Preservation contract

S27-F must not modify:

- `audio/percussion.py`;
- S19 legacy kick/snare/closed-hat behavior;
- S27-A2 cymbal source;
- S27-B hi-hat source;
- S27-C snare source;
- S27-D tom source;
- authored event timing, velocity or drum identity.

## Closure gate

1. A normal 8-beat groove with kick + snare + hi-hat must be structurally playable.
2. Two hands + two feet on one downbeat must be allowed.
3. Three exact-simultaneous stick hits must produce HIGH hand-capacity evidence.
4. Same-foot duplicates must produce HIGH foot-capacity evidence.
5. Fast rudiment-like bursts must be evidence, not automatic score mutation.
6. High→mid→floor fills must receive deterministic plausible alternating-hand assignments.
7. Running the analyzer twice on the same IR must be identical.
8. Analysis must not mutate the IR.
9. Existing sound-engine source hashes remain unchanged.
