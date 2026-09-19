# Reference Surface — v1.15.5

The checked-in reference assets are executable contracts, not illustrative pseudocode.

## Canonical examples

- `examples/basic/demo_ir.json` — minimal direct Music IR. It validates and renders as-is.
- `examples/basic/seed_ir.json` — execution-capable seed used by the Composer Brief compiler.
- `examples/basic/composition_brief.json` — Agent-authored structured composition decision record.
- `examples/basic/high_level_ir.json` — deterministic compiler output from the seed + brief.
- `examples/concert_piano_patch.json` — current `piano_design` category + numeric-control authoring.
- `examples/upright_piano_patch.json` — compact acoustic upright example.
- `examples/electric_tine_piano_patch.json` — electric tine/pickup/amp example.
- `examples/electric_reed_piano_patch.json` — electric reed example.
- `examples/electric_fm_piano_patch.json` — digital-FM stage-piano example.

`high_level_ir.json` is regression-tested against the compiler. It must not become hand-edited drift.

## Schema authority

- `schemas/composition_brief.schema.json`
- `schemas/piano_design.schema.json`

The Python validators remain the execution authority because they enforce cross-field relationships
that plain JSON Schema cannot express conveniently, such as section-ID membership, motif/rhythm
length equality, groove cell count vs `steps_per_bar`, and piano cutoff ordering.

The JSON Schemas mirror the public shape, types, enums and independent category/control surfaces.

## Packaged references

The wheel ships synchronized copies under `code_composer/reference/` so downstream Agent runtimes can
inspect the same schemas/examples without depending on a source checkout. Tests require the packaged
copies and top-level source references to be byte-identical.

## Rule

A file under `examples/` or `schemas/` may not be treated as historical documentation. Historical
formats belong in validation/history docs, not in the current reference surface.
