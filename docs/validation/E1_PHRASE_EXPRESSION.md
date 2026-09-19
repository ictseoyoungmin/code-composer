# v1.16 E1 — Phrase Expression

Status: CLOSED

## Execution position

```text
arrangement / resolved note events
→ Performance IR phrase realization
→ final resolved Music IR events
→ audio synthesis
```

Expression is stored in Music IR before rendering; it is not an audio-only post effect.

## Implemented semantics

### Dynamic curve

`dynamic_curve` is the Agent-authored final normalized velocity target.

It is not a multiplier over random base velocity.

### Timing curve

`timing_curve_ms` is an explicit onset offset from the underlying musical event.

Optional deterministic microtiming is added only inside the `PerformanceIR.realization` bound.

### Gate / articulation

`gate_curve` scales symbolic note duration.

Discrete musical articulations then apply deterministic execution semantics:

- legato
- tenuto
- neutral
- staccato
- accent
- marcato

### Accent

Each authored accent point is assigned to the nearest note onset in the phrase and modifies that onset.

### Breath

`breath_after_beats` creates real same-role silence after the phrase body. Events that would occupy
that authored silence are removed.

Two phrase envelopes on the same role may not overlap each other or each other's authored breath.

## Event provenance

Every realized event stores a `performance` object containing the original event and every expressive
decision applied to it. This makes the performance inspectable and revisable.

## Three-way dogfood

One identical eight-note piano motif was rendered at 44.1 kHz with the same seed and three phrase plans.

Pitch identity is identical in all variants.

Audio correlations after RMS normalization:

- lyrical ↔ whispered: `0.2136`
- lyrical ↔ urgent: `0.2394`
- whispered ↔ urgent: `0.0513`

The difference therefore comes from performance realization, not pitch rewriting.

A repeated render of the lyrical plan has identical WAV SHA-256:

`4185c34b4b07310a259498f7e74aa5b78f147b5ed43b34d5f5c94d16b85db3de`

## Regression

- pytest: 134 / 134 PASS
- runtime modules: 107
- import edges: 117
- import cycles: 0
- import failures: 0

## E0 compatibility

With no `performance_ir`, E1 is byte-identical to E0 for Composer Plan, Music IR and WAV.

## Scope boundary

E1 does not yet rewrite motif pitches/rhythms. That belongs to E2.
