# v1.5 Timbre Architecture

## Whistle / pluck graph

```text
Pitched oscillators
  + small pitch approach
  + tonal attack partial
  + band-limited breath
        ↓
      ADSR
        ↓
  band-pass / tone shaping
        ↓
   soft waveshaping
        ↓
      declick
        ↓
      output
```

## Design constraints

1. Breath is band-limited and low-gain. It must read as air, not static.
2. Pluck definition uses a decaying harmonic partial rather than a broadband impulse.
3. Pitch approach is small and short; vibrato remains independent.
4. Note edges are explicitly smoothed.
5. All behavior is serializable Music IR / instrument graph data.
6. Identical input graphs produce byte-identical note renders.

## QA metrics

- onset click score
- >7 kHz energy ratio
- spectral flatness
- low-harmonic concentration
- full-song section analysis

The metrics are evidence, not automatic aesthetic truth. The final patch is intentionally
kept below the point where added air turns into broadband hiss.
