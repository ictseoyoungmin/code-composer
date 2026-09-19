# R4 — Reference Hygiene

Status: CLOSED

## Goal

Make current examples, schemas, docs and packaged references describe the same v1.15.4 canonical system.
Historical formats remain in validation/history documents only.

## Executable examples

- `examples/basic/demo_ir.json` — minimal direct Music IR; validates and renders as-is.
- `examples/basic/composition_brief.json` + `seed_ir.json` — canonical Composer Agent boundary.
- `examples/basic/high_level_ir.json` — deterministic compiler output from that seed + brief.
- `examples/concert_piano_patch.json` and `upright_piano_patch.json` — current `piano_design` authoring.

Render QA:

- Minimal Music IR: analyzer issues = 0, energy correlation = 1.0000.
- High-level compiled IR: analyzer issues = 0, energy correlation = 1.0000.

## Schema closure

`composition_brief.schema.json` now mirrors the R2 public validation surface for transport, tonal,
form, materials, groove, orchestration, harmony, development and transitions.

`piano_design.schema.json` now matches runtime semantics: `categories` and `controls` are independent
optional surfaces. Categories-only, controls-only and default-empty designs are valid. Python runtime
validation remains authoritative for cross-field invariants.

## Packaged references

The wheel contains synchronized copies under `code_composer/reference/`. Eight packaged schema/example
files were compared to top-level source references and are byte-identical.

## Regression

- pytest: 102 / 102 PASS
- runtime modules: 102
- import failures: 0
- import cycles: 0

## Behavior preservation

R3 and R4 use the same representative Brief and seed:

- Plan SHA-256: `3ccb63001a88e7a98d4d8e74d32750291255ece2a76522dfc4050cf400538a25`
- Music IR SHA-256: `cc254fa49320783f5a374d8e8cbec5d06b09eabd99041b45a5b89974dfb2f5d8`
- Arrangement SHA-256: `4160cc8f4a4d3edd6a029b9dfaa0de47d9ad4fc0138407f1bfcf420234f250cf`
- WAV SHA-256: `b2b0b712fa0249f0246f73725b3e9cdef1dbfb12248dbd76988ace84bdf7aa49`

All are byte-identical between R3 and R4.
