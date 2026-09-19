# S22 — Drum Acoustic Voicing & Timbre Polish

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Polish the S21 dry acoustic core without adding room, mastering coloration, new articulations, stateful kit interaction, or drummer grammar. The target is less brittle separation between contact/body/wire and less narrow metallic peakiness, not a darker or masked mix.

## Compatibility boundary

`drums.acoustic_kit_modeled_realistic@1.0.0` remains unchanged. S22 adds `drums.acoustic_kit_modeled_polished@1.0.0` as a separate opt-in preset.

## Voicing changes

- **Kick:** softer bounded beater/contact HF while preserving sub/body weight.
- **Snare:** head/body remains present while wire/impact bands are blended and HF brittleness reduced.
- **Toms:** impact is less detached from the membrane body; high/mid/floor tuning and long decay remain intact.
- **Hi-hat / ride / crash:** increased dense modal population, lower narrow-peak dominance, frequency-dependent HF-tail damping, and softer contact onset.

## Matched dry-source evidence

Same **114 explicit events**, 8 bars, 96 BPM, 24 kHz. S21 first, S22 second.

- Kick onset-click score: **0.863 → 0.346**, low-band energy remains **0.9962**.
- Snare body ratio: **0.453 → 0.560**; air remains **0.149** and centroid moves **3454 → 2637 Hz**.
- Open hi-hat decay remains **1.030 s**.
- Ride bow / bell identities remain separated at **5544 / 5974 Hz**.
- Crash decay remains long at **2.110 s**.

## Validation

- S22 focused: **10 / 10 PASS**.
- Source regression: **498 / 498 PASS**, **75 test files**.
- Clean-installed wheel regression: **498 / 498 PASS**, source-path injection disabled.
- Import/static graph boundary unchanged from S21: **130 modules / 191 edges / 0 cycles**, public entrypoints **9**.
- Factory presets: **17**, including three percussion presets (S20 compatible, S21 realistic, S22 polished).

## Next

Return to listening review. **S23 Performance-to-Timbre Dynamics is only a candidate** and opens only if insufficient strike-force / strike-position control is now the next reproducible bottleneck.
