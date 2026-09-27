# CR07 — Broader Orchestration Dogfood

Status: **CLOSED**

Issue: #37

## Purpose

CR07 proves that the Composer-first Song model remains **track-function agnostic**
across materially different ensembles. The test is not whether Code Composer can
recognize a fixed list of arrangement roles; it is whether authored track identity
and function survive unchanged through lowering, performance-score binding, physical
realization, and rendering.

## Contract under test

- `track.function` is arbitrary authored descriptive text.
- lowerers must preserve track IDs / functions exactly.
- no six-role grammar or role-order table may be required for the Composer-first path.
- unknown instrument families are allowed only when the Composer supplies an explicit
  compatible `render_lock.preset`; CR07 does **not** add a generic fallback.
- Performance Score and realized IR must cover the exact authored track set.
- Performance Score v1 carries explicit `drum` hit events for percussion engines; pitched-note drum surrogates are rejected before render.
- rendering remains deterministic and provenance-bound.

## Dogfood set

1. **Copper Lines** — band / rock-like: clean electric guitar, modeled finger bass,
   acoustic kit, electric keys. Functions: `offbeat-chop`, `root-motion`,
   `backbeat-grid`, `upper-answer`.
2. **Glass Courtyard** — chamber: modeled violin, acoustic piano, explicitly locked
   lower bowed generic voice. Functions: `bowed-cantus`, `resonant-floor`,
   `inner-breath`.
3. **Blue Relay** — electronic: modeled low pulse, generic pad, generic lead,
   acoustic kit. Functions: `sub-pulse`, `air-bed`, `glass-hook`, `sync-grid`.

These are independent authored pieces with different tempo, meter/texture, track
count, instrument-family vocabulary, and note material.

## Engineering gate

- all three Song + Performance Score fixtures validate;
- Song → Execution Plan preserves exact track IDs/functions;
- explicit unknown-family preset locks resolve deterministically;
- Execution Plan → realized IR preserves exact track IDs;
- 24 kHz real renders contain finite samples and zero clipping;
- fingerprints and artifact hashes are reproducible;
- focused CR07 regressions plus repository CI remain green.

## Perceptual gate

Engineering success does not rank the pieces or certify musical quality. Closure
requires listening to the three rendered miniatures and confirming they sound like
coherent excerpts rather than broken orchestration-path fixtures.

No automatic genre score, aesthetic score, or preferred ensemble is introduced.


## CR07 blocker resolved — explicit drum-hit authority

The first real band/electronic render exposed a missing Composer-first contract:
Performance Score v1 could author pitched notes and piano sustain controls, while the
percussion engine intentionally accepts explicit drum events only.

CR07 therefore adds one narrow public event type:

```json
{
  "id": "d-b1-k1",
  "type": "drum",
  "start_beat": 0.0,
  "duration_beats": 0.16,
  "drum": "kick",
  "velocity": 0.48
}
```

This is authored musical/performance state, not inferred orchestration. The bridge
lowers it one-to-one to the existing runtime `event_type: "drum"` surface. A
percussion engine rejects pitched-note surrogates; a non-percussion engine rejects a
drum hit. Continuous hi-hat pedal control remains outside CR07 rather than being
implicitly invented.


## Closure — 2026-09-27

CR07 is **CLOSED**.

Engineering evidence:
- validated candidate: `5ebf7f0888eb69ffb8c94b9eff96f5be1b2eba40`
- CR07 dogfood #13 / run `36313943714`: SUCCESS
- full CI #119 / run `36313943715`: SUCCESS
- blocking regression on Python 3.10 / 3.12: `758 passed / 3 deselected` each
- CR03 piano/violin dogfood #43 / run `36313943700`: SUCCESS
- artifact `10929852459`, digest `sha256:0002ec2b9f0d0d8f798f7373435be11f7c5fc25d070fbc823baba07ec391e1e3`
- all three CR07 renders: 24 kHz, finite audio, clipped sample ratio 0
- authored track IDs/functions preserved through Song → Execution Plan → Performance Score → realized IR
- explicit unknown-family preset locks preserved; no generic family fallback added
- Composer-first explicit `drum` hit authority added and validated

Perceptual authority:
- the three-piece listening pack was delivered after the engineering gate.
- the user explicitly instructed the agent to proceed with **listening closure** on 2026-09-27.
- this closes the required human/perceptual gate; it is not an automatic aesthetic score, genre ranking, or analyzer-derived quality verdict.

The known runner-sensitive legacy drum byte-exact probe tracked by Issue #2 remains
non-blocking and does not override the successful blocking regression suite.
