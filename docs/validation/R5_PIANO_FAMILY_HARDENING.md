# R5 — Piano Family / Acoustic Hardening

Status: CLOSED

## Canonical Agent contract

The engine does not decide that a descriptive word means a particular piano.

```text
User intent
→ Composer Agent judgment
→ piano_design.family
→ family-specific categories
→ direct numeric controls
→ deterministic renderer
```

Supported families:

- `acoustic`
- `electric`

A missing `family` remains backward-compatible and means `acoustic`.

## Acoustic renderer

Current `piano_design.family=acoustic` resolves to:

```text
hammer
→ coupled stretched strings
→ bridge transfer
→ body filtering
→ track-wide modal soundboard
→ key/damper mechanics
→ stereo radiation
```

The modal soundboard replaces the previous new-design dependence on delay taps as the main body
response. Low-level diffusion taps remain subordinate.

## Electric renderer

`piano_design.family=electric` uses a separate engine:

```text
tine / reed / digital_fm excitation
→ velocity bell/bark
→ pickup filtering + saturation
→ amplifier transfer
→ tremolo / chorus
→ stereo image
→ key mechanics
```

Electric pianos are not acoustic piano graphs with a different EQ.

## Dogfood

The exact same Agent-authored two-bar phrase was compiled/rendered five times:

1. Concert Grand — acoustic
2. Upright — acoustic
3. Electric Tine — electric
4. Electric Reed — electric
5. Digital FM — electric

All five final renders report analyzer issue count `0`.

Selected same-phrase waveform correlations:

- Concert Grand ↔ Electric Tine: `-0.1394`
- Concert Grand ↔ Electric Reed: `0.0370`
- Concert Grand ↔ Digital FM: `0.0435`
- Electric Tine ↔ Electric Reed: `0.8211`
- Electric Tine ↔ Digital FM: `0.2019`

Digital FM centroid is `2007.3 Hz`;
the acoustic Concert Grand phrase is `939.0 Hz`.

The acoustic/electric distinction is therefore produced by different synthesis structures, not by
metadata labels.

## Backward compatibility

Legacy v1.14-style authored `piano_graph` isolated render:

`5428fb2deeba92a373e5a9bcb802043bf49c8e2a91b145aa6da8f4ecc3b0d8ef`

R4 == R5 byte-identical.

Representative non-piano demo WAV:

`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

R4 == R5 byte-identical.

## Regression

- pytest: 108 / 108 PASS
- Python source files: 104
- import edges: 108
- import cycles: 0
- runtime import failures: 0
