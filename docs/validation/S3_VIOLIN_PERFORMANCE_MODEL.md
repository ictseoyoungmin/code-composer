# S3 — Violin Performance Model Closure

**Status:** CLOSED  
**Engine baseline:** v1.17.0  
**Date:** 2026-09-17

## Purpose

S3 adds a physical-performance planning boundary for a real conventional violin without turning that boundary into a composition generator. Notes, rhythm, harmony, phrasing intent and explicit expression remain authored upstream. S3 only realizes an existing monophonic violin line into string/position/finger and bow mechanics plus playability evidence.

## Scope

S3 v1.0 supports standard G3-D4-A4-E5 tuning, planning range G3..A7, monophonic fingering paths, contextual string/position/finger selection, chromatic low/high-finger alteration, position-shift/string-crossing evidence, legato bow grouping, deterministic down/up bow direction, normalized bow usage and conservative bow-force/speed control targets.

Default planning is strict-comfort. If the best deterministic path exceeds the comfortable transition threshold, the command rejects the line rather than silently calling it human-friendly. `--allow-challenging` keeps the musical material intact and exposes the difficulty evidence for explicit revision.

The numeric transition score is an internal deterministic planning metric, not a universal violin pedagogy grade. Individual violinists may choose different fingerings for tone, anatomy, technique or interpretive reasons.

## Musical-authority boundary

S3 does not change pitch/rhythm to improve playability and does not invent vibrato, portamento or special-technique taste. Existing `performance.instrument_expression` values take precedence. Only absent bow force/speed controls are filled from already-authored event dynamics.

The existing `bowed_string` synthesis engine can consume those compatible controls for audition, while the same realization JSON is retained as future human-score/notation planning evidence.

Not yet supported: double/multiple stops, harmonics, pizzicato/arco switching, physical spiccato/ricochet bounce, scordatura, MusicXML/engraving.

## Public surface

```bash
code-composer-violin INPUT_IR.json TRACK_ID OUTPUT_IR.json [--allow-challenging]
```

Agent-facing routing is documented in `kit/workflows/violin-performance.md` and `kit/contracts/violin-performance.md`. The report schema is shipped as `violin_performance.schema.json`.

## Dogfood

Repository-only dogfood used the factory `bowed.violin.synthetic_warm` sound on an existing 48-note lead. Strict-comfort planning passed:

- events: **48**
- classification: **comfortable**
- max transition score: **0.960887**
- strings selected: **G, D, A**
- maximum selected position band: **6**
- dogfood WAV SHA256: `1f7ee597435fa35dce92f0d44e0def7d131eac83edeaa256ad49f6fb2ba7329b`

The dogfood composition/audio remains validation-only and is not shipped inside the installed Skill.

## Backward compatibility

S2 contained 118 Python source files. S3 keeps all **118/118 existing Python files byte-identical** and adds only:

- `app/violin_cli.py`
- `performance/__init__.py`
- `performance/violin.py`

Legacy final dogfood A/B/C remain byte-identical:

- A `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

## Validation

- Focused S3 tests: **12/12 PASS**
- Full source regression: **333/333 PASS**
- Clean-installed wheel regression: **333/333 PASS**
- Coverage: **92.71%**
- `performance/violin.py`: **91.88%**
- violin CLI: **89.29%**
- `compileall`: **PASS**
- import sweep: **120 modules / 0 failures**
- static graph: **121 modules / 173 edges / 0 cycles**
- standalone Skill self-check: **PASS**
- skill validation: **PASS**
- clean standalone ZIP -> wheel -> isolated install: **PASS**
- public console entrypoints: **8**

## Packaging

- standalone Skill: **181 files**, forbidden build/cache/audio/MIDI artifacts **0**
- Codex plugin: **183 files**
- Claude plugin: **183 files**
- both plugin embedded Skill subtrees: **exact byte match** to standalone Skill

S3 closes the first physical violin realization bottleneck. Future slices can extend technique breadth or notation export without weakening the separation between musical authorship and instrumental mechanics.
