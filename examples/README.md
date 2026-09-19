# Repository Examples / Regression Evidence

This directory is **maintainer-facing and intentionally excluded from the installed agent skill**.

It contains compatibility fixtures, regression material, dogfood and historical/showcase evidence that may include complete musical content. Agents using the installed Code Composer skill must not treat this directory as a creative reference corpus.

The canonical agent-facing examples are instead `skills/code-composer/kit/examples/`, which explain operations without supplying musical taste.

---

## Historical content retained for regression

# Code Composer Examples — v1.16 repository

## Current expressive authoring

Use `examples/v1.16/` for the current Expressive Score Plan / Performance IR-era authoring surface.


## v1.16 final-closure evidence

`examples/v1.16/final_closure/` is retained release evidence for the closed v1.16.0 integrated dogfood. It is not the primary authoring template surface. The individual `after.wav` files and structured before/after evidence remain canonical release evidence. L4 removed the exact duplicate repeat copies and derived concatenated comparison WAVs after proving they added no unique evidence.

## Legacy compatibility fixtures

`examples/basic/` intentionally retains v1.15.x metadata. These files are regression fixtures used to prove that
v1.16 preserves the legacy Composition Brief → Composer Plan → Music IR → WAV path byte-for-byte.

Do not rewrite their embedded version fields merely to match the package version; doing so would destroy the
compatibility baseline they exist to test.


## Historical/basic notes

## 1. Minimal direct Music IR

`basic/demo_ir.json` is the smallest representative direct Music IR example and renders directly.

## 2. Canonical Composer Agent flow

```text
external Composer Agent
→ basic/composition_brief.json
→ code-composer-compose
→ basic/high_level_ir.json
→ code-composer
```

The compiler does not infer style words. The Agent writes explicit musical and sound-design decisions.

## 3. Piano family design

Piano family is an explicit structural choice, not a vocabulary mapping.

### Acoustic

- `concert_piano_patch.json`
- `upright_piano_patch.json`

Acoustic design categories:
`body / hammer / stringing / soundboard / perspective`

New acoustic designs resolve to a hammer/string/bridge/modal-soundboard/mechanics engine.

### Electric

- `electric_tine_piano_patch.json`
- `electric_reed_piano_patch.json`
- `electric_fm_piano_patch.json`

Electric design categories:
`mechanism / pickup / amp / modulation / perspective`

Electric designs resolve to a separate excitation/pickup/amp engine.

### Authoring rule

```text
family + categories
→ discrete topology / mechanism

controls
→ exact numeric values
```

The engine never converts subjective words such as "warm", "nostalgic", or "cinematic" into numeric
piano parameters. The Composer Agent decides the family/categories/controls for the musical purpose.
