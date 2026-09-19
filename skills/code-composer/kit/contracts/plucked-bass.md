# Plucked Bass Engine Contract

`plucked_bass` is a deterministic pitched-instrument engine for explicitly authored electric-bass notes. It is a lightweight physical/parametric string model, not a sample library and not an emulation claim for a named commercial instrument.

## Authored authority

The engine consumes existing canonical Music IR events. It does not invent bass notes, rhythms, chord roots, articulations, slides, or section structure.

The S16 factory preset is:

- `bass.electric_finger_modeled@1.0.0`

Factory preset content is sonic capability only. It contains no musical material.

## String model

Each note uses a bounded harmonic bank whose partial amplitudes are shaped by:

- pluck position along the vibrating string;
- pickup sampling position;
- partial rolloff;
- bounded stiffness-like inharmonicity;
- frequency-dependent modal damping, with upper partials decaying faster than the fundamental;
- a low-level deterministic band-limited finger transient.

The output then passes through a simple pickup/tone bandwidth stage and bounded soft saturation. Stereo width is intentionally tiny and high-passed so the low fundamental remains centered rather than becoming chorus-like.

## Existing expression compatibility

Existing bass `performance` controls remain usable:

- `pitch_start_cents`
- `pitch_end_cents`
- `pitch_time_s`
- `attack_scale`
- `release_scale`

This allows the existing deterministic approach-note and accent/short/legato/ghost realization to drive the physical bass engine without changing the composition layer.

## Explicit limits

S16 models fingerstyle single notes only. It does not claim to model:

- slap/pop collisions;
- plectrum scrape;
- fret collision/buzz;
- palm muting;
- continuous state across overlapping/legato notes;
- amplifier/cabinet/microphone emulation;
- a measured named bass or pickup.

Those require separate evidence and should not be inferred automatically.
