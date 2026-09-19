# Sound Palette Contract — v1.13

The Composer Agent authors the actual synthesis design in `CompositionBrief.sound_palette`.
Code Composer does **not** map adjectives, genres, or style vocabulary to timbres.

Pipeline:

`Prompt -> Agent musical judgment -> Composition Brief.sound_palette -> validator/compiler -> instrument patch graph -> deterministic DSP`

Each palette role may contain human-readable `character` / `rationale` metadata, but those
strings are never interpreted by the compiler. Only the explicit patch graph affects audio.

Pitched roles may author oscillators, unison, ADSR, filter, LFO, pitch approach, breath,
tonal attack partial, waveshaper, declick and output gain. Drums author the existing
kick/snare/hat procedural graph directly.

The validator bounds the supported DSP surface so an agent cannot silently invent an
unsupported oscillator/filter/effect or extreme unsafe parameter values.
