# S28-A — Continuous Acoustic-Piano Sustain Pedal State

Status: **CLOSED — R2 USER PERCEPTUAL PASS**

## Why this slice exists

Production listening identified a structural piano problem larger than the remaining S27 ensemble polish: acoustic sustain was encoded primarily as a note-local `performance.pedal = true` flag. In that model a note selects `pedal_release_s` and can keep ringing long after a harmony change even if a real pianist would briefly release and repedal.

S28-A does not tune reverb, EQ, or bus ducking. It introduces an explicit performer control state so harmony clearing belongs to the piano performance model.

## New authored control

```json
{
  "event_type": "piano_control",
  "control": "sustain_pedal",
  "start_beat": 0.0,
  "duration_beats": 4.0,
  "points": [
    {"offset_beats": 0.0, "position": 1.0},
    {"offset_beats": 3.86, "position": 1.0},
    {"offset_beats": 3.94, "position": 0.0},
    {"offset_beats": 4.0, "position": 0.0}
  ]
}
```

`position` is normalized from `0 = released` to `1 = fully down`. Curves are sequential and their final position persists until the next authored curve. This makes pedal down / up / repedal explicit without inferring motion from harmony or genre.

## Runtime semantics

- Tracks with no `piano_control` events stay on the historical note renderer.
- Once an acoustic piano track contains explicit sustain control, the pedal timeline becomes authoritative over note-local pedal booleans.
- If a key is released while the pedal is down, that string is kept undamped only until the next authored down→up threshold crossing.
- At pedal-up, S14's ordinary damper release is used. Another `pedal_release_s` tail is **not** attached.
- A later repedal does not resurrect a note that has already been damped.
- Track-wide soundboard / sympathetic coupling follows the explicit pedal envelope with short causal smoothing.
- Electric-piano pedal control is intentionally out of scope for this slice.

## Legacy compatibility

Legacy note-local `performance.pedal` projects take the old path when no explicit piano control is present. Existing piano render tests remain deterministic and byte-stable within their historical path.

## Dogfood

`tools/s28a_continuous_piano_pedal_dogfood.py` renders a 92 BPM four-harmony piano passage twice with identical notes/velocities:

1. historical note-local `pedal=true`;
2. S28-A explicit pedal lift + repedal at each harmony boundary.

For the first chord rendered in isolation, residual RMS measured 300–1200 ms after the following bar boundary:

- legacy note-local pedal: `0.05332677`
- S28-A explicit pedal-up: `0.00005948`
- ratio: `0.0011154` (~0.11%)

This is evidence that the previous harmony is actually cleared by the pedal state instead of being masked with mix processing.

## R1 / R2 perceptual reopen

The first S28-A candidate cleared old harmony correctly but exposed a synthetic `wah/meow` release. R1 removed a synchronized side-string collapse but user listening still found the artifact. R2 isolated the remaining interaction:

- detuned unison beating remained coherent under one common release envelope;
- fixed soundboard modal state could continue after strings had already damped.

R2 keeps detuning during the struck note, then models pedal-up as short staggered felt contact across all unison strings plus a shorter post-lift fixed-modal body state. No pitch sweep or mix masking is used. User listening accepted R2.

## Validation

- original S28-A focused: **8/8 PASS**
- original full repository: **88 test files / 597/597 PASS**
- R2 piano focused: PASS before the next slices
- R2 user perceptual gate: **PASS / CLOSED**

## Deferred

S28-A deliberately does **not** address the other piano-naturalism blockers yet:

- deterministic per-strike hammer/string/soundboard identity;
- Composer-authored chord micro-roll / hand attack;
- phrase-direction onset and gate timing;
- final audit of drum→music-bus ducking.

The next piano slice should be chosen from those remaining audible blockers after S28-A production listening.
