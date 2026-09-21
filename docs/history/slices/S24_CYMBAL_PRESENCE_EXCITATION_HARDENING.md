# S24 — Cymbal Presence & Excitation Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Fix the S23 cymbal imbalance identified by listening: hi-hat/ride/crash were weak relative to kick/snare/tom while the broadband wash read as a separate TV-static/Gaussian-noise layer. S24 strengthens metallic attack and plate/modal body, reduces independent hiss, and rebalances cymbal presence without room/reverb masking.

## Acoustic strategy

- S23 preset remains unchanged; S24 is opt-in.
- Broadband wash is band-shaped and amplitude-coupled to the plate modal envelope.
- Modal body and short metallic-contact presence are reinforced.
- Final cymbal level is rebalanced only after the excitation/body redistribution; the gain change is not used to amplify the old static layer.
- No new articulation, room/mic model, stateful choke, or drummer grammar.

## Matched dry-source evidence

Same S23 authored `strike_force` / `strike_position`, seed, velocity and articulation for each pair. Full dogfood uses the same **114 explicit events**, 8 bars, 96 BPM, 24 kHz.

- Open hat RMS ratio: **1.59×**; 9–11.5 kHz hiss ratio **0.230 → 0.046**.
- Ride bow RMS ratio: **1.69×**; hiss **0.175 → 0.025**.
- Ride bell RMS ratio: **1.80×**; 1.8–8 kHz metal-body ratio **0.691 → 0.943**.
- Crash RMS ratio: **1.80×**; hiss **0.176 → 0.029**.
- Snare listening guard: RMS ratio **1.00×**, confirming non-cymbal stability.
- Full groove RMS: **0.07488 → 0.07961**, peak **0.7166 → 0.7221**, clipping **0**.

## Validation

- S24 focused: **10/10 PASS**.
- Source regression: **518/518 PASS**, **77 test files**.
- Clean-installed wheel regression: **518/518 PASS**, source-path injection disabled.
- Import/static graph: **130 modules / 191 edges / 0 cycles**, public entrypoints **9**.

## Next

Return to listening review. **Stateful Kit Interaction remains a candidate, not automatically opened.**
