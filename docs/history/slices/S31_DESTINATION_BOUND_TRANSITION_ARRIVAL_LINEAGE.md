# S31 — Destination-Bound Transition / Boundary Arrival Lineage

Status: CLOSED / PERCEPTUAL PASS

Canonical base: GitHub `main@529bccdde58bb5d5c9fb081e076f7f0c8e197e8c` (S30 CLOSED / post-merge CI SUCCESS).

## Problem

S29 gives cross-section thematic lineage and S30 gives explicit section progression lineage, but E5 harmonic anticipation still stores a second independent `target_degree`. A transition can therefore remain syntactically valid while preparing a degree that no longer matches the destination section's authored S30 progression.

S31 closes only this cross-surface gap.

## Agent authority

For each enabled harmonic anticipation, the Agent explicitly chooses exactly one target source:

1. legacy `target_degree`, or
2. `arrival_binding = {source: destination_progression, progression_index: N}`.

The Agent still authors role, anticipation duration, chord intervals, velocity and gate.

## Runtime authority

For an arrival binding the deterministic runtime:

1. requires the destination section to have an explicit S30 `progression_variant`;
2. validates that the named song-local progression exists;
3. validates that the explicit index is in range;
4. resolves that degree without choosing another index or cadence;
5. emits the anticipation through the existing E5 engine;
6. records progression ID, index, resolved degree and destination section on events and transition reports.

## Compatibility

Legacy `target_degree` remains accepted and follows the historical E5 path. `target_degree` and `arrival_binding` cannot coexist. Absent S31 fields therefore preserve pre-S31 behavior.

## Flagship

`Threadline at First Light` reuses the CLOSED S30 arrangement. A is the S30 baseline. B adds only five pad harmonic-anticipation gestures, each bound to destination progression index 0:

- intro → verse: `verse_ground[0] = 1`;
- verse → pre: `pre_drive[0] = 4`;
- pre → chorus: `chorus_arrival[0] = 6`;
- chorus → return: `return_turn[0] = 4`;
- return → final: `final_cadence[0] = 5`.

Each anticipation is a three-note authored scale-degree chord, for 15 added pad notes total. Lead, bass, drums, and all pre-existing pad events remain identical.

Render evidence:

- 24 kHz / 112 BPM / 16 bars / 36.485708 s;
- A RMS: 0.1063182952;
- B RMS: 0.1062211757;
- RMS difference: about 0.008 dB;
- A peak: 0.66769163;
- B peak: 0.66225666;
- B clipped sample ratio: 0;
- added S31 anticipation notes: 15.

## Closure gate

Engineering gate is **CLOSED**:

- full repository: **98 test files / 659/659 PASS**;
- focused S31 + E5 + S30 + S29 + S15 + S27-M R2: **52/52 PASS**;
- expressive/performance schema + packaged-reference parity: PASS;
- post-v1.16 intentional-source hash allowlist: PASS;
- standalone self-check / canonical Skill validation / plugin distribution: PASS;
- compileall: PASS;
- Skill / Codex / Claude builds: PASS.

Perceptual closure requires production listening to confirm that B makes boundaries feel causally prepared for the destination harmony without sounding like extra chords pasted on top. Metrics alone cannot close this slice.

## Perceptual closure

On 2026-09-23, the user completed the controlled S30-baseline vs S31 destination-bound transition listening gate and chose to proceed. S31 is therefore **CLOSED / PERCEPTUAL PASS**. The accepted treatment makes section boundaries prepare the actual destination progression without changing lead, bass, drums, or the pre-existing S30 harmony inside each destination section.
