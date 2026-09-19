# S4 — Violin Double-Stop Realization Closure

**Status:** CLOSED  
**Engine:** v1.17.0  
**Date:** 2026-09-17

S4 extends S3 physical violin realization with a deliberately conservative two-note bowed double-stop surface. It does not compose, revoice, simplify, or silently rewrite notes.

## Closed scope

- At most two simultaneous pitches at one onset.
- Adjacent violin strings only.
- Equal duration and shared articulation inside each double stop.
- Open-string and stopped adjacent-string realizations.
- Conservative same-finger stopped fifth handling.
- Hand-frame checks for position gap, stopped-note span, and finger-order consistency.
- Shared bow direction/position/force/speed evidence for both notes.
- Deterministic single-note ↔ double-stop transition planning.
- Existing authored instrument expression remains authoritative.

Explicitly **not** claimed: triple/quadruple stops, rolled chords, staggered overlapping voices, harmonics, pizzicato/arco switching, bounce articulations, scordatura, or notation export.

## Architecture

The S3 surface remains `performance/violin.py`. Common fingering and transition mechanics were extracted into `performance/violin_mechanics.py`; the S4 two-note planner is isolated in `performance/violin_double_stop.py`. This removes a transient import cycle and leaves the package graph acyclic. Same-onset two-note material routes to S4; monophonic material stays on the S3 path.

## Backward compatibility

The 48-event S3 monophonic dogfood produced identical per-event realization and playability under S3 and S4. Legacy A/B/C render hashes remain byte-identical:

```text
A  93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba
B  7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377
C  db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f
```

## Double-stop dogfood

A repository-only seven-note fixture containing three two-note gestures passed default strict-comfort planning:

```text
classification          comfortable
max transition score    0.37
max gesture score       1.0
max difficulty score    1.0
double-stop events      6
WAV SHA-256              9fb55327feba2f0f6d1cdc76af757fa4d17602217b8842bdf07755c29a181f73
```

The musical dogfood is validation evidence only and is not shipped inside the agent Skill.

## Validation

```text
Focused S3/S4             23 / 23 PASS
Source regression        344 / 344 PASS
Clean-installed regression 344 / 344 PASS
Coverage                   92.799%

violin.py                  92.708%
violin_mechanics.py         89.000%
violin_double_stop.py       94.650%
violin_cli.py               89.286%

Import modules              122
Import failures               0
Static modules              123
Static edges                177
Cycles                        0
compileall                  PASS
Self-check                  PASS
Skill validation            PASS
```

Clean-installed wheel SHA-256: `a9951e95821788af29231bed5fc293444a3ba1468656ccafdfec81488d19b8b9`.

## Packaging

```text
Standalone Skill      183 files
Codex plugin          185 files
Claude plugin         185 files
Forbidden artifacts     0
Codex subtree         exact
Claude subtree        exact
```

The installed Skill still contains no polished musical examples or validation WAV/MIDI material.
