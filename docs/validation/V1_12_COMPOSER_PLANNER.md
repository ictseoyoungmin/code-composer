# v1.12 REOPEN — Agent-Authored Composer Planner

## Why v1.12 was reopened

The first implementation used `STYLE_PRESETS`, `STYLE_MATERIALS`, aliases and mood-keyword maps. That made natural-language understanding a growing heuristic dictionary and caused style labels to imply fixed motifs/progressions.

That path is revoked.

## New canonical path

`Prompt -> Composer Agent -> CompositionBrief -> validator/compiler -> Music IR -> render/analyze`

There is no canonical free-text vocabulary parser in the engine.

## Preserved

- ComposerPlan / Music IR boundary
- deterministic renderer
- hard constraint validation
- orchestration grammar
- harmonic grammar
- macro form development
- transition shaping
- analyzer / revision loop

## Removed from canonical source

- style -> fixed motif mapping
- style -> fixed progression mapping
- style alias table
- mood keyword map
- prompt keyword parser

## CLI

```bash
python -m code_composer.composer_cli \
  seed_ir.json \
  composition_brief.json \
  planned_ir.json \
  plan.json
```

The caller/Agent authors `composition_brief.json`.
