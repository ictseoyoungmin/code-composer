# S7 — Physical String-Crossing Continuity & Coupling — CLOSED

Date: 2026-09-17

## Closure

S7 adds `bowed.violin.modeled_coupled@1.0.0` without changing S5 `modeled_open` or S6 `modeled_continuous`. The S7 renderer retains independent violin-string waveguide states, transfers bow contact over a finite adjacent-string overlap, and lets the released string continue a bounded bridge residual into the common body/radiativity stage.

This is a conservative deterministic bridge/body coupling approximation. It does not claim a measured violin, finite-element body feedback, continuous double-stop physics, or advanced bounce articulations.

## Validation

- S7 focused tests: **6 / 6 PASS**
- bowed-waveguide / violin focused set: **39 / 39 PASS**
- source regression: **360 / 360 PASS**
- clean-installed regression: **360 / 360 PASS**
- bowed-waveguide focused coverage: **93.22%**
- self-check / isolated Skill validation / compileall: **PASS**
- import sweep: **124 modules / 0 failures**
- static graph: **124 modules / 180 internal edges / 0 cycles**

Full-suite coverage tracing is not used as a closure blocker because Python per-sample physical-model tracing expands runtime disproportionately; the changed bowed-waveguide module is measured directly.

## Backward compatibility

The same S6 crossing phrase rendered from the original S6 repository and from S7 using `modeled_continuous` is byte-identical: `67c6d89b2145c89d85e890d6138e94fa51acbfccfbf32bf8f233605c803dd3ff`.

Legacy A/B/C WAVs are also byte-identical:

- A `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

## Crossing evidence

Repository-only dogfood realizes `G → D → A → E → E`. The first three boundaries are actual adjacent-string crossings. Relative to S6 reset-on-string-change behavior, S7 retains more 30 ms post-boundary energy and reduces the single-sample boundary jump at all three crossings. These metrics verify removal of the structural reset seam; they are not treated as a perceptual quality score.

S7 coupled WAV SHA-256: `55a43efd22104fb636910419c62cb88c1cf3513f932748a923418a8c7d57da9c`. The clean-installed wheel reproduces the same hash.
