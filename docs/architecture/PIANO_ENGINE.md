# Piano Engine

`kind: piano` is a dedicated deterministic, sample-free piano path. It does not reuse the generic oscillator envelope as a piano preset.

## Signal model

1. **Coupled strings** — 1/2/3 strings by register with cent-level detuning.
2. **Stretched partial bank** — inharmonicity increases away from the middle register.
3. **Register-dependent decay** — bass partials sustain longer; treble partials decay faster.
4. **Velocity-dependent hammer** — harder strikes increase transient energy and open the hammer/body spectrum.
5. **Damper / sustain pedal** — note-off damping and pedal release are separate authored parameters.
6. **Per-note resonance** — low-level long-decay resonant modes approximate local sympathetic ringing.
7. **Track-wide soundboard coupling** — the summed piano phrase excites shared delayed stereo taps; explicit pedal events increase coupling.
8. **Keyboard stereo image** — bass is placed left, treble right, with multi-string width around that position.

The renderer never infers piano character from words such as `warm`, `bright`, or `concert`. An agent must author the actual `piano_graph` values in `sound_palette`.

## Performance surface

Each note event may provide:

```json
{"performance": {"pedal": true, "release_scale": 1.0}}
```

`pedal` controls damper release and track-wide soundboard coupling. `release_scale` scales the authored release time without changing the instrument design.

## Boundaries

This is an algorithmic piano model, not a sampled Steinway/Yamaha emulation. Its purpose is deterministic in-engine piano performance with meaningful dynamics and resonance. A future sample/SFZ backend can coexist behind the same Music IR contract without replacing this engine.
