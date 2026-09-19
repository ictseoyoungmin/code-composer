# v1.7 Bass Articulation

## Goal

Move bass performance beyond identical note envelopes while preserving the existing harmony and kick coupling.

## Performance states

- accent: stronger downbeat anchor, shorter attack
- short: tighter kick-coupled response
- legato: longer gate and release
- ghost: low-velocity interstitial note
- approach: short note two semitones below the next anchor with a +200 cent pitch approach

## Dogfood counts

```text
accent   34
short    32
legato   32
ghost    16
approach 31
```

## Whole-song QA

- analyzer issues: 0 -> 0
- energy correlation: 0.9889 -> 0.9886
- deterministic SHA-256: `23196c794e7e88e8790647495bd5ba013224cf06607a9b3d1fef258edaac0ca1`

Repeated render is byte-identical.
