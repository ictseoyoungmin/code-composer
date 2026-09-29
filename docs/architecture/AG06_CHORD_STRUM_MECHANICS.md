# AG06 — Chord / Strum Mechanics

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01–AG05 CANONICAL CLOSED.

Canonical upstream:
- main: `e1d772c87e6c994a5493424332d145c6f3acbaab`
- AG01 R3 acoustic identity
- AG02 string/fret authority
- AG03 right-hand excitation semantics
- AG04 left-hand articulation semantics
- AG05 multi-string/arpeggio authority

## Core ownership

AG06 models one chord stroke as **one continuous shared gesture**.

A stroke is not a set of independent per-string velocity values and it is not
random humanization. Every traversed string samples a local state from the same
deterministic gesture.

Each chord note carries the same shared `strum` gesture payload plus an optional
per-string state:

```json
{
  "strum": {
    "stroke_id": "F-down-01",
    "direction": "down",
    "traversal_ms": 28,
    "entry_strength": 0.62,
    "acceleration": 0.1,
    "pick_depth": 0.58,
    "attack_angle_deg": 42,
    "follow_through": 0.72,
    "accent_position": 0.5,
    "accent_amount": 0.0,
    "from_string": 6,
    "to_string": 1,
    "state": "sounding"
  }
}
```

All shared fields must be identical for every note in one `stroke_id`. `state`
may be `sounding` or `muted`.

## Composer authority

The Performance Score owns:
- chord pitches;
- string / fret voicing;
- nominal chord onset;
- note duration;
- note velocity;
- AG03 right-hand method;
- AG04 mute/dead articulation when used.

AG06 does not rewrite those canonical values.

The realizer derives:
- traversal index / position;
- render-local contact offset in milliseconds;
- correlated local force;
- bounded render-local velocity scale.

The renderer applies the derived offset and effective velocity only to render-local
event copies. Canonical IR start/velocity remain unchanged.

## Direction / traversal

Standard guitar numbering is retained:
- string 6 = low E side;
- string 1 = high E side.

Therefore:
- downstroke traverses high string number → low string number, e.g. 6→1;
- upstroke traverses low string number → high string number, e.g. 1→6.

Absent note events inside the authored traversal span are **skipped strings**.
They remain part of the hand path and therefore consume traversal time, but produce
no pitched excitation.

A `muted` string must explicitly use AG04 `fretting_mute` or `dead_note`.
AG06 never invents a mute.

## Deterministic force profile

Per-string force is a bounded function of shared gesture state and traversal
position. The profile includes:
- entry/exit trajectory;
- acceleration;
- stroke speed;
- pick/finger depth;
- attack angle;
- follow-through;
- direction-specific load tilt;
- local accent envelope.

There is **no per-string random draw**.

Consequences:
- all strings must not receive identical excitation;
- down/up are not merely reversed note order;
- fast vs slow changes force distribution as well as onset spacing;
- an accent affects a local region of the stroke rather than scaling all strings uniformly.

## Frozen invariants

- no AG06 metadata preserves the AG05 path;
- AG01–AG05 realization metadata remains authoritative and is never rewritten;
- a strum note cannot also be owned by AG05 arpeggio;
- AG06 never invents chord notes or a chord shape;
- AG06 never changes canonical MIDI/start/duration/velocity.

## Closure gate

1. real C / F / G / Am voicings are used;
2. down/up traversal order is mechanically correct;
3. one nominal chord onset remains unchanged in canonical IR;
4. render-local micro-onsets follow stroke traversal;
5. per-string force is deterministic, correlated and non-uniform;
6. no independent random humanization is used;
7. fast stroke vs slow rake changes both onset spacing and force distribution;
8. local accent produces non-uniform force ratios;
9. skipped strings consume traversal distance without sounding;
10. muted/dead strings require explicit AG04 mute state;
11. pick and finger stroke evidence is included;
12. all evidence files satisfy peak < 0.98;
13. AG01–AG05 evidence + full CI pass;
14. actual-pipeline 24 kHz listening confirms realistic chord stroke direction and force distribution;
15. explicit human listening PASS is required before merge.
