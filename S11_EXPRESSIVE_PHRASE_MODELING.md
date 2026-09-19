# S11 — Expressive Phrase Modeling — CLOSED

Date: 2026-09-18  
Engine version: 1.17.0  
Baseline: S10 Violin Performance-to-Timbre Expression Hardening

## Goal

S10 made individual bowed-string events respond more naturally to performance state. S11 closes the next listening bottleneck: **a violin phrase must breathe as one authored gesture across multiple notes rather than as a sequence of individually plausible notes**.

S11 does **not** add another violin preset or another synthesis architecture. It extends the existing Performance IR with optional phrase-scale control curves that drive the S10 `bowed.violin.modeled_expression` engine.

## Added contract

A phrase may author `instrument_expression_curves` for:

- `bow_pressure`
- `bow_speed`
- `bow_position`
- `bow_noise_gain`
- `vibrato_depth_cents`
- `vibrato_rate_hz`
- `vibrato_onset_s`

The controls are bounded by the expressive-score-plan validator and interpolated at note onsets. Event-local `performance.instrument_expression` remains more specific and overrides the phrase envelope control-by-control. S11 does not infer style, emotion, taste, notes, rhythm, harmony, form, or orchestration.

## Compatibility

When a phrase has no `instrument_expression_curves`, S11 adds no new event metadata. A matched deterministic fixture was executed under the original S10 source tree and the S11 source tree:

- Performance IR SHA256: `cbee40dc921df9efc2cd3894e394396ea6fb346331bca401a1d261607c884b08` — **identical**
- violin-realized IR SHA256: `5ee0967b8d225909c759ae05bfe6f3349329dce224b6e7e1a15ad20fc96c3772` — **identical**
- factory preset count: **11 → 11**
- violin preset count: **6 → 6**

## Dogfood — Between Two Streetlights

The S10 dogfood piece was reused as a listening regression without changing pitch/onset identity between control and S11 treatment.

- bars: **20**
- tempo/key: **76 BPM / E natural minor**
- violin events: **60**
- playability: **comfortable**
- max transition score: **0.759033**
- warnings: **0**
- events receiving phrase-expression change: **60**
- control/S11 physical fingering realization equal: **true**
- control/S11 note/timing/velocity identity: **true**
- clipping ratio: **0.0 / 0.0**
- rise RMS: **0.036617 → 0.040343**
- apex RMS: **0.035191 → 0.046371**

The audition intentionally caps overlapping legato note durations at the next onset so the matched comparison stays on the stateful physical-string renderer instead of entering its overlap fallback. Pitch and onset identity are preserved.

## Validation

- S11 focused tests: **6 / 6 PASS**
- source regression: **386 / 386 PASS**
- clean-installed wheel regression: **386 / 386 PASS** across **64 isolated test-file processes**, failed files **0**
- standalone self-check: **PASS**
- isolated Skill validation: **PASS**
- compileall: **PASS**
- runtime imports: **126 / 126**, failures **0**
- static graph: **126 modules / 182 edges / 0 cycles**

## Packaging

- standalone Skill: **198 files**
- Codex plugin: **200 files**
- Claude plugin: **200 files**
- forbidden build/cache/audio/MIDI artifacts in installed Skill: **0**
- plugin embedded Skill subtree == standalone Skill: **byte-exact** for both adapters
- clean-tested wheel SHA256: `cbd2fcf261cd3347e676cdb28a61c09c5bd10b0ef700e161c911141f5cfceed0`

## Closure

S11 is **CLOSED**. The next planned slice is **S12 — Violin Realism Hardening**, focused on player-mechanics detail such as position shifts, bow retakes, string crossings, and open-string versus stopped-string behavior while preserving S10/S11 compatibility.
