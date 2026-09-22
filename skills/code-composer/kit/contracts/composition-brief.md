# Composition Brief Contract

The Composition Brief is explicit agent-authored musical intent passed into deterministic compilation. It should encode requested form, tonal/rhythmic/orchestration/development/transition constraints without relying on style-keyword tables inside the engine.

Validate against `kit/schemas/composition_brief.schema.json`. Do not invent fields outside the documented schema. User hard constraints must remain explicit rather than being hidden in prose.


## Explicit thematic variants

A Composition Brief may provide optional `materials.motif_variants`. Each variant is complete agent-authored musical material (`intervals` + `rhythm`) plus an `identity_floor` and optional `identity_hard_min`. A section selects one only through explicit `development.sections.<id>.motif_variant`.

The runtime does not generate, infer, or choose variants. It measures lineage against the canonical `main` motif, enforces only the authored hard minimum, and records the resulting identity evidence in resolved arrangement metadata. If no variant is authored/selected, the legacy single-motif arrangement path is preserved.


## Explicit harmonic progression variants

A Composition Brief may provide optional `materials.progression_variants`. Each variant is a complete Composer Agent-authored scale-degree path (`degrees`). A section selects one only through explicit `harmony.sections.<id>.progression_variant` (or the harmony default when intentionally shared).

The runtime does not generate, infer, optimize, or auto-select progression variants. It materializes them as song-local progression objects, validates every reference, and routes the same selected section progression to pad, bass, and arp roles so harmonic ownership cannot drift between accompaniment layers. When no progression variant is selected, historical global-progression indexing is preserved.
