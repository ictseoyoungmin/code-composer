# S12 — Violin Realism Hardening — CLOSED

Date: 2026-09-18  
Engine version: 1.17.0  
Baseline: S11 Expressive Phrase Modeling

## Goal

S11 made phrase-scale bow and vibrato controls breathe across multiple notes. S12 closes the next listening bottleneck: **the realized violin must preserve audible traces of a player's physical mechanics rather than treating every stopped/open note, shift, crossing, or separated bow stroke as the same generic event**.

S12 adds one opt-in preset, `bowed.violin.modeled_realistic@1.0.0`, on top of the existing S10/S11 physical-expression path. It does not replace or mutate the older presets.

## Added player-mechanics behavior

- open-string notes strongly suppress left-hand vibrato while stopped strings retain authored vibrato;
- stopped strings receive slightly stronger finger-end damping than open strings;
- same-string position shifts create a finite pitch/contact transition scaled by realized position distance;
- stopped-string crossings use a slightly longer finite contact-transfer window with bounded incoming-string bow-force preload;
- sufficiently separated bow groups may be realized as same-direction retakes with an off-string reset and finite recontact transient.

The layer is deterministic and consumes existing violin-realization evidence. It does not invent notes, rhythm, harmony, form, style, or emotion.

## Compatibility

`modeled_realistic` is separate and opt-in. With `realism_hardening.enabled=false`, matched S12 realization and rendering are byte-identical to the S10/S11 `modeled_expression` path for the supported regression phrase. Existing S5-S11 presets remain present and unchanged.

Factory surface after S12:

- total factory presets: **12**
- violin presets: **7**
- new preset: **`bowed.violin.modeled_realistic@1.0.0`**

## Dogfood — Between Two Streetlights

The S11 dogfood piece was reused without changing authored pitch/onset/duration/velocity identity.

- bars: **20**
- tempo/key: **76 BPM / E natural minor**
- violin events: **60**
- playability: **comfortable**
- max transition score: **0.759033**
- warnings: **0**
- open strings: **9**
- stopped strings: **51**
- physical string crossings: **11**
- realized position shifts: **1**
- bow retakes in the song: **0** (the song contains no sufficiently long eligible rests)
- matched 13-event audition clipping ratio: **0.0 / 0.0**

A separate retake protocol verifies the missing mechanism: the same three separated notes produce `down → up → down` under the S11 control and `down → down → down` under S12, with the latter two S12 strokes explicitly marked `retake=true`.

## Validation

- S12 focused tests: **7 / 7 PASS**
- source regression: **393 / 393 PASS**
- clean-installed wheel regression: **393 / 393 PASS** across **65 isolated test-file processes**, failed files **0**, timeouts **0**
- runtime imports: **126 / 126**, failures **0**
- static graph: **126 modules / 182 edges / 0 cycles**
- standalone self-check: **PASS**
- isolated Skill validation: **PASS**
- compileall: **PASS**

## Packaging

- standalone Skill: **199 files**
- Codex plugin: **201 files**
- Claude plugin: **201 files**
- forbidden build/cache/audio/MIDI artifacts in installed Skill: **0**
- plugin embedded Skill subtree == standalone Skill: **byte-exact** for both adapters
- clean-tested wheel SHA256: `69f05f1a4f212387af2d559f6fde6c55b43bfcf89caeb398210f772f026423dc`

Exact artifact hashes are recorded in `S12_RELEASE_MANIFEST.json`.

## Closure

S12 is **CLOSED**. Functional, source, clean-installed, and package-boundary validation are complete. The next planned slice is **S13 — Articulation Expansion**, adding explicit violin technique vocabulary while preserving S12 player-mechanics realism.
