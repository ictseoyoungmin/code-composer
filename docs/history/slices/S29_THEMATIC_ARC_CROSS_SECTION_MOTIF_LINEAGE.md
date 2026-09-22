# S29 — Thematic Arc / Cross-Section Motif Lineage

Status: CLOSED / PERCEPTUAL PASS

## Problem

The existing composition stack already supports macro-form density/register development and detailed E2 motif transformation inside Performance IR, but the high-level Composition Brief exposes only one canonical motif. As a result, section labels and density changes can be valid while the listener still hears disconnected section-local material rather than one recognizable theme developing across the song.

S29 closes only that integration gap. It does not add a style model, hidden melody generator, or random mutation policy.

## Agent authority

The Composer Agent explicitly authors optional `materials.motif_variants` entries. Each variant contains:

- complete scale-relative `intervals`;
- complete `rhythm`;
- an `identity_floor` quality target;
- optional `identity_hard_min` validity threshold.

`development.sections.<section>.motif_variant` explicitly selects a variant for a section. The engine never chooses a variant automatically.

## Engine authority

The deterministic runtime:

1. validates variant shape/rhythm;
2. measures structural identity against canonical `main` with the existing E2 identity metric;
3. enforces only an explicitly authored hard minimum;
4. routes the selected motif into the existing phrase arranger;
5. records per-section and per-event lineage evidence;
6. reports distinct motif count and minimum identity for development families.

Absent S29 fields preserve the prior arrangement path.

## Non-goals

- no automatic motif mutation;
- no genre keyword inference;
- no LLM/music-model inside the engine;
- no change to S27/S28 instrument synthesis;
- no change to S27-M ensemble interaction;
- no global mix ducking or mastering workaround.

## Closure gate

Engineering closure requires focused + regression + package validation and a clean source ZIP. Perceptual closure required a fresh full-song A/B where form/harmony/instruments/mix were held fixed and only explicit thematic variants differed. The user accepted the S29 listening gate on 2026-09-22.

## Engineering validation

- focused S15 + S27-M R2 + S29: **29/29 PASS**;
- full repository: **96 test files / 644/644 PASS**;
- standalone skill self-check: PASS;
- canonical Skill validation: PASS;
- plugin distribution validation: PASS;
- compileall: PASS;
- Skill / Codex / Claude builds: PASS;
- post-v1.16 intentional-source hash allowlist updated for every S29-modified baseline file.

S29 also hardens S15 ensemble interaction so explicit `*_control` events are excluded from leader counting, timing offsets, and overlap-yield calculations. This preserves the existing control-event byte-preservation contract when S29 dogfood adds continuous piano-pedal controls.

## Full-song flagship

`Threadline at First Light` is a 16-bar / 24 kHz / 112 BPM A/B. Form, harmony, rhythm, instrument engines, seed, mix, support-track events, and lead timing/duration/velocity are held fixed. B changes only explicit Composer-authored section motif variants.

- rendered duration: **36.485708 s**;
- lead events: **91**;
- lead pitches changed vs control: **27**;
- support event identity: **exact**;
- lead timing/duration/velocity identity: **exact**;
- A RMS: **0.09664456**;
- B RMS: **0.09661606**;
- A peak: **0.65903955**;
- B peak: **0.67550264**;
- B clipped sample ratio: **0.0**.

Authored identity floors are met in every treated section. Measured motif identity scores are verse 0.816429, pre 0.673929, chorus 0.810000, return 0.905000, and final 0.827857.

For this listening artifact only, the long modeled-violin preview resets physical violin state at authored section boundaries to avoid the known long-run renderer slowdown. Natural release tails overlap the next section, and A/B use the identical preview policy. This does not change the S29 runtime contract.


## Perceptual closure

User listening PASS on 2026-09-22 closes S29. `Threadline at First Light` is retained as the closure A/B evidence.
