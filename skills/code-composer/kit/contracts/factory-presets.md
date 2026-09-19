# Factory Presets

Factory presets are **versioned sonic resources**, not composition examples.

## Boundary

- Presets may contain instrument-engine patch parameters and capability metadata.
- Presets must not contain notes, MIDI events, melodies, motifs, rhythms, chords, progressions, form, or arrangement content.
- The agent selects a preset from the user's sonic intent and the current composition context; it must not infer a melody, rhythm, harmony, or arrangement from the preset.
- `kit/presets/CATALOG.json` is the agent-facing catalog. It intentionally omits raw patch values.

## Selection

Prefer capability matching over name matching. Inspect:

- `character`
- `strengths`
- `limitations`
- `recommended_roles`
- `expression_capabilities`
- `engine` / `family`

Do not treat a limitation as a quality score. It describes the intended operating range.

## Brief authoring

A sound-palette role may use either an explicit `patch` or a factory `preset_id`, never both. S17 extends this to the `drums` role through registered percussion-patch validation.

```json
{
  "sound_palette": {
    "roles": {
      "lead": {
        "preset_id": "<select-from-catalog>",
        "preset_version": "1.0.0",
        "patch_overrides": {}
      }
    }
  }
}
```

`patch_overrides` are optional song-local sound-design changes. They may not replace preset identity fields (`kind`, `engine`, `family`).

## Materialization invariant

At compile time the factory preset is copied and overrides are applied. The resulting **fully materialized patch** is written into canonical Music IR together with exact `preset_provenance`.

The rendered song therefore does not depend on whatever version of the factory preset becomes current later.

## CLI

Use `code-composer-presets list` to discover capabilities, `show <preset-id>` for one metadata record, and `materialize <preset-id>` only when an explicit patch view is operationally necessary.
