# AG04 — Left-Hand Articulation / Damping

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01 R3, AG02 and AG03 CANONICAL CLOSED.

Canonical upstream:
- main: `badb65ba9d67f8664d6c7e01510eb2f230158b3d`
- AG01 R3 acoustic identity
- AG02 string/fret authority
- AG03 right-hand excitation semantics

## Authored contract

AG04 extends `instrument_performance` with an isolated nested object:

```json
{
  "string": 1,
  "fret": 3,
  "left_hand": {
    "technique": "hammer_on",
    "transition_ms": 11
  }
}
```

Supported techniques:
- `palm_mute`
- `fretting_mute`
- `dead_note`
- `slide`
- `hammer_on`
- `pull_off`
- `natural_harmonic`

Optional controls:
- `amount`: 0..1 for damping intensity;
- `transition_ms`: 4..240 for slide/hammer/pull destination transition;
- `harmonic_order`: 2..5 for natural-harmonic mode family.

Artificial harmonic remains outside the narrow AG04 closure unless later evidence
shows it can be added without reopening the accepted scope.

## Physical ownership

AG04 owns left-hand/damping mechanics only.

Mute/dead-note mechanics affect:
- source decay;
- frequency-dependent damping;
- tonal/string-energy scale;
- contact/noise balance;
- post-gate residual decay.

Natural harmonic:
- preserves authored MIDI as the sounding pitch;
- reindexes surviving string modes by the authored harmonic order;
- reduces stiffness-like inharmonicity;
- does not retune body modes or global EQ.

Slide / hammer-on / pull-off:
- require a preceding pitched guitar note;
- require the same resolved AG02 string;
- preserve authored destination MIDI/fret;
- attach explicit source/destination fret provenance;
- use a continuous time-varying pitch phase over the transition window;
- suppress the destination pluck excitation;
- add only a small deterministic fret-contact transient.

Hammer-on must move upward and pull-off downward. A destination transition event may
not simultaneously author a new AG03 `right_hand` strike.

## Frozen upstream invariants

- no AG04 mechanics -> AG03 canonical output sample-exact;
- AG02 string/fret authority is not rewritten;
- AG03 right-hand semantics are not rewritten;
- body modes, global EQ, deterministic seed, authored pitch/onset/duration remain unchanged;
- downstream slices must preserve these invariants or explicitly REOPEN AG04.

## Provenance

Authored intent remains in `performance.instrument.left_hand`.
Resolved mechanics are attached as `performance.left_hand_realization` and
reported under `guitar_performance_report.tracks[*].left_hand_events`.

## Closure gate

1. no-left-hand path is sample-exact with AG03 canonical across E2/E3/E4;
2. mute/dead/harmonic preserve authored note identity and are deterministic;
3. mute/dead techniques produce physically ordered damping differences;
4. natural harmonic changes mode participation without changing authored sounding MIDI;
5. slide/hammer/pull require same-string predecessor state;
6. hammer/pull destination cannot create a new right-hand pick attack;
7. slide uses a continuous source→destination pitch trajectory;
8. invalid/future AG04 fields fail loudly;
9. AG01/AG02/AG03 preservation evidence and full CI pass;
10. actual-branch 24 kHz single-note and transition-phrase evidence passes human listening.
