# S28-D — Authored Piano Phrase Direction Timing / Gate

Status: **ENGINEERING CANDIDATE / LISTENING GATE OPEN**

## Decision

No new timing engine was added. Code Composer already has the correct v1.16 E1 authoring surface: `timing_curve_ms` and `gate_curve`. S28-D reuses it rather than creating a competing piano-only timing API.

For piano naturalism, the dogfood disables random microtiming and velocity variation. The Composer authors phrase direction explicitly: the rising half pulls forward toward about `-8 ms`, then the resolution relaxes toward positive timing, while gate length follows its own phrase curve.

## Integration hardening

The S28-D flagship exposed one latent cross-feature bug: E4 orchestration-budget realization decorated `piano_control` events with note-only `orchestration_budget` metadata, which later violated the piano-control contract. Explicit `*_control` events now pass orchestration-budget arbitration unchanged and are not counted as sounding role occupancy.

This hardening also protects authored drum controls from being treated as sounding notes.

## Current canonical interpretation

The status above records the state **at the S28-D checkpoint**. S28-D became part of the accepted piano-naturalism baseline used by S28-H and later S27-M R2 / S29-S31 full-song work.

No separate retrospective listening PASS is asserted. S28-D is **not an active reopenable task** unless new production evidence specifically points to phrase timing/gate behavior.
