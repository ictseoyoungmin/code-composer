# AG07 — Percussive Guitar Performance

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01–AG06 CANONICAL CLOSED.

Canonical upstream:
- main: `d90b2543e90fcdb79bb2b725d5b11d001d0b3f4b`
- AG01 tone identity
- AG02 string/fret authority
- AG03 right-hand excitation
- AG04 left-hand articulation
- AG05 multi-string/arpeggio authority
- AG06 continuous strum gesture

## Ownership

AG07 uses the existing Performance Score `instrument_action` event for percussive
acoustic-guitar actions. It does not create a separate drum track.

Supported actions:
- `body_tap`
- `top_slap`
- `bridge_hit`
- `string_slap`
- `muted_strum`
- `dead_strum`
- `nail_click`

Example:

```json
{
  "id": "slap-1",
  "type": "instrument_action",
  "start_beat": 2.0,
  "duration_beats": 0.08,
  "action": "top_slap",
  "parameters": {
    "strength": 0.62,
    "location": "soundboard"
  }
}
```

## Same-guitar resonator invariant

AG07 does **not** route these actions through the percussion engine and does not
use drum samples or impulse responses.

Each action creates a deterministic mechanical contact/excitation signal and
feeds it through the same `radiate_acoustic_guitar_body()` stage used by the
accepted pitched acoustic-guitar model.

Location changes excitation/coupling spectrum, not the guitar body's accepted
modal frequencies. Supported locations:
- lower_bout
- upper_bout
- soundboard
- bridge
- strings
- rim

## Action semantics

### body_tap / top_slap / bridge_hit / nail_click

These are body/contact excitations with different low/high/contact balance.
Location influences how the fixed body resonator is excited.

### string_slap

Produces short deterministic string/fretboard contact energy without adding a
stable authored musical pitch. The result still radiates through the same body.

### muted_strum / dead_strum

Produces multiple correlated string-contact bursts along one authored traversal.
Supported parameters:
- direction: down / up
- traversal_ms: 6..180
- string_count: 2..6
- strength

This is a percussive action, not an AG06 pitched chord stroke. AG06 continues to
own pitched chord traversal; AG07 owns the non-pitched contact action.

## Simultaneous note + action

A note event and an AG07 instrument_action may share the same authored onset.
Examples:
- thumb bass + top slap;
- ringing fingerstyle note + body tap;
- note phrase + bridge hit accent.

AG07 must not rewrite the note's pitch, string/fret, onset, duration, right-hand,
left-hand, arpeggio, or strum realization.

## Patch scope

AG07 instrument actions are enabled only for the accepted R3 acoustic-guitar
patch family:
- physical_model = `ag01_modal_bridge_body_v2`
- string_source_model = `triangular_pluck_bridge_force_v2`

Older/provisional acoustic-guitar patches reject AG07 actions.

## Determinism / provenance

Performance Score action identity, action name, start, duration and parameters
remain authoritative in the render IR. The renderer derives only a deterministic
action seed from global seed + track identity + action ordinal.

## Frozen invariants

- no instrument_action -> AG06 path unchanged;
- AG01–AG06 note mechanics remain untouched;
- no percussion engine or drum-event substitution;
- no external samples/IRs;
- note + action simultaneity preserves note authority.

## Closure gate

1. all seven actions compile on canonical patch;
2. provisional/foundation patch rejects AG07 actions;
3. repeated render of identical action is deterministic;
4. action peak remains < 0.98 without per-event normalization;
5. body locations are audibly/quantitatively distinct;
6. all actions pass through same acoustic body radiation path;
7. muted/dead strum down/up contact sequences remain distinct;
8. note + action same-onset pipeline preserves note pitch/onset/duration;
9. thumb-bass + top-slap combined evidence sounds like one guitar performance;
10. muted/dead/string slap read as guitar string/body contact, not generic drums;
11. AG01–AG06 preservation evidence + full CI pass;
12. explicit human listening PASS before merge.
