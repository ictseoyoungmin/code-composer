# S14 — Acoustic Piano Release & Resonance Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Problem

Acoustic piano could expose a `meow / wah / singing` pitched release tail with `pedal=false`, especially after chords. The bug was treated as an engine artifact, not as expressive resonance.

## Root causes found

1. `_modal_soundboard()` used long fixed high-Q modal frequencies even after ordinary damper-down note-off.
2. `_resonance_layer()` synthesized a long independent ratio bank including `1.5 × fundamental`, which can become an unplayed pitch when the struck tone decays.
3. All detuned unison strings used the same release envelope, allowing the release to expose beating that was subtle during attack/sustain.

## Engine fix

- The always-on soundboard now uses a short **damper-down modal state**.
- A longer modal response is added only when authored sustain-pedal activity keeps the strings undamped.
- No-pedal per-note resonance accepts harmonic ratios only and is strongly subordinate to the struck string.
- Secondary detuned strings receive extra damping only after note-off; attack and sustain detuning are preserved.
- No factory preset is silenced with `resonance_gain=0`; the acoustic engine itself is hardened.

## Regression gate

`tests/test_piano_release_tail.py` renders `concert_grand`, `studio_grand`, and `upright` as single note / dyad / triad with no pedal and checks:

- persistent off-harmonic narrow spectral peaks,
- release RMS re-swell,
- historical `1.5×` non-harmonic ratio leakage,
- pedal-on shared body resonance preservation.

The most vulnerable concert-grand protocol improved persistent off-harmonic peak from roughly **−42 dB to −54 dB** for single/dyad/triad. The direct `1.5×` release component for MIDI 60 fell from **−41.49 dB to −94.00 dB** relative to the fundamental.

## Validation

- S14 focused: **20 / 20 PASS**
- source regression: **420 / 420 PASS**
- clean-installed wheel regression: **420 / 420 PASS**
- self-check: **PASS**
- isolated Skill validation: **PASS**
- compileall: **PASS**
- import sweep: **126 / 126**, 0 failures
- static graph: **126 modules / 182 edges / 0 cycles**

## Listening evidence

A 24 kHz protocol renders single → dyad → triad for concert grand, studio grand and upright before and after S14. The A/B is release-tail evidence only; it is not a composition reference.

## Next

**S15 — Ensemble / Orchestration Realism.** Piano engine defects must not be hidden by EQ, masking, or orchestration; S14 closes the known release-tail artifact first.
