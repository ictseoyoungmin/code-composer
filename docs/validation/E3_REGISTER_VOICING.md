# v1.16 E3 — Register & Voicing

Status: CLOSED

## Execution order

```text
Motif Development
→ Register / Voicing Allocation
→ Phrase Expression
→ Audio Renderer
```

E3 changes placement, not musical identity. A register operation may only choose an octave-equivalent MIDI note. It never changes pitch class to satisfy a constraint.

## Agent-authored register contract

Each role may define:

- `hard_range` — mandatory MIDI range
- `preferred_range` — soft target inside the hard range
- `center` — secondary register gravity
- `max_span` — maximum simultaneous voicing span
- `min_intervoice_distance` — simultaneous voice spacing
- `motion_policy` — `free`, `smooth`, `stepwise_preferred`, `oblique`, `contrary`
- `overlap_policy` — authored cross-role intent exposed to analysis

If no octave-equivalent candidate satisfies the hard plan, E3 fails explicitly instead of rewriting the note.

## Contour guard

The first allocator pass revealed a failure mode where a downward melodic cadence could be moved to the next octave because that was numerically closer to the register center. E3 now penalizes octave choices that reverse upstream melodic/voice-leading direction when a contour-preserving candidate exists.

This keeps register optimization subordinate to E2 motif identity.

## Voicing allocation

Simultaneous notes are allocated as a group. Candidate voicings must satisfy:

- hard range
- pitch-class preservation
- ascending voice order
- `max_span`
- `min_intervoice_distance`

The deterministic cost then considers preferred range, center, source-octave displacement and the Agent-authored motion policy.

## Register Collision Analyzer

E3 adds symbolic collision evidence:

```text
collision = time overlap × within-octave pitch proximity × authored role importance
```

The analyzer also carries each role's `overlap_policy` as intent metadata. It does not decide that a collision is artistically wrong.

## Dogfood

One piano/pad/arp phrase was intentionally authored with all three roles crowded in the middle register. Notes, rhythm, instruments and mix were frozen.

Collision score:

```text
Crowded source     35.176508
Initial E3 plan    6.056083
Agent revision     0.000000
```

The second pass changed **register plans only**. Final realized ranges:

- lead: MIDI 62–69
- pad: MIDI 37–49
- arp: MIDI 86–97

The final collision score is zero under the E3 measurement window.

Final E3 WAV SHA-256:

`002f9ba2511ac082d803ba2e3421d112cc425f386a4cd9be8a254c532c7b0607`

Repeated render is byte-identical.

## Regression

- pytest: 163 / 163 PASS
- runtime modules: 110
- import edges: 123
- import cycles: 0
- import failures: 0

## Compatibility

Direct Music IR without Performance IR remains byte-identical to E2:

`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

The E1 phrase-only Lyrical fixture also remains byte-identical under E2 and E3 because its notes already satisfy its authored register plan:

`4185c34b4b07310a259498f7e74aa5b78f147b5ed43b34d5f5c94d16b85db3de`

## Scope boundary

E3 does not yet decide which roles should be active or decorative at each moment. That is E4 — Orchestration Budget.
