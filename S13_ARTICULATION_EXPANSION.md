# S13 — Articulation Expansion — CLOSED

Date: 2026-09-18  
Engine version: 1.17.0  
Baseline: S12 Violin Realism Hardening

## Goal

S12 made the modeled violin preserve more of the player's physical mechanics. S13 closes the third planned violin-quality slice by expanding the explicit performance vocabulary without weakening that S12 arco path.

S13 adds one opt-in preset, `bowed.violin.modeled_articulated@1.0.0`, layered on `modeled_realistic`. Existing presets remain present and ordinary arco events continue through the S12 continuous/realism renderer.

## Added articulation behavior

- **pizzicato** — deterministic finger-pluck excitation, pluck-position-dependent partial weighting, a short bounded finger-noise transient, and free string/body decay;
- **harmonic** — canonical MIDI remains the authored sounding pitch. The planner attaches a plausible nearby natural partial when available, otherwise conservative artificial-fourth or modeled-sounding-pitch metadata; rendering lightens bow pressure/vibrato and harmonic voicing without rewriting pitch;
- **spiccato** — a finite bouncing-bow contact interval followed by an off-string/free-decay interval for each explicitly authored detached note.

The layer is deterministic. It does not infer or compose articulation choices, melody, rhythm, harmony, form, orchestration, or emotion. Ricochet/sautillé sequence generation, col legno, explicit sul ponticello/sul tasto notation, and continuous double-stop special-articulation state remain out of scope.

## Compatibility

`modeled_articulated` is separate and opt-in. With `articulation_expansion.enabled=false`, matched arco rendering is byte-identical to S12 `modeled_realistic`. Existing S5-S12 factory presets remain present.

Factory surface after S13:

- total factory presets: **13**
- violin presets: **8**
- new preset: **`bowed.violin.modeled_articulated@1.0.0`**

## Dogfood — Between Two Streetlights

A 31-event excerpt from the existing S12 dogfood composition was reused so S13 could be judged against established material rather than a purpose-built demo phrase.

- tempo/key: **76 BPM / E natural minor**
- audition range: beats **40–72**
- violin events: **31**
- explicitly changed articulation events: **9**
- spiccato: **4**
- natural harmonic: **1**
- pizzicato: **4**
- playability: **comfortable**
- max transition score: **0.76**
- warnings: **0**
- clipping ratio: **0.0 / 0.0** (S12 control / S13)
- control RMS: **0.03084049**
- S13 RMS: **0.02746452**
- difference RMS: **0.03998443**

The control and S13 audition preserve the same composition excerpt; only the selected explicit articulation events use the new technique layer.

## Validation

- S13 focused tests: **7 / 7 PASS**
- source regression: **400 / 400 PASS** across **66 isolated test-file processes**, failed files **0**, timeouts **0**
- clean-installed wheel regression: **400 / 400 PASS** across **66 isolated test-file processes**, failed files **0**, timeouts **0**
- clean wheel SHA256: `528444d0b7d9adbb5e75713a41d2eb7c5f9d54c27dcac2fd8c81d4c82ecaf19a`

Package-boundary validation:

- standalone Skill: **200 files**
- Codex plugin: **202 files**
- Claude plugin: **202 files**
- forbidden build/cache/audio/MIDI artifacts in installed Skill: **0**
- plugin embedded Skill subtree == standalone Skill: **byte-exact** for both adapters
- runtime imports: **126 / 126**, failures **0**
- static graph: **126 modules / 182 edges / 0 cycles**
- exact artifact hashes are recorded in `S13_RELEASE_MANIFEST.json`.

## Closure

S13 is **CLOSED**. Functional, source, clean-installed, and package-boundary validation are complete. This closes the planned S11 → S12 → S13 violin-quality sequence. The next action is a fresh flagship composition/perceptual dogfood pass before deciding whether another engine slice is justified.
