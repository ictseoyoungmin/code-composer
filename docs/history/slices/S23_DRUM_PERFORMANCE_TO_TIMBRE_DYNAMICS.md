# S23 — Drum Performance-to-Timbre Dynamics

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Keep the S22 polished dry-source identity and add explicit performance-to-timbre controls without turning track gain or velocity into ambiguous semantics. `strike_force` and `strike_position` are authored event-local controls; omission follows S22 byte-identically.

## Public semantics

- `velocity`: musical intensity/level authority, unchanged.
- `strike_force` (`0..1`): excitation hardness/brightness/contact emphasis.
- `strike_position` (`0..1`): center/bell-side (`0`) to edge-side (`1`) mode emphasis.
- Runtime never invents either control.

## Matched dry-source evidence

Same **114 explicit events**, 8 bars, 96 BPM, 24 kHz. Control omits S23 strike controls; treatment authors them.

- Snare same-velocity force centroid: **1633 → 3308 Hz**.
- Snare center→edge centroid: **1733 → 3305 Hz**.
- Ride soft→hard centroid: **5079 → 5892 Hz**.
- Crash centerward→edgeward centroid: **5553 → 5421 Hz**, decay **2.03 → 2.24 s**.
- Groove RMS remains level-stable: **0.07488 → 0.07488**.

## Validation

- S23 focused: **10/10 PASS**.
- Source regression: **508/508 PASS**, **76 test files**.
- Clean-installed wheel regression: **508/508 PASS**, source-path injection disabled.
- Import/static graph: **130 modules / 191 edges / 0 cycles**, public entrypoints **9**.

## Next

Return to listening review. **S24 Stateful Kit Interaction is a candidate**, not automatically opened.
