# S20 — Drum Articulation Foundation

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Expand the S17 modeled acoustic percussion core from a three-element vocabulary into an explicit, agent-authored acoustic-kit articulation surface without introducing automatic hits, fills, timing humanization, or stateful kit behavior.

## Preserved baseline

The S19 canonical preset `drums.acoustic_kit_modeled@1.0.0` exposed kick, snare center, and closed hi-hat. S20 preserves those default sounds byte-identically. Focused regression pins the S19 hashes for all three. The older non-S17 percussion path also remains unchanged.

## Explicit articulation surface

- **Kick:** `default`.
- **Snare:** `center`, `ghost`, `rimshot`, `cross_stick`.
- **Hi-hat:** `closed`, `half_open`, `open`, `pedal`, `choke`.
- **Ride:** `bow`, `bell`, `choke`.
- **Crash:** `crash`, `choke`.
- **High / mid / floor toms:** `center`, `edge`.

`articulation` is optional on drum events and rhythm-fill events. Omission keeps the historical defaults (`snare=center`, `hat=closed`, etc.). Aliases such as `half-open` and `cross-stick` normalize to canonical identifiers. Unsupported values fail loudly instead of silently degrading.

## Acoustic behavior

- Snare ghost strokes use reduced head/wire excitation; rimshot and cross-stick have distinct shell/rim/wood mode structures.
- Hi-hat openness changes both metallic modal decay and broadband wash. Measured dogfood decay ordering is **closed 0.066s < half-open 0.338s < open 1.121s**.
- Ride bell is a brighter, more focused ping than ride bow: centroid **4201 Hz → 5050 Hz**, while its decay is shorter (**1.788s → 1.236s**).
- Crash has a long wash (**1.956s**) and an explicit short choke-contact response (**0.054s**).
- Tom center tuning descends high → mid → floor by spectral centroid (**195.9 → 144.0 → 96.8 Hz**); edge articulation shifts mode balance upward.

S20 `choke` is deliberately only an explicit short contact articulation. It does **not** terminate a previously ringing cymbal or open hi-hat. Shared residual state and true choke interaction remain S22 scope.

## Authoring / export contract

The runtime never invents articulation from genre, velocity, or surrounding notes. The agent writes it explicitly. MIDI export retains the historical kick/snare/closed-hat General MIDI mappings and adds standard-compatible mappings for open/pedal hat, ride bell, ride/crash, and toms.

## Validation

- S20 focused: **11 / 11 PASS**.
- Source regression: **478 / 478 PASS** across **73 test files**.
- Clean-installed wheel regression: **478 / 478 PASS** across the same **73 test files**, source-path injection disabled.
- Import: **130 / 130**, static graph **130 modules / 191 edges / 0 cycles**.
- Skill self-check / isolated self-check / compileall / skill validation: **PASS**.

## Percussion-focused dogfood

A 24 kHz native, 8-bar / 96 BPM authored kit passage exercises the S20 vocabulary without automatic humanization. It contains **104 explicit drum events**, peak **0.757690**, RMS **0.097847**, clipped sample ratio **0**. The audition bundle also contains isolated grouped reels for snare, hi-hat, ride/crash, and tom articulations.

## Next

Return to listening review. **S21 Performance-to-Timbre Dynamics is only a candidate**; open it only if the next reproducible bottleneck is the lack of strike-force/position-to-timbre control rather than composition, mixing, or state interaction.
