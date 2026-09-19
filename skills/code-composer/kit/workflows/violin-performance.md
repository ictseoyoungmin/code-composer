# Human-playable violin realization

Use this workflow only after the musical notes/rhythm are already authored and the target track uses a supported bowed violin engine (`bowed_string` or `bowed_waveguide`) with `family=violin`.

1. Confirm the requested line is intended for real violin performance, not merely violin-like synthesis.
2. Keep the melody, intervals and rhythm unchanged. Do not simplify the composition silently.
3. S4 accepts monophonic notes and conservative synchronous two-note double stops. A double stop must use one onset, equal duration and one articulation; triple stops and staggered overlapping voices remain out of scope.
4. Run `code-composer-violin INPUT_IR.json TRACK_ID OUTPUT_IR.json`.
5. Inspect `violin_performance_report.playability`, per-event left-hand/bow realization, and any `double_stop` gesture evidence.
6. If default strict-comfort rejects the line, decide explicitly whether to revise the composition or inspect with `--allow-challenging`. Do not relabel a challenging line as comfortable.
7. If long-phrase shaping is explicitly authored, use Performance IR `instrument_expression_curves` to coordinate bow pressure/speed/contact position and vibrato across the phrase before violin mechanical realization. Event-local controls remain authoritative. Do not invent these curves from bundled examples.
8. Render the realized IR if audition is useful. `bowed.violin.modeled_continuous` consumes planned same-string bow groups/directions as continuous waveguide state. `bowed.violin.modeled_coupled` additionally keeps physical-string states alive across adjacent G/D/A/E crossings. `bowed.violin.modeled_admittance` adds a weak causal bridge/body feedback loop. `bowed.violin.modeled_expression` keeps that physical path and adds deterministic performance-to-timbre microvariation for a less cloned/repeated tone; S11 phrase curves can drive its authored long-term control targets. `bowed.violin.modeled_realistic` adds the S12 technique-aware layer: open/stopped-string behavior, finite position shifts, crossing-force transfer, and bow retakes after sufficient rests. `bowed.violin.modeled_articulated` keeps that S12 arco path and, only for explicitly authored events, adds S13 pizzicato, harmonic, and spiccato rendering. `modeled_open` and `synthetic_warm` remain valid alternatives.
9. For a human handoff, treat the JSON realization as planning evidence. S4 does not yet claim MusicXML/engraving support.

Do not infer vibrato taste, portamento style, chord voicing, or special techniques from bundled material. S13 articulations must be explicitly authored or explicitly requested. Preserve authored expression and user intent.
