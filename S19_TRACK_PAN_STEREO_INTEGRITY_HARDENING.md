# S19 — Track Pan / Stereo Integrity Hardening

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Make `track.pan` predictable and stereo-safe across instrument engines. A track-level pan change must position an already-rendered stereo source at mixer level rather than collapsing its intrinsic stereo image to mono and repanning it inside the instrument/event path.

## Bottleneck discovered by post-S18 listening review

The matched post-S18 full-song render of *September Window, 5:42 PM* showed that the loudest section became spatially narrower even though S15 authored role-pan separation. Inspection isolated the legacy/non-graph path: non-zero `track.pan` was passed as the fallback event/engine pan, and stereo sources such as modeled violin and acoustic piano were reduced to mono before equal-power repanning.

A no-FX excerpt reproduced the defect:

- violin at `track.pan=+0.12`: L/R correlation ~1.000 versus ~0.936 at zero track pan;
- piano at `track.pan=-0.14`: L/R correlation ~0.99999 versus ~0.978 at zero track pan.

## Implemented semantics

- Instrument rendering starts from its intrinsic stereo image; `track.pan` is not passed as an instrument/event fallback.
- Explicit event `pan` remains event-local.
- Legacy engine track post-processing and legacy per-track insert FX run before track pan.
- Legacy `track.pan` is applied once with `audio.dsp.apply_pan`, the same stereo-balance operator already used by graph-mode routing.
- S18 post-instrument linear `track.gain` remains unchanged.
- `track.pan == 0` preserves the pre-S19 unpanned stereo render.
- Notes, rhythms, velocity, articulation, S15 timing/yielding and factory presets are unchanged.

## Focused regression

S19 focused tests cover:

- acoustic-piano intrinsic stereo preservation;
- S13 articulated-violin intrinsic stereo preservation;
- S16 modeled-bass pan parity;
- S17 modeled-percussion pan parity;
- legacy insert FX followed by stereo track pan;
- legacy pan parity with graph route-pan operator;
- explicit event pan remaining event-local before track-level balance.

Result: **7 / 7 PASS**.

## Full regression

- Source regression: **467 / 467 PASS** across **72 test files**.
- Clean-installed wheel regression: **467 / 467 PASS** across the same **72 test files**, source-path injection disabled.
- Import: **130 / 130**, static graph **130 modules / 191 edges / 0 cycles**.

## Full-song dogfood

The S18 control and S19 treatment use the identical full-song IR, including the same notes, velocities, gains, FX and authored S15 pan values. Only runtime pan semantics differ.

| Metric | S18 control | S19 treatment |
| --- | ---: | ---: |
| Duration | 69.55 s | 69.55 s |
| Peak | 0.347767 | 0.347767 |
| Clipping | 0 | 0 |
| Global stereo width | 0.054929 | 0.068687 |
| `open_field` stereo width | 0.035602 | 0.061314 |
| `last_bell` stereo width | 0.058669 | 0.077932 |

Master mono waveform correlation is **0.997932** and full stereo difference RMS is **0.00238129**. The musical center is therefore nearly unchanged while the lost stereo information is restored.

## Compatibility boundary

S19 intentionally changes non-zero legacy `track.pan` rendering because the old behavior conflated track-level positioning with event/instrument pan and destroyed stereo information. Zero track pan, explicit event pan semantics, graph route pan, S18 track gain semantics, and all S13–S17 instrument/ensemble behavior remain preserved.

## Next

Return to full-song listening. Do not preselect S20; open the next slice only from another reproducible audible or authoring bottleneck.
