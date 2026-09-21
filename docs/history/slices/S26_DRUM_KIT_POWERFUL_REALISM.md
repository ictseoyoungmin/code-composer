# S26 — Drum Kit Powerful Realism / Performance & Room Integration

Status: **ENGINEERING CANDIDATE — PERCEPTUAL GATE OPEN**

## Reopen reason

The S19 core and R5 ride/crash recovery removed the largest source-level regressions,
but actual 4–12 bar drum performances still lacked the physical authority of one drummer
playing one kit in one room. Further cymbal-only tuning would not address that bottleneck.

## Preservation boundary

S26 starts from `drums.s19_core_cymbal_extension@1.0.0` and does not change its
`kick`, `snare`, `hat`, `ride`, `crash`, or `cymbal_extension` blocks. The new
factory preset is `drums.s19_core_powerful_room@1.0.0` and adds only
`drum_graph.kit_integration` plus a percussion-engine track post-process.

## Research-derived architecture

- Direct/close path remains the transient and timing anchor.
- Near-coincident overhead path adds band-limited shared kit energy and short deterministic reflections.
- Early room reflections use a compact image-style delay/attenuation layout.
- Late room uses a four-line normalized Hadamard feedback delay network with feedback gain derived from target RT60 and frequency-dependent damping.
- Authored drum-event velocity drives a bounded room-send envelope; quiet timekeeping does not excite the room like a hard snare/crash accent.
- Zero-delay low/body parallel path restores close kick/snare weight without extending source decay.
- Ambient and full-kit parallel compressors are feed-forward and attack/release smoothed so initial dry transients are not simply flattened.

See `CREDITS.md` for research and open-source provenance.

## First bottleneck dogfood

One 4-bar 118 BPM rock/pop performance at 24 kHz:

1. bar 1 — crash/kick downbeat, closed-hat pocket;
2. bar 2 — closed-hat dynamic lift;
3. bar 3 — crash replaces ride on the section downbeat, ride resumes on the next eighth;
4. bar 4 — stronger ride bar, final crash/kick punctuation with no simultaneous ride.

Timing and velocity are explicitly authored. S26 does not generate the pattern.

## Objective evidence from the current candidate

RMS-matched S26 versus the exact R5 dry source on the same event/seed render:

- overall 2–6 kHz energy ratio: `0.0655 -> 0.1056`;
- overall 6–11 kHz energy ratio: `0.0320 -> 0.0488`;
- first backbeat snare 0–20 ms RMS: `0.2017 -> 0.2455` (~+21.7%);
- first backbeat snare 30–160 ms RMS: `0.0943 -> 0.1159` (~+22.9%);
- initial kick 0–20 ms RMS: `0.4518 -> 0.4402` (~-2.6%);
- initial kick 30–120 ms RMS: `0.2839 -> 0.2760` (~-2.8%);
- final crash 350–900 ms RMS: `0.0520 -> 0.0672` (~+29.4%);
- integrated/raw groove RMS is within ~1% of the dry groove before any A/B matching.

These metrics are directional evidence only. Closure requires listening confirmation that
the integrated render feels more like a powerful real kit rather than merely brighter or wetter.

## Closure gate

S26 may close only if:

- the dry close-core identity remains recognizable;
- kick impact is not materially weakened;
- snare/crash accents gain physical authority in musical context;
- the kit sounds spatially coherent rather than like separate reverb inserts;
- the rejected long tonal cymbal ringing does not return;
- focused regression and packaging validation pass;
- user listening accepts the actual-performance A/B.
