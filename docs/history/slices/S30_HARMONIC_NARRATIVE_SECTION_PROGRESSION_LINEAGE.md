# S30 — Harmonic Narrative / Section Progression Lineage

Status: CLOSED / PERCEPTUAL PASS

Canonical base after S29 merge: `main@5eac5af57e2e58076b60e521bd60a2ea92fddb64` (S29 CLOSED / perceptual PASS).

## Problem

S29 closes cross-section thematic lineage, but its flagship still uses one global progression path. Section energy, harmonic color, and motif variants can differ while verse/pre/chorus/return remain points on the same repeating harmonic loop. The listener can therefore hear stronger thematic continuity without equally strong harmonic departure, tension, arrival, and resolution.

S30 closes only this integration gap.

## Agent authority

The Composer Agent may explicitly author `materials.progression_variants`. Each variant contains a complete scale-degree sequence. A section selects one through `harmony.sections.<id>.progression_variant`.

The engine never generates, mutates, ranks, or auto-selects a progression variant.

## Engine authority

The deterministic runtime:

1. validates progression-variant IDs and degree ranges;
2. materializes variants as song-local progressions with `home` provenance;
3. validates all runtime references before arrangement;
4. resets explicit section-variant indexing at the section boundary;
5. routes the same selected progression to pad, bass, and arp;
6. annotates treated harmonic events with progression lineage;
7. reports explicit degree paths through harmony analysis.

Absent S30 fields preserve historical global-progression indexing and event metadata.

## Cross-feature hardening

S30 dogfood exposed that harmony analysis treated `piano_control` events as chord notes. Harmony analysis now ignores non-note pad events, preserving S28 continuous-pedal controls while still analyzing pitched harmony.

## Non-goals

- no automatic chord-progression generation;
- no genre/style progression table;
- no key change or modulation inference;
- no change to S29 motif lineage;
- no change to S27/S28 instrument engines;
- no change to S27-M ensemble interaction;
- no bus-ducking/mastering workaround.

## Flagship

`Threadline at First Light` remains the controlled 16-bar / 24 kHz / 112 BPM flagship. A is the CLOSED S29 thematic baseline. B keeps the same form, thematic variants, rhythm, lead, drums, instrument engines, seed, mix, and ensemble interaction; B changes only explicit section progression variants routed to piano and bass.

Treatment degree paths:

- verse: `1 → 6 → 3`;
- pre: `4 → 5`;
- chorus: `6 → 7 → 3 → 1`;
- return: `4 → 6 → 5`;
- final: `5 → 1`.

Render evidence before full repository closure:

- duration: 36.485708 s;
- A RMS: 0.09984945;
- B RMS: 0.10631830;
- A peak: 0.68796487;
- B peak: 0.66769163;
- B clipped sample ratio: 0.0;
- piano pitch events changed: 38;
- bass pitch events changed: 33;
- lead event identity: exact;
- drum event identity: exact;
- piano/bass timing, duration, velocity and controls: exact.

## Engineering validation

- focused S30 + S29 + S15 + S27-M R2: **36/36 PASS**;
- full repository: **97 test files / 651/651 PASS**;
- Composition Brief schema/reference parity: PASS;
- post-v1.16 intentional-source hash allowlist: PASS;
- standalone skill self-check: PASS;
- canonical Skill validation: PASS;
- plugin distribution validation: PASS;
- compileall: PASS;
- Skill / Codex / Claude builds: PASS.

Raw B is 0.545 dB higher in whole-song RMS than A because the authored voicings redistribute energy. Audition packaging therefore keeps raw evidence and additionally provides RMS-matched A/B with B gain `0.93915587` (-0.545 dB) so perceptual preference is not driven by loudness.

## Closure gate

Engineering gate is CLOSED.

## Perceptual closure

On 2026-09-23, the user completed the controlled listening gate and chose to proceed. S30 is therefore **CLOSED / PERCEPTUAL PASS**. The accepted treatment creates the intended harmonic departure → tension → arrival → return → final-resolution arc while retaining the S29 thematic lineage. The RMS-matched A/B remains the closure evidence.
