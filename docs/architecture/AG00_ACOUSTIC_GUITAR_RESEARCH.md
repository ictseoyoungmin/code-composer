# AG00 — Acoustic Guitar Research / Provenance Map

Status: **RESEARCH PASS COMPLETE · IMPLEMENTATION NEXT**

Target release: **v1.19.0 — Acoustic Guitar Performance System**

This document narrows the research basis for AG00–AG09. It is not an implementation spec and does not make third-party code or measured data normative.

## Design conclusion

The existing Code Composer engine boundary is suitable for adding a new acoustic-guitar instrument, but the complete v1.19 scope requires one architecture hardening pass before DSP work:

1. keep `InstrumentEngine.render_note()`, `render_track()`, `tail_seconds()`, validation, and factory-preset provenance;
2. add an instrument-scoped performance payload for structured non-generic mechanics such as string/fret/right-hand intent;
3. add a general instrument-action event path so body taps/slaps do not become hard-coded global Performance Score event types;
4. generalize instrument mechanics realization so guitar does not create a second family-specific branch beside violin;
5. implement complex guitar DSP as a package, not a new monolithic `audio/acoustic_guitar.py`.

## Evidence map

| Slice | Research signal | Resulting contract/design constraint |
|---|---|---|
| AG00 | Laurson/Erkut/Välimäki; Cuzzucoli/Lombardo | Separate authored performance control from physical resonator state. |
| AG01 | Karjalainen et al.; Bécache et al.; Ma/Xiong; Wühle et al. | String → bridge → body/radiation is causal and modular; objective complexity does not replace listening. |
| AG02 | Perez-Carrillo; Vodka et al.; Atre/Apte | String/fret are real performance state, not incidental metadata. |
| AG03 | Cuzzucoli/Lombardo; Perez-Carrillo; Germain/Evangelista; Pluta et al. | Finger/nail/pick/trajectory must alter excitation, not merely post-EQ or gain. |
| AG04 | Karjalainen/Vodka groundwork | Left-hand damping/state transitions remain explicit mechanics; no hidden note rewriting. |
| AG05 | Laurson et al.; Perez-Carrillo | Fingerstyle is independent multi-string performance with overlapping resonances. |
| AG06 | existing Composer-first timing authority | Strum direction/traversal is authored performance; engine does not invent chord/rhythm content. |
| AG07 | Martelloni/McPherson/Barthet 2020/2021 | Body percussion belongs to the same guitar/body system and should preserve hit-zone identity. |
| AG08 | Laurson et al.; Elejabarrieta et al.; Torres/Boullosa; Ma/Xiong | Persistent six-string/body state and shared bridge/body coupling are required for continuous performance. |
| AG09 | Wühle/Merchel/Altinsoy | Human listening remains closure authority for musical quality. |

## Steel-string calibration rule

A substantial part of the classic guitar-physics literature uses nylon/classical instruments. v1.19 may reuse those sources for general causal structure—pluck phases, bridge coupling, soundboard/back/air modes—but must **not** copy their fitted parameters as steel-string constants.

Steel-string-specific references (Wühle et al. 2025; Ma & Xiong 2026; the earlier steel/plucked-string literature) and Code Composer's own AG01 listening evidence are the calibration authority.

## AG01 first bottleneck

Before strum, fingerstyle, or body percussion is expanded, AG01 must prove that isolated E2–E4 notes are recognizable as a generic steel-string acoustic guitar rather than a zither, generic Karplus-Strong pluck, or electric/synthetic pluck.

The first render comparison should hold pitch, timing, velocity, and output level as constant as practical while varying only the candidate acoustic-guitar physical path.

## Provenance boundary

Research references are conceptual/validation inputs only. v1.19 currently bundles no third-party:

- guitar source code;
- body or bridge impulse response;
- recordings or note datasets;
- measured modal tables;
- FEM meshes;
- motion-capture/performance data;
- commercial/named-instrument fitted values.

Any later measured asset must pass the existing exact-source, checksum, license, units, attribution, preprocessing, and redistribution checklist in `CREDITS.md`.
