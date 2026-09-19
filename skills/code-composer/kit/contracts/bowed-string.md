# Bowed String Engine Contract

The `bowed_string` engine is a deterministic family engine for explicitly authored bowed-string patches. It does not embed a named violin/cello preset.

Authoring shape:

- `kind`: `bowed_string`
- `engine`: `bowed_string`
- optional semantic `family`
- `bowed_string_graph.strings`: harmonic/string parameters
- `bowed_string_graph.bow`: bow position, pressure, speed, friction-noise parameters
- `bowed_string_graph.vibrato`: rate, depth, onset, fade
- `bowed_string_graph.envelope`: attack and release
- optional `bowed_string_graph.body`: explicit body resonances

Optional event-level `performance.instrument_expression` controls consumed by this engine are documented by the engine registry and include bow pressure/speed/position, vibrato rate/depth/onset, bow-noise gain, and attack/release overrides.

The patch values must be chosen from the current composition intent. Do not copy timbral values from repository dogfood or validation fixtures.

Schema: `src/code_composer/reference/schemas/bowed_string.schema.json`.
