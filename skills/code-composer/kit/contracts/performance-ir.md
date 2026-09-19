# Performance IR Contract

Performance IR carries explicit expressive realization instructions such as phrase dynamics, timing, gate/articulation and bounded microvariation. The deterministic engine realizes authored expression; it does not infer phrase shape from bundled examples.

Schema: `kit/schemas/performance_ir.schema.json`.

## S11 phrase-level instrument expression

A phrase may optionally contain `instrument_expression_curves`. This surface is authored musical intent, not an automatic humanizer. Supported S11 controls are:

- `bow_pressure`
- `bow_speed`
- `bow_position`
- `bow_noise_gain`
- `vibrato_rate_hz`
- `vibrato_depth_cents`
- `vibrato_onset_s`

Each value is a normalized phrase-position curve whose first point is at `0.0` and last point is at `1.0`. During performance realization, the curve is interpolated at each note onset and written to `performance.instrument_expression`. Existing event-local instrument-expression values are more specific and therefore override the phrase value for that control only.

When `instrument_expression_curves` is absent, S11 adds no event field and preserves the pre-S11 Performance IR realization path byte-for-byte for matched deterministic inputs.

The phrase layer does not invent notes, rhythms, harmony, orchestration, fingering or special techniques. Violin physical realization consumes authored bow controls when present and fills only controls that remain absent.


## S15 ensemble interaction

Performance IR may explicitly describe inter-player timing/yielding at the orchestration-section level and role pan offsets at the realization level. See `contracts/ensemble-interaction.md`. These surfaces are authored intent: runtime does not infer leadership or ensemble feel from a genre/style label.
