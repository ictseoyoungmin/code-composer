# CR08 — Resonant Release Semantics / Plucked Instrument Tail Authority

Status: **CLOSED**

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


## Listening closure — 2026-09-27

The matched CR08 A/B listening pack was delivered after the engineering gate.
The user explicitly approved proceeding on 2026-09-27, so the required human
perceptual gate is recorded as **PASS**.

This is human closure evidence, not an analyzer-derived aesthetic score.

Validated pre-merge evidence:
- candidate HEAD: `43c6453546174072bc1c6093e593f2ffc91cae0f`
- CR08 dogfood #4 / run `36317982806`: SUCCESS
- full CI #126 / run `36317982805`: SUCCESS
- blocking regression: Python 3.10 / 3.12 each `763 passed / 3 deselected`
- artifact #10931267884
- artifact digest: `sha256:d11825650a86ac0887c489c70b64cd3e6b5f63818cd6cd7192bc60c9de7e55fb`
- portable SHA256 manifest: PASS
- phrase A/B: 24 kHz / clipping 0
- isolated probe authored gate: 0.18 s
- gate-cut buffer: 4320 samples
- resonant buffer: 21599 samples
- post-gate RMS gate-cut → resonant: 0 → 0.0657406
- late-tail RMS: 0.00868024

Canonical CLOSED status is finalized only after merge and post-merge main CI.


## Canonical merge evidence

- listening closure HEAD: `de87e6f167a9fc6a2a10de41f0b7b387ad313054`
- PR #41 squash merge: `ada1703792919451abd32fad382e1f3ae5fee219`
- post-merge main CI #128 / run `36320753259`: SUCCESS
- Python 3.10 / 3.12: SUCCESS
- Issue #40 may be closed after this evidence-only closure patch reaches main.
