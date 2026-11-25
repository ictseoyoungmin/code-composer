# Balanced grand: opt-in treble refinement

This change separates the verified legacy unison-envelope fix from an optional
voicing. The existing Natural preset and default piano routing stay as they
were. Select `piano.concert_grand_balanced@1.0.0` to audition the new voicing.
No sample library or replacement music ships with this change.

- Legacy release now multiplies each string's own decay envelope by the damper,
  rather than overwriting it with the shared envelope. Existing explicit pedal
  behavior is unchanged. Old preview stems are invalidated.
- The Balanced source gradually adds radiation loss to higher partials of
  three-string notes above middle C. The first two struck partials and the
  hammer impulse are not attenuated by this mechanism. Zero is inert.
- Upper harmonic reinforcement follows the center string's stretched
  frequencies and cannot retain a longer exponential decay than that mode.
  This avoids a separate higher pitched tail under sustain. Lower reinforcement
  and the shared soundboard remain on their original path.
- Compared with the earlier audition's more aggressive onset damping, the new
  onset ramp retains more early upper-mode energy. The preset also leaves more
  output headroom. These changes are inside the source; no master EQ or
  compressor is used.

Illustrative E5 pedal-down probe, 48 kHz, velocity 0.86, dry per-note path.
Band RMS (2.1–6.5 kHz) relative to first 50 ms, common render headroom:

| Model | 80–160 ms | 350–550 ms |
| --- | ---: | ---: |
| Released Natural | -14.9 dB | -18.9 dB |
| Earlier preview | -20.4 dB | -39.8 dB |
| Balanced | -18.3 dB | -41.7 dB |

E5 fundamentals matched rounded to 0.01 dB in the 140–280 ms window; full-band
attack difference versus Natural was under 0.1 dB in this probe. This is a
reduced model and targeted listening candidate, not a match to a named
instrument; validation does not replace listener approval. The E5 numbers do
not predict every register. A same-score audition uses whole-take static
loudness matching and verifies that neither internal peak cap is engaged.
