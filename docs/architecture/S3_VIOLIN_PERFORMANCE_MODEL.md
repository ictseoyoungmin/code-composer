# S3 Violin Performance Model

## Purpose

S3 separates **musical authorship** from **physical violin realization**. The composition decides what notes and rhythms exist. The violin planner decides how a conventional player could physically realize an already-authored monophonic line.

The planner is deliberately downstream of composition and upstream of both synthetic bowed-string audition and future notation export.

```text
Music IR / resolved events
        ↓
Violin Performance Planner
  ├─ left-hand path
  │   ├─ string
  │   ├─ position
  │   ├─ finger
  │   └─ shift/crossing evidence
  └─ bow path
      ├─ grouping
      ├─ down/up direction
      ├─ normalized bow usage
      └─ force/speed control targets
        ↓
realized Music IR + playability report
        ├─ bowed-string synthetic audition
        └─ future notation / human handoff
```

## Physical scope

S3 uses conventional violin tuning G3-D4-A4-E5 and plans pitches from G3 through A7. Each pitch receives multiple candidate string/hand/finger realizations where physically plausible. A deterministic dynamic-programming path minimizes left-hand position shifts, string crossings, high-position burden, and chromatic finger extension under the available transition time.

The resulting `transition score` is an internal planning metric. It is evidence for Code Composer, not a universal pedagogical grade or claim about a specific player's skill.

## Bow model

S3 treats bowing as a finite directional gesture, not as note gate length. Consecutive authored `legato` notes may share one bow while the group's duration stays within the configured bow-duration budget. Other articulation boundaries start a new bow. Bow groups alternate down/up direction deterministically.

Bow force and speed are normalized engine control targets derived conservatively from the already-authored event dynamics. They are not Newton/metre-per-second measurements. Existing authored `instrument_expression` values always take precedence.

S3 intentionally does not invent vibrato style, portamento, harmonics, pizzicato, spiccato/ricochet bounce behavior, double stops, scordatura, or notation marks.

## Comfort gate

Default CLI operation uses `strict_comfort=true`. If the best path exceeds the comfortable transition threshold, planning fails rather than silently calling the line human-friendly. `--allow-challenging` exists for inspection and iterative revision; it preserves the line and reports the difficulty classification.

The planner never changes pitch or rhythm to make a passage easier. Any musical simplification must be an explicit Composer Agent/user revision.

## Current limitation

The position model is a deterministic fingering planner for production validation, not a substitute for a professional violinist's final editorial fingering. Individual players may choose different strings and fingerings for tone, phrasing, anatomy, or school/tradition. Human-facing score export remains a later slice.
