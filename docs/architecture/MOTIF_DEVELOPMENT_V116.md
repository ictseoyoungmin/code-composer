# v1.16 Motif Development Architecture

Status: E2 CLOSED

## Execution order

```text
source motif
→ explicit transform chain
→ concrete motif statement
→ identity measurement / floor check
→ phrase note-event replacement
→ E1 Phrase Expression
→ renderer
```

E2 runs before E1 because pitch/rhythm identity must be established before velocity, timing, gate, articulation and breath are realized.

## Creative boundary

The deterministic engine may execute a structural operation, but it must not decide the new musical material.

Therefore:

- `fragment` requires explicit `start` + `length`
- `sequence` requires explicit scale-degree displacement
- `transpose` / `register_shift` require explicit semitones
- `rhythm_scale` requires an explicit factor
- `rhythm_rewrite` requires the new rhythm
- `cadence_rewrite` requires explicit replacement tail intervals, and optional explicit tail rhythm
- `ornament` requires insertion position + explicit intervals + explicit rhythm
- `response` requires the complete explicit response intervals + rhythm
- `call` is a lineage marker and leaves the current material unchanged

The old vague `amount` contract for cadence/response/ornament is removed.

## Identity evidence

The engine measures:

- normalized interval-shape retention
- contour retention
- relative-rhythm landmark retention
- first/apex/final anchor retention
- statement-length retention

These measurements are combined into a deterministic `identity.score`.

The Composer Agent supplies `identity_floor` as a quality target. Falling below it does not block rendering; the resolved statement records `identity_target_met=false` and E6 emits `MOTIF_IDENTITY_LOSS` so the Composer Agent can revise the structured plan.

When a composition genuinely requires a hard validity boundary, the Agent may additionally author `identity_hard_min`. Source-aware motif compilation fails only below this explicit hard minimum. `identity_hard_min` must be less than or equal to `identity_floor`. There is never an automatic substitution with a safer transform.

## Pitch realization

The statement intervals remain scale-relative structural offsets. A phrase uses its existing first note as the anchor; transformed scale-degree offsets are projected through the piece tonal scale. Semitone transforms are then applied explicitly.

E3 will own hard/preferred register enforcement. E2 intentionally does not solve voicing/range conflicts.

## Provenance

Resolved events carry `motif_statement` metadata with statement ID, source motif, transformed interval, semitone shift, identity score and floor. The resolved IR also stores the full `motif_development_report`, including transform traces.


## Call / response relation

`call` and `response` are explicit musical rewrites, not descriptive aliases.

```text
call
  → explicit intervals + rhythm

response
  → explicit intervals + rhythm
  → responds_to: earlier statement ID
```

The referenced statement must exist earlier in statement order and must itself contain a `call` transform. The relation is retained in `motif_development_report` and per-note provenance.
