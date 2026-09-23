# CR01 — Minimal Song Model + Contract Foundation

Status: **ENGINEERING CANDIDATE**

Issue: #19

## Purpose

CR01 establishes the first canonical Composer-first authoring state after CR00.

The Song document is deliberately smaller than the pre-refactor `CompositionBrief`, while its structural contract is strict. The authored surface describes music and ownership. Renderer implementation details appear only when explicitly locked.

## Canonical separation

```text
Song
├─ musical intent (soft text; never auto-mapped to presets)
├─ transport / optional tonality
├─ ordered sections
├─ instruments
│  ├─ musical identity: family / variant
│  └─ optional render_lock: engine / preset
├─ tracks
│  ├─ arbitrary track id
│  ├─ arbitrary musical function
│  └─ instrument reference
├─ materials
│  ├─ motif
│  ├─ progression
│  └─ rhythm
├─ parts
│  ├─ section reference
│  ├─ track reference
│  └─ material reference
└─ hard locks
   └─ bpm / root / scale
```

Track function is **not an enum**. `counterline`, `texture`, `ostinato`, `harmonic-bed`, or a future user-defined function are equally legal.

Instrument family is not the render engine. A violin may be authored as a violin without naming an engine. When `render_lock` is absent, lowering owns engine selection. When it is present, aggregate runtime validation verifies the locked engine/preset.

## Contract rules

- `format` is `code-composer-song/v1`.
- IDs are explicit, unique, and cross-referenced.
- Unknown fields are rejected.
- A Song is authored without a seed Music IR.
- `meta.global_seed` is a deterministic realization seed, not a seed document.
- Tonality is optional; the Song model itself can represent non-tonal material.
- Hard locks are redundant by design: they guard user requirements against accidental Composer revision.
- Canonical JSON serialization is key-order independent and SHA-256 fingerprinted.
- No analyzer may mark the music aesthetically “good” or rewrite it from this contract.

## Deliberate non-goals

CR01 does **not**:

- lower Song into the pre-refactor Music IR;
- preserve `CompositionBrief` compatibility;
- preserve the six privileged arrangement roles;
- select a renderer when the Song did not lock one;
- infer a style/mood vocabulary into musical material;
- render a full composition;
- define a universal aesthetic score.

Those are either explicitly rejected by CR00 or belong to later slices.

## Next boundary

After CR01 contract closure, CR02 can build the first deterministic **Song → execution plan** lowering path against this model without requiring a legacy seed IR.
