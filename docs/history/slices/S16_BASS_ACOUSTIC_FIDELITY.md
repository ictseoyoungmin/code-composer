# S16 — Bass Acoustic Fidelity Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Remove the largest post-S15 support-instrument fidelity mismatch without widening the slice into another orchestration rewrite.

The post-S15 flagship showed that violin and acoustic piano had dedicated physical/performance models while bass was still a generic sine/triangle support patch. S16 therefore gives bass its own deterministic plucked-string/pickup engine while preserving all authored notes, S15 ensemble relationships, and the existing bass articulation layer.

## Implemented engine

New engine: `plucked_bass`  
New factory preset: `bass.electric_finger_modeled@1.0.0`

The engine independently implements a lightweight physical/parametric electric-bass model:

- pluck-position harmonic weighting;
- pickup-position harmonic sampling/notches;
- bounded stiffness-like inharmonicity;
- frequency-dependent damping so upper partials decay faster than the fundamental;
- deterministic low-level finger attack texture;
- pickup/tone bandwidth shaping and bounded soft saturation;
- deliberately tiny high-passed stereo width so low bass remains centered.

It reuses existing `pitch_start_cents`, `pitch_end_cents`, `pitch_time_s`, `attack_scale`, and `release_scale` performance controls. No new notes or articulations are inferred.

## Compatibility

- Existing generic synth behavior is unchanged.
- Existing bass arrangement/articulation logic is unchanged.
- S15 leader/follower timing, overlap-weighted yielding, and role-pan realization are unchanged.
- S14 acoustic-piano release hardening is unchanged.
- S13 violin articulation/physical-performance paths are unchanged.
- The new bass engine is opt-in through an explicit patch/preset.

## Regression evidence

S16 focused regression verifies:

- engine/preset registration;
- deterministic rendering and bounded output;
- upper-partial energy decays faster than low partials;
- pluck position changes brightness without inventing a fixed pitch;
- pickup position changes spectral response deterministically;
- existing authored pitch approaches drive the modeled string pitch;
- attack/release performance controls affect excitation deterministically;
- invalid physical parameters are rejected.

## Dogfood — Last Light on Platform Three

The S15 flagship was re-rendered at 24 kHz with **only the bass instrument patch changed**.

- all track event lists identical: **true**
- control bass stem RMS: **0.010765**
- S16 bass stem RMS: **0.010330**
- RMS ratio: **0.9596**
- control bass stem spectral centroid: **142.50 Hz**
- S16 bass stem spectral centroid: **298.84 Hz**
- full-song control/treatment mono waveform correlation: **0.97721**
- full-song difference RMS: **0.01128**
- treatment peak: **0.34657**
- treatment clipping: **0.0**

The comparison is therefore not a loudness trick: integrated bass-stem energy remains close while the modeled bass exposes a stronger finger/pluck and upper-partial decay structure.

## Validation

- S16 focused: **8 / 8 PASS**
- source regression: **443 / 443 PASS** across 69 test files
- clean-installed wheel regression: **443 / 443 PASS** across 69 test files
- import sweep: **129 / 129**, 0 failures
- static graph: **129 modules / 189 edges / 0 cycles**
- public entrypoints: **9**

## Research provenance

S16 uses published string-synthesis/acoustics work only as conceptual reference for pluck/pickup spatial response and frequency-dependent damping. The implementation is independent; no external source code, recordings, measured damping tables, pickup measurements, or named-instrument fitted data are bundled. See `CREDITS.md`.

## Next candidate

If listening confirms that the bass now sits closer to the piano/violin fidelity level, the remaining support-instrument mismatch is **percussion acoustic fidelity**. Keep that as a separate slice rather than combining it with S16.
