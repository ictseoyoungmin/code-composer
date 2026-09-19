# Violin Performance Contract

This boundary turns already-authored violin notes into an explicit physical realization for a conventional four-string violin. It does **not** compose notes, rhythms, harmony, or style.

## Scope

S4 extends the S3 monophonic planner with conservative synchronous double-stop realization. It supports:
- standard G3-D4-A4-E5 tuning;
- MIDI 55..105 (G3..A7) planning range;
- monophonic notes plus at most two pitches at one onset;
- bowed double stops on adjacent strings only;
- equal duration and one shared articulation for the two notes of a double stop;
- one shared bow gesture/contact-string pair for the two notes;
- open-string double stops and stopped adjacent-string fingerings;
- conservative same-finger stopped fifths when both strings use the same longitudinal stop point;
- conservative hand-frame checks for position gap, finger ordering and stopped-note span;
- contextual transition planning between single-note and double-stop gestures;
- string, position, finger and chromatic finger alteration;
- legato bow grouping, alternating down/up bow direction and normalized bow usage;
- bow force/speed targets derived from already-authored event dynamics;
- preservation of explicit `instrument_expression` values;
- S12 opt-in bow-retake planning for sufficiently separated groups when the selected patch enables `realism_hardening`.

The default double-stop comfort envelope is intentionally conservative: maximum one position-band difference and seven semitones of stopped-note longitudinal span. These are deterministic planning constraints, not universal pedagogy laws, and may be tightened through planner configuration.

S13 additionally recognizes explicitly authored monophonic `pizzicato`, `harmonic`, and `spiccato` articulations. The planner attaches deterministic `technique` evidence without changing authored MIDI; for harmonics, MIDI is always the sounding pitch. Natural partials are preferred when close to the authored pitch, with conservative artificial-fourth or modeled-sounding-pitch fallback metadata.

Not yet supported:
- triple/quadruple stops or rolled chords;
- staggered/overlapping polyphony with different onsets;
- double-stop notes with independent durations or special articulations;
- ricochet/sautillé sequence generation;
- col legno or explicit sul ponticello/sul tasto notation;
- scordatura;
- MusicXML/engraved notation export;
- automatic musical vibrato or articulation decisions.

## Authority

Canonical Music IR remains the musical authority. Violin realization is downstream physical-performance state. The planner may reject mechanically unsuitable input, but it must not rewrite the melody or intervals to make them easier.

Every realized event receives:
- `performance.violin_realization.left_hand`
- `performance.violin_realization.transition`
- `performance.violin_realization.bow`

For a double stop, both notes also receive the same `gesture_id`, `gesture_type=double_stop`, and `double_stop` evidence including the partner pitch and selected adjacent string pair.

The existing bowed-string engine consumes only compatible `performance.instrument_expression` controls. Explicitly authored expression wins over planner defaults. S12 `modeled_realistic` also consumes already-realized string/finger/position/transition/bow evidence. S13 `modeled_articulated` consumes explicit articulation plus S13 `technique` evidence while preserving the S12 arco realization for ordinary notes. With S12/S13 disabled, pre-S12 realization and rendering remain unchanged.

## Playability

Default planning is `strict_comfort=true`. A line whose best deterministic path exceeds the comfortable transition/gesture threshold is rejected instead of silently claiming human playability. `--allow-challenging` may be used for inspection/hardening; it emits `challenging` or `impractical` evidence in the report.

The numeric transition and gesture scores are internal deterministic planning metrics, not universal violin difficulty grades.
