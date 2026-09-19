> Superseded semantic note: H3 changes `identity_floor` from a hard compile threshold to a QA target and introduces optional `identity_hard_min`. See `H3_E2_SEMANTIC_CLOSURE.md`.

# v1.16 E2 — Motif Development

Status: CLOSED

## Execution order

```text
source motif
→ explicit Agent-authored transform chain
→ concrete motif statement
→ identity measurement / identity_floor check
→ phrase note/rhythm replacement
→ E1 Phrase Expression
→ renderer
```

## Supported transforms

`exact`, `fragment`, `sequence`, `transpose`, `register_shift`, `rhythm_scale`, `rhythm_rewrite`, `inversion`, `retrograde`, `cadence_rewrite`, `ornament`, `call`, `response`.

## Contract hardening

The earlier vague `amount` field is no longer accepted for cadence/ornament/response.

- cadence rewrite requires explicit replacement tail intervals and optional explicit tail rhythm
- ornament requires insertion position, explicit intervals and explicit rhythm
- response requires complete explicit response intervals and rhythm

The deterministic engine executes these instructions; it does not invent the replacement melody.

## Identity guard

Each statement carries an Agent-authored `identity_floor`. The engine measures interval-shape, contour, relative-rhythm landmarks, first/apex/final anchors and length retention. If the score is below the floor, validation fails. No automatic fallback transform is substituted.

## Validation boundary

Source-motif-dependent checks run before render when Performance IR is attached/validated:

- source motif must exist
- transform chain must execute structurally
- identity floor must pass
- transformed statement rhythm must fit its phrase window
- a statement-backed phrase must use a statement belonging to the same section

## Five-section dogfood

One source motif produced five concrete statement sequences:

- origin: exact, identity `1.0`
- memory: rhythm expansion + explicit cadence rewrite, identity `0.913929`
- bloom: first-half fragment + upward sequence, identity `0.774`
- stillness: three-note fragment + rhythm expansion, identity `0.7425`
- return: rhythm expansion + +3 semitone register shift + explicit cadence rewrite, identity `0.888929`

All five resolved note/rhythm sequences are distinct and every identity floor passes.

Dogfood WAV SHA-256:

`a4bc630fca2999c8b457aaf717c401126943bcd871f2cee7453a32b6a3073df4`

A second render from the same Music IR has the same SHA.

The broad legacy audio analyzer reports 12 section-energy/sparsity/transition issues on this intentionally sparse single-instrument fixture. Those are not E2 closure criteria; orchestration/transition/expressive QA are E4/E5/E6 work.

## Regression

- pytest: 154 / 154 PASS
- runtime modules: 108
- import edges: 119
- import cycles: 0
- import failures: 0

## Backward compatibility

No `performance_ir`:

`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

E1 == E2 byte-identical.

E1 phrase-only lyrical dogfood, with zero motif statements:

`4185c34b4b07310a259498f7e74aa5b78f147b5ed43b34d5f5c94d16b85db3de`

E1 == E2 byte-identical.

## Next

E3 — Register & Voicing.
