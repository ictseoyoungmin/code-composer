# CR08 — Resonant Release Semantics / Plucked Instrument Tail Authority

Status: **IMPLEMENTATION / LISTENING CANDIDATE**

Issue: #40

## Trigger

A real gayageum club-track dogfood exposed an audible phrase defect: the authored
note ended and the synthesized buffer ended with it, so string/body resonance was
cut inside phrases and at bar boundaries.

The uploaded before/after packages are unusually clean regression evidence:

- the before and sustain-fix authored IR files are byte-identical;
- both have SHA-256 `2fc42e79fa75e7a9b72ce51348f48554bb90615e6f34e87833fdf47a73d2f508`;
- the original renderer allocated only `written duration + 0.12 s`;
- the sustain-fix renderer added 0.42–0.85 s depending on ornament and applied a
  post-gate decay;
- therefore the audible fix lived only in piece-specific renderer code.

CR08 moves the useful semantic upward without copying the song-specific ornament
table.

## Contract

For instrument engines, note `duration_s` is the authored gate/excitation duration.
It is **not** a universal mandate that the returned sample buffer must end at
note-off.

An engine that owns physical/resonant decay may:

1. return samples beyond authored note-off;
2. report its maximum additional lifetime with `tail_seconds(patch)`;
3. let that resonance overlap later beats/bars;
4. consume explicit numeric performance expression such as pitch approach,
   vibrato, or release damping;
5. remain deterministic.

The renderer already allocates the maximum of mix tail and engine tail. CR08 uses
that existing boundary instead of adding a song-specific release table to
`render.py`.

## First opt-in engine

`resonant_pluck` + factory preset `resonant_pluck.zither_bright`.

The preset is a general deterministic zither-like physical/parametric sound design.
It does **not** claim measured or sampled gayageum replication.

The engine separates:
- onset/excitation;
- authored gate duration;
- partial/body natural decay;
- post-gate damping;
- final numerical boundary fade.

No ornament string such as `slide`, `bend`, `tremolo` selects a hard-coded
tail duration. Expression is numeric and authored.

## Matched dogfood

**Silk Afterimage** — F# natural minor / 112 BPM / 8 bars.

The same Song + Performance Score is rendered twice:

- diagnostic gate-cut baseline: only `natural_tail_s` is set to zero after
  canonical lowering;
- resonant candidate: the unchanged factory preset is used.

Notes, timing, pitch, expression and mix remain identical.

## Closure

Engineering gate:
- focused CR08 tests PASS;
- complete repository CI PASS;
- existing engine/audio regressions remain unchanged;
- isolated probe has measurable post-gate energy only in the resonant candidate and
  that energy decays;
- full phrase renders at 24 kHz with finite audio and clipping 0;
- portable artifact hashes PASS.

Perceptual gate:
- listen to matched phrase A/B;
- verify short authored gates no longer sound unnaturally chopped;
- reject excessive smear or uncontrolled resonance buildup.

Tests do not certify the musical result and no aesthetic score is introduced.
