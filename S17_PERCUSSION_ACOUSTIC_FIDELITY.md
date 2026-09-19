# S17 — Percussion Acoustic Fidelity Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Close the remaining support-instrument fidelity mismatch after S16 without reopening composition, ensemble timing, violin, piano, or bass. S17 promotes percussion from an implicit special-case renderer into an explicit registered engine boundary and adds one opt-in generic modeled acoustic-kit preset.

## Implemented engine / preset

- Registered engine: `percussion`
- Factory preset: `drums.acoustic_kit_modeled@1.0.0`
- Existing explicit drum events remain the musical authority. The engine does not invent hits, fills, timing, or arrangement.

### Kick

The modeled branch uses a compact membrane modal bank instead of the legacy preset's single pitch-swept body. Authored velocity changes bounded tension-relaxation pitch motion and upper-mode excitation. A short band-limited impact models the beater without leaving a sustained unrelated tone.

### Snare

A membrane/body modal bank is coupled to deterministic stochastic snare-wire collision energy. The wire response begins after a small coupling delay and decays independently from the batter-head strike; it is not a periodic amplitude LFO.

### Closed hi-hat

An inharmonic metallic mode cluster receives bounded deterministic strike variation. Higher authored velocity increases high-mode excitation and extends decay modestly. Open-hat/choke/ride/crash state remains outside this slice.

## Compatibility

- Legacy `kind: percussion` output is byte-identical to S16 when `realism_hardening` is absent or disabled.
- S16 modeled bass is unchanged.
- S15 ensemble interaction is unchanged.
- S14 acoustic-piano release hardening is unchanged.
- S13 articulated violin is unchanged.
- Drum factory presets are now selectable explicitly through Composition Brief; preset content remains sonic-only and contains no rhythm pattern or musical material.

## Regression evidence

S17 focused tests verify:

- registered percussion engine and modeled factory preset;
- exact legacy drum hashes and disabled-block identity;
- deterministic same-seed output plus bounded seed-sensitive timbral variation;
- snare velocity changes spectral brightness beyond scalar loudness;
- hi-hat velocity changes decay while retaining high-frequency dominance;
- snare wire-rattle energy persists after the initial strike but remains bounded;
- kick remains low-frequency dominated with bounded membrane tail;
- agent-authored drum preset selection materializes into canonical Music IR;
- invalid realism parameters are rejected.

## Dogfood — Last Light on Platform Three

Only the drums instrument patch changed from the S16 flagship. Track event lists, mix graph, violin, piano, and bass patches are identical.

- drum stem control RMS: **0.006724**
- drum stem modeled RMS: **0.006724**
- drum stem control/model correlation: **0.1244**
- full-song control/model correlation: **0.9866**
- full-song difference RMS: **0.00868**
- treatment peak: **0.3627**
- treatment clipping: **0.0**

The drum-stem RMS was deliberately level-matched before full-song comparison, so the A/B is not a loudness trick.

## Validation

- S17 focused: **10 / 10 PASS**
- source regression: **453 / 453 PASS** across 70 test files
- clean-installed wheel regression: **453 / 453 PASS** across 70 test files
- import sweep: **130 / 130**, 0 failures
- static graph: **130 modules / 191 edges / 0 cycles**
- public entrypoints: **9**

## Research provenance

Published membrane-percussion and snare-collision work was used only as conceptual guidance for impact/modal decomposition, amplitude-dependent tension relaxation, and snare-wire collision behavior. The implementation is independent; no external code, recordings, simulation meshes, measured modal tables, impulse responses, or named-kit fitted data are bundled. See `CREDITS.md`.

## Next

Do not automatically open S18. First listen to the level-matched percussion A/B and the full-song S17 treatment, then identify the next audible bottleneck from evidence.
