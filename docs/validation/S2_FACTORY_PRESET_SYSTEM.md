# S2 — Factory Preset System Closure

**Status:** CLOSED  
**Engine baseline:** v1.17.0  
**Date:** 2026-09-17

## Purpose

S2 turns instrument presets into a first-class professional production surface without turning them into compositional examples. The governing rule is: **presets provide sonic capability; the user's brief/current song provides musical content.**

## Factory preset model

The installed Skill now ships a small versioned catalog of six sonic resources:

- `bowed.violin.synthetic_warm`
- `generic.clean_lead`
- `generic.soft_pad`
- `piano.concert_grand`
- `piano.electric_tine_warm`
- `piano.upright_intimate`

The S1 bowed-string dogfood patch is promoted unchanged as `bowed.violin.synthetic_warm`. Its limitations remain explicit: it is a deterministic synthetic/modelled bowed violin resource, not a claim of exposed virtuoso-solo realism.

## Agent-facing boundary

`kit/presets/CATALOG.json` exposes only selection metadata: character, strengths, limitations, recommended roles and expression capabilities. Raw patch values are hidden from the normal agent selection surface. Genre-specific guidance was removed from the final catalog so presets do not become taste/style templates.

Factory definitions are rejected if they contain compositional keys such as notes, note events, melody, motifs, rhythms, chords/progressions, sections/form, arrangement or MIDI. Existing **Examples teach operation, never taste** policy remains intact.

## Deterministic materialization

A Composition Brief may specify `preset_id`, optional exact `preset_version`, and song-local `patch_overrides`. The compiler resolves this immediately into a complete instrument patch and records exact `preset_provenance`. The canonical Music IR therefore does not depend on future factory-preset contents. Updating a factory preset later cannot silently change an already-authored song. Identity fields (`kind`, `engine`, `family`, `preset_provenance`) cannot be replaced through overrides.

## Public surface

`code-composer-presets` adds `list`, `show`, and `materialize`. `list/show` expose metadata without raw patch values; `materialize` is an explicit operational/debug surface. `surface.json`, Skill workflows, contracts and command documentation all expose the preset capability.

## Validation

- Focused preset tests: **11/11 PASS**
- Full regression: **321/321 PASS**
- Coverage: **92.65% (93% display)**
- `code_composer.presets`: **84.21%**
- preset CLI: **90.48%**
- Import sweep: **118/118, 0 failures**
- Static graph: **118 modules / 165 edges / 0 cycles**
- `compileall`: **PASS**
- Standalone Skill self-check: **PASS**
- Clean standalone ZIP → wheel → isolated install preset smoke: **PASS**
- Public console entrypoints: **7**
- S0/S1 musical-content firewall: **PASS**

Legacy final dogfood A/B/C remain byte-identical:

- A `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

## Packaging

- Standalone Skill: **174 files**, forbidden build/cache/audio/MIDI artifacts **0**
- Codex plugin: **176 files**
- Claude plugin: **176 files**
- Codex and Claude embedded Skill subtrees: **exact byte match** to standalone Skill
- Factory-preset audition WAV remains validation-only and is not shipped in the Skill.

S2 closes the preset architecture. Future work may improve/add presets, but each new preset must remain a sonic resource with honest capability/limitation metadata and no bundled compositional answer.
