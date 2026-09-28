# Instrument Engine Contract

Use this contract only when the task needs to author or extend an instrument patch. Normal composition should stay at the workflow/brief level.

## Boundary

An instrument patch resolves to exactly one registered engine. Pitched families use note/track rendering; percussion keeps explicit drum events while using the engine boundary for validation and tails. The engine owns:

- note rendering,
- optional stateful whole-track rendering,
- any tail beyond symbolic note-off,
- optional track-wide post-processing,
- engine-specific IR/runtime/authoring validation,
- the names of optional `performance.instrument_expression` controls it consumes,
- validation of optional canonical `instrument_performance` payloads,
- validation of optional non-note `instrument_action` events,
- optional engine-owned mechanics realization before rendering.

The render pipeline must not branch on concrete instrument families.

## Resolution

Prefer an explicit `engine` field for new engine-specific patches. Legacy generic and piano patches remain readable through compatibility inference.

Built-in engine names are currently `generic`, `piano`, `bowed_string`, `bowed_waveguide`, `plucked_bass`, `resonant_pluck`, `percussion`, and `acoustic_guitar`. `bowed_string` is the legacy synthetic/additive bowed family; `bowed_waveguide` is the modeled causal bow/string engine.

## Extension rule

A new instrument family should normally add an engine module and register it. Do not add `if violin`, `if cello`, or similar branches to the central renderer.

Related family instruments should share an engine when their physical/performance model is substantially the same. A semantic `family` field may distinguish user-authored designs without changing the engine boundary.

## Instrument-scoped performance and actions

Performance Score note events may carry an optional `instrument_performance` object. The core score validator checks only that it is deterministic JSON-compatible data; the resolved engine owns semantic validation. Unsupported payloads are hard errors, not ignored hints.

Performance Score may also carry `instrument_action` events with an authored action identifier plus structured parameters. The resolved engine must explicitly opt in through `validate_action_event`; unsupported actions are hard errors. Engines that eventually render actions should normally use stateful whole-track rendering so actions and notes share one physical state.

Physical realization is selected declaratively by the engine's `mechanics_realizer` identifier and executed through the performance-domain mechanics registry. Audio-engine modules must not import performance realizers, and the central performance bridge must not add new family-specific mechanics branches.

## Performance expression

Universal timing, velocity, gate, and articulation remain part of the common performance path. Engine-specific continuous controls may be supplied under an event's `performance.instrument_expression` object. Engines must ignore unsupported keys rather than infer extra musical intent.

## Taste isolation

Schemas and templates may describe fields and legal ranges. Factory presets may be bundled as versioned sonic resources, but they must contain no melody, rhythm, harmony, form, or arrangement content. Examples remain operational only; repository dogfood stays outside the installed Skill.
