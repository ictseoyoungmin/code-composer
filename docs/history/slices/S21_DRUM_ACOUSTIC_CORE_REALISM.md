# S21 — Drum Acoustic Core Realism Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Remove the remaining compact/procedural "toy drum" ceiling at the **dry-source acoustic core** before adding more performance grammar. S20's articulation vocabulary remains intact; S21 changes how the opt-in realistic kit vibrates after a strike.

## Compatibility boundary

The historical `drums.acoustic_kit_modeled@1.0.0` preset is preserved byte-identically for kick, snare-center and closed hi-hat. S21 adds `drums.acoustic_kit_modeled_realistic@1.0.0` as a separate opt-in preset. Existing projects therefore do not silently change timbre.

## Reduced-order acoustic model

- **Kick:** paired batter/resonant membrane modes, enclosed-air cavity response, weak shell modes and a bounded beater-contact transient.
- **Snare:** paired heads + cavity + shell, with the resonant-head proxy driving the wire-rattle envelope instead of an unrelated independent noise tail.
- **Toms:** high/mid/floor sizes retain their tuning while gaining paired heads, size-dependent cavity response and shell coloration.
- **Hi-hat / ride / crash:** dense deterministic inharmonic plate fields with closely split modal pairs, natural beating, broadband strike/wash excitation and bounded velocity-dependent high-mode emphasis.

This is an independent compact approximation, not FDTD, a sampled drum kit, or a fitted commercial instrument.

## Matched dry-source evidence

The A/B audition uses the **same 114 explicit events**, 8 bars at 96 BPM and 24 kHz. S20 is rendered first and S21 second. No room, overhead, reverb, stateful choke, or drummer grammar is used.

- Kick body-band ratio (120–500 Hz): **0.001360 → 0.003835**, while 20–120 Hz energy remains **0.9962**.
- Snare body-band ratio: **0.121 → 0.453**; centroid moves **5408 → 3454 Hz**, reducing the noise-only impression while retaining air.
- Ride bow centroid: **4195 → 5265 Hz**; ride bell remains brighter at **5834 Hz**.
- Crash free decay increases **1.956 → 2.248 s**.
- Open hi-hat free vibration remains long at **1.143 s**.

## Explicit non-goals

S21 does **not** add room/overhead/microphone simulation, stateful cymbal/hat choking, shared residual kit state, sticking rules, groove grammar, or automatic humanization. Those remain later listening-driven candidates.

## Validation

- S21 focused: **10 / 10 PASS**.
- Source regression: **488 / 488 PASS** across **74 test files**.
- Clean-installed wheel regression: **488 / 488 PASS** across the same **74 test files**, source-path injection disabled.
- Import: **130 / 130**, static graph **130 modules / 191 edges / 0 cycles**.
- Factory presets: **16**, including two percussion presets (S20-compatible and S21 realistic).

## Next

Return to listening review. **S22 Performance-to-Timbre Dynamics is only a candidate**; open it only if the next reproducible bottleneck is insufficient strike-force / strike-position control rather than remaining acoustic-core, mix, or state-interaction issues.
