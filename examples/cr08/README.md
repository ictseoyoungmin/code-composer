# CR08 — Resonant Release Dogfood

**Silk Afterimage** is a short F# minor zither + keys bottleneck piece.

The canonical Song/Performance Score is rendered twice from the same authored state:

- `phrase_gate_cut.wav` — diagnostic baseline with only the zither preset's
  `natural_tail_s` changed to zero after lowering;
- `phrase_resonant.wav` — canonical CR08 resonant-pluck preset.

The diagnostic does not rewrite notes, timing, pitch, expression, or mix. It exists
only to expose the old failure mode where sample lifetime ended with the authored
gate.

The artifact also contains isolated one-note probe A/B files for objective boundary
inspection. Listening remains the perceptual authority for closure.
