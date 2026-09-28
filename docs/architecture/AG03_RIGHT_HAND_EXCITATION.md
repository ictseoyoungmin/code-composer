# AG03 — Right-Hand Excitation

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01 R3 and AG02 CANONICAL CLOSED.

Canonical upstream:
- main: `8e076f8370bb6ce89beee9fb6eca4cc5b1b56461`
- AG01 tone: `ag01_modal_bridge_body_v2` + `triangular_pluck_bridge_force_v2`
- AG02 authority: standard six-string string/fret realization

## Authored contract

AG03 extends `instrument_performance` with an isolated nested object:

```json
{
  "string": 1,
  "fret": 0,
  "right_hand": {
    "method": "pick",
    "pluck_position": 0.11,
    "attack_angle_deg": 35.0,
    "strength": 0.7
  }
}
```

Supported methods:
- `finger`
- `thumb`
- `nail`
- `pick`

The optional controls are:
- `pluck_position`: normalized string position in [0.03, 0.49];
- `attack_angle_deg`: [0, 90];
- `strength`: [0, 1].

No right-hand payload means no AG03 realization is attached.

## Physical ownership

AG03 changes excitation only. It does not retune the guitar body, global EQ,
string/fret identity, authored pitch/timing, or deterministic noise seed.

The method layer controls bounded changes to:
- bridge-force partial rolloff;
- release/contact ramp duration;
- contact-burst gain;
- contact-burst high/low spectral bounds;
- contact-burst decay;
- authored pluck position.

Attack angle and strength add small continuous deltas. Authored velocity affects
excitation spectrum only when AG03 mechanics are explicit.

## Frozen upstream invariants

- no AG03 mechanics -> AG02 canonical output sample-exact;
- neutral explicit reference at the canonical pluck position -> sample-exact;
- AG02 string/fret realization remains unchanged;
- body modes and bridge/body coupling are untouched;
- no new random seed or phase identity is introduced.

## Provenance

Authored intent remains in `performance.instrument.right_hand`.
Resolved mechanics are attached as `performance.right_hand_realization` and
reported under `guitar_performance_report.tracks[*].right_hand_events`.

## Closure gate

1. no-right-hand and neutral reference are sample-exact with AG02 canonical;
2. finger/thumb/nail/pick preserve authored method identity and are deterministic;
3. same pitch/string/fret/velocity produces distinct method-dependent excitation;
4. method deltas remain bounded and do not become a new instrument identity;
5. pluck position, attack angle and strength produce deterministic changes;
6. invalid/future AG03 fields fail loudly;
7. authored MIDI/onset/duration remain unchanged;
8. blocking CI and upstream AG01/AG02 preservation evidence pass;
9. actual-branch 24 kHz listening evidence compares the same pitch/string/fret/velocity;
10. explicit human listening PASS is required before merge.
