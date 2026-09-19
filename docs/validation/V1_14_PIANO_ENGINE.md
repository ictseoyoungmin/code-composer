# v1.14 Piano Engine Dogfood

An original D-major benchmark was used; it is not a transcription of an existing composition.

## Isolated QA

- C4 spectral centroid by velocity: 619.9 -> 782.6 -> 992.1 Hz
- C4 onset crest by velocity: 2.42 -> 2.86 -> 3.44
- Register stereo balance MIDI 40 / 60 / 80: -0.354 / 0.000 / 0.348
- Register centroid MIDI 40 / 60 / 80: 382.6 / 863.6 / 1994.1 Hz
- Pedal late-tail RMS: 0.0850 -> 0.1502
- Low/mid/high late-to-onset decay ratio: 0.780 / 0.566 / 0.171

## Full benchmark

- analyzer issues: 0
- energy correlation: 1.0000
- clipped sample ratio: 0.000000
- SHA-256: `2adba5ffeeb7c8c0b217b7303a1f672dfc53edc6a8cbd87a14c6c591d7eee5f5`
- repeated render byte-identical: `True`

## Regression

- piano tests: 8 / 8 PASS
- full pytest: 58 / 58 PASS
- import failures: 0
