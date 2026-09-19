# R5R1 — Piano Fidelity Correction

Status: CLOSED

## Why R5 was reopened

The first R5 piano-family listening files were not a valid fidelity reference:

1. They were rendered at 22.05 kHz.
2. The dogfood reused a song-oriented lead mix graph containing delay, bus compression,
   reverb sends and master processing.
3. The new electric-piano renderer did not explicitly suppress high-register aliasing
   produced by tine/reed upper partials and nonlinear pickup/amp/FM stages.

The WAV files did not exhibit digital sample clipping, but those three factors could make
the result sound brittle, smeared or "broken".

## Corrections

### QA rate

All canonical piano listening QA is now 44.1 kHz minimum.

### Electric anti-aliasing

- explicit tine/reed harmonics above the internal Nyquist guard are omitted
- electric rendering uses deterministic internal oversampling:
  - output <= 24 kHz: 4x internal rate
  - output <= 48 kHz: 2x internal rate
  - above 48 kHz: native rate
- nonlinear pickup/amp/FM generation happens at the internal rate
- final output uses deterministic `scipy.signal.resample_poly` low-pass/downsampling

A regression compares a high-register render at 22.05 kHz against a 44.1 kHz
reference downsample and requires strong waveform correlation.

### Clean piano QA chain

The corrected family dogfood routes the piano lead through one clean bus:

`piano -> clean group -> master`

No delay, reverb, compressor, sidechain or limiter is present in the timbre-QA mix.

## Regression

- full pytest: 110 / 110 PASS
- import regressions from R5 remain unaffected
- all corrected family phrase renders: analyzer issue count 0
- user-facing QA WAVs: 44.1 kHz stereo
- legacy acoustic `piano_graph` behavior is unchanged by the electric anti-alias patch

## Listening order

`piano_family_5way_clean_44k1.wav`

1. Concert Grand
2. Upright
3. Electric Tine
4. Electric Reed
5. Digital FM

A/B files are old R5 first, then R5R1.
