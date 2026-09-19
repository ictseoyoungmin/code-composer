# S10 — Violin Performance-to-Timbre Expression Hardening

Status: **CLOSED**

## Goal

Preserve the S9 physical bowed-string/body architecture while reducing the repeated identical-voice impression when a violin part is realized across phrases. S10 changes performance-to-timbre controls, not composition.

## New factory surface

`bowed.violin.modeled_expression@1.0.0`

The preset starts from the S9 `modeled_admittance` physical configuration and adds an opt-in `expression_hardening` block. Existing S5-S9 preset JSON files are unchanged.

## Control model

- deterministic low-rate bow-pressure, bow-speed and bow-position drift;
- deterministic per-event control offsets;
- bounded attack-duration/pressure/noise variation;
- bounded bow-change pressure dip/noise variation;
- vibrato coupled to excitation pressure/energy and output amplitude;
- no note, rhythm, harmony, form or arrangement generation inside the sound engine.

The model is seeded and deterministic. It is intended to follow established bowed-string control relationships rather than simulate humanity with unconstrained random noise.

## Compatibility invariant

`modeled_expression` with `expression_hardening.enabled=false` must match S9 `modeled_admittance` byte-for-byte on matched isolated-note and supported realized-track renders.

## Research basis

- Schoonderwaldt (2009): bow force/pressure is a dominant control of spectral centroid, with bow speed and bow-bridge distance coordinating the playable timbre region.
- Mellody & Wakefield (2000): violin vibrato includes significant partial-amplitude modulation in addition to frequency modulation.
- Guettler (2002): bow force and acceleration are operative parameters during establishment of Helmholtz motion, motivating bounded attack/reversal transients.

See `CREDITS.md` for full citations.

## Explicit non-goals

- no sampled performer cloning;
- no named-instrument claim;
- no random EQ automation;
- no harmonics, pizzicato, ricochet/spiccato bounce or continuous double-stop physical state.

## Closure validation

- S10 focused tests: **6/6 PASS**.
- Full source regression: **380/380 PASS**. Physical-model files were process-isolated where needed because repeated Python per-sample waveguide tests accumulate runtime cost in a single pytest process; no test was omitted.
- Clean-installed wheel regression: **380/380 PASS** with the repository `pythonpath` injection disabled and imports routed to the clean wheel target.
- Standalone Skill self-check: **PASS**.
- Skill validation: **PASS**.
- `compileall`: **PASS**.
- Import sweep: **126 modules / 0 failures**.
- Static import graph: **126 modules / 182 edges / 0 cycles**.
- Clean wheel SHA256: `9c99cc0af8167221bd5c98de6ce8d2b3de1d895e76fbcf86be4b5fb2c4036bd9`.

The wheel build temporarily creates `kit/build/`; S0R1 hygiene correctly rejected that transient directory during clean regression. It was removed and the affected repository-hygiene tests were rerun successfully. The canonical Skill closes with no persisted build output.

## Matched S9/S10 dogfood

A fresh two-bar D natural minor validation phrase at 84 BPM was realized once and rendered through both presets with the same eight performance events:

- S9 control: `bowed.violin.modeled_admittance@1.0.0`;
- S10 treatment: `bowed.violin.modeled_expression@1.0.0`;
- performance realization equality: **true**;
- clipping ratio: **0.0 / 0.0**;
- left-channel STFT log-spectrum correlation: **0.986822**;
- left-channel spectral-centroid trajectory correlation: **0.821606**.

This is a matched timbre/performance-control A/B, not a composition comparison. The audition files remain validation evidence outside the installed Skill.

## Release packaging

- standalone Skill: **198 files**;
- Codex plugin: **200 files**;
- Claude plugin: **200 files**;
- forbidden build/cache/audio/MIDI payload inside the canonical Skill: **0**;
- plugin Skill subtrees are generated from the canonical Skill rather than independently edited copies.

S10 is therefore **CLOSED**. A later listening result may reopen the slice, but new violin techniques such as harmonics, pizzicato, or physical spiccato/ricochet belong in separately scoped slices rather than being folded into this closure.
