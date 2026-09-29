# AG05 — Arpeggio / Fingerstyle Performance

Status: **CANONICAL CLOSED · HUMAN LISTENING PASS**

Target release: **v1.19.0**

Dependency: AG01–AG04 CANONICAL CLOSED.

Canonical upstream:
- main: `9234b2fa2000b5bf51c8a4fb1d176903c634591b`
- AG01 R3 acoustic identity
- AG02 string/fret authority
- AG03 right-hand excitation semantics
- AG04 left-hand articulation semantics

## Ownership

AG05 coordinates **Composer-authored multi-string note sequences**. It does not
compose chord voicings, arpeggio patterns, note order, timing, or durations.

Each note may add:

```json
{
  "arpeggio": {
    "gesture_id": "c-major-arp-01",
    "player": "index",
    "voice": "inner",
    "sequence_index": 2
  }
}
```

Supported player roles:
- `thumb`
- `index`
- `middle`
- `ring`
- `pick`

Supported voice roles:
- `bass`
- `inner`
- `treble`

AG05 requires explicit AG03 right-hand authoring on every coordinated note.
It does not silently choose a player sound:
- thumb -> AG03 `right_hand.method=thumb`
- index/middle/ring -> AG03 `finger` or `nail`
- pick -> AG03 `pick`

## Multi-string execution contract

AG05 validates and records:
- exact authored sequence order;
- exact resolved AG02 string/fret;
- thumb/finger/pick role identity;
- independent string-state overlap;
- bass sustain underneath later inner/treble notes;
- repeated-finger evidence;
- same-string state collisions.

A gesture must:
- contain at least two events;
- span at least two resolved strings;
- use unique sequence indexes;
- have sequence order agree with strictly increasing authored onset;
- avoid stacking two independent AG05 note states on the same string at once.

If Composer wants a repeated same-string note, the previous authored duration must
release by the new onset. Stateful re-attack/coupling beyond that is AG08 scope.

## Frozen invariants

- no AG05 metadata -> AG04 canonical path unchanged;
- AG05 metadata itself is acoustically inert for an otherwise identical note;
- all audible picked-vs-fingerstyle differences come from explicit AG03 right-hand authoring;
- AG02 string/fret and AG04 left-hand semantics are never rewritten;
- MIDI, onset, duration and velocity remain exactly Composer-authored.

## AG06 boundary

AG05 is **not strumming**.

AG05 does not:
- synthesize down/up chord strokes;
- spread simultaneous chord notes automatically;
- derive string velocity from one stroke gesture;
- invent skipped/muted strings.

Those belong to AG06 Chord / Strum Mechanics, including the requirement that a
single stroke must not apply identical force to every traversed string.

## Closure gate

1. no-AG05 path preserves AG04;
2. AG05 metadata alone does not change an otherwise identical note render;
3. C/F authored voicings execute on their exact strings/frets;
4. bass notes overlap later inner/treble notes without collapsing to one chord trigger;
5. picked arpeggio and fingerstyle use identical authored note content/timing in evidence;
6. thumb/index/middle/ring/pick roles are explicit and validated against AG03 methods;
7. same-string independent overlap fails loudly;
8. AG01–AG04 evidence and full CI pass;
9. actual-pipeline 24 kHz C/F listening shows multi-string independent resonance;
10. explicit human listening PASS is required before merge.


## Closure evidence — 2026-09-29

AG05 closes after explicit human listening PASS on the C/F fingerstyle vs picked-arpeggio evidence.

Authoritative engineering evidence before closure metadata:
- PR #66 HEAD: `86b13ed119677be123173605394f437fcca09175`;
- CI #195 — SUCCESS;
- Python 3.10 / 3.12: 836 passed each;
- AG01 R3 Evidence #23 — SUCCESS;
- AG02 R3 Evidence #17 — SUCCESS;
- AG03 Right-Hand Evidence #15 — SUCCESS;
- AG04 Left-Hand Evidence #10 — SUCCESS;
- AG05 Arpeggio Evidence #3 — SUCCESS.

Accepted evidence:
- C: 5 independently overlapping strings, bass-under-upper overlap 8;
- F: 5 independently overlapping strings, bass-under-upper overlap 9;
- picked/fingerstyle pairs preserve identical MIDI/onset/duration/velocity/string/fret identity;
- evidence peak gate < 0.98 passes for all files;
- an invalid F same-string overlap was rejected and fixed in authored score rather than weakening validation.

Human verdict:
- C fingerstyle vs picked arpeggio: PASS;
- F fingerstyle vs picked arpeggio: PASS.

AG06+ must preserve AG01–AG05 closed invariants. Strum mechanics may derive micro-onsets
and per-string excitation from an authored stroke gesture, but may not silently rewrite
the chord voicing or bypass AG02–AG05 authority.
