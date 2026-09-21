# S27-C — Snare Articulation Authenticity

Status: ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN
Date: 2026-09-20
Baseline: S19 legacy snare preserved + S27-B two-cymbal hi-hat CLOSED

## Problem

The canonical `snare` is a strong early Code Composer voice, but it is one articulation. A real snare changes causally with strike position and contact technique: normal head strokes excite the batter/resonant heads and wires, rimshots strike head and rim together, cross-stick is primarily a rim/shell wooden knock, and ghost notes are genuinely quiet strokes rather than normal hits scaled after synthesis.

## Research anchors

- E. K. Ellington Scott and Andrew Morrison, “The Acoustics of the Modern Jazz Drum Kit,” *Acoustics Today* 18(4), 31–41, 2022, DOI `10.1121/AT.2022.18.4.31`: snare = batter head + resonant/snare head + contacting wires; wires are central to the crisp staccato identity.
- Ewa Skrodzka, E. Hojan, and R. Proksza, “Vibroacoustic investigation of a batter head of a snare drum,” *Archives of Acoustics* 31(3), 289–297, 2006: central excitation strongly favors the lowest radiating mode, while non-central excitation changes the observed spectral peaks; other drum elements materially affect the perceived sound.
- Randy Worland and Benjamin Boe, coupled-drumhead vibration measurements, JASA 2013, DOI `10.1121/1.4831235`: the two heads are coupled through enclosed air/shell motion.
- Yamaha/Roland technique documentation is used only to confirm performance semantics: rimshot = head+rim contact; cross-stick/side-stick = rim-focused technique with the stick resting across/muting the head.

No publication source code, measured modal table, sample, recording, mesh, or proprietary instrument asset is copied. The model is independently implemented as a compact deterministic approximation.

## Preservation rule

- Existing `snare` rendering remains byte-compatible and is not rerouted.
- S19 kick/legacy snare/legacy closed-hat remain preservation anchors.
- S27-A2 ride/crash and S27-B hi-hat blocks remain unchanged in the new preset.
- New behavior is explicit opt-in through authored articulation names.

## New articulation surface

- `snare_center` — normal backbeat/head stroke.
- `snare_ghost` — quiet head stroke with audible but bounded wire response.
- `snare_rimshot` — simultaneous head + rim excitation; stronger, brighter attack.
- `snare_cross_stick` — dry woody rim/shell knock with minimal membrane/wire drive.

MIDI export keeps center/ghost/rimshot on acoustic-snare note 38 and uses GM side-stick note 37 for cross-stick. The richer authored articulation remains in the Code Composer IR.

## Compact causal model

`stick force -> batter-head modes -> delayed coupled resonant head -> snare-wire response`

with an additional rim/shell path when the technique requires it.

- Strike position changes modal weighting instead of changing only EQ.
- Snare-wire noise is amplitude-shaped by resonant-head motion, not added as an unrelated stationary noise layer.
- Rimshot combines the head path and a strong short hoop/shell contact path at the same time origin.
- Cross-stick heavily suppresses heads/wires and emphasizes short low/mid rim-shell modes plus wooden contact.

## First-candidate tuning

At 24 kHz, seed 17:

- S19 legacy snare at velocity 0.86: RMS ~0.0821, first 20 ms ~0.1682.
- S27-C center at velocity 0.86: RMS ~0.0989, first 20 ms ~0.1950.
- S27-C ghost at velocity 0.34: RMS ~0.0227, first 20 ms ~0.0465.
- S27-C rimshot at velocity 0.86 after bright-crack retune: onset is intentionally stronger than center while retaining membrane body.
- S27-C cross-stick is centered in the low/mid woody rim region and has far less late wire/head energy than center.

The rimshot was retuned before dogfood because an earlier candidate let low rim modes dominate too much; the accepted engineering candidate shifts more of the simultaneous contact energy into the short hoop/wood crack while keeping the head path active.

## Closure gate

1. `snare_center` must retain the approved S19 backbeat authority.
2. `snare_ghost` must read as a real quiet stroke, not simply a full snare hit normalized later.
3. `snare_rimshot` must sound like head + rim at one instant: louder/sharper, but still unmistakably a snare rather than a wood block.
4. `snare_cross_stick` must sound dry/woody and rim-led, with minimal wire/body tail.
5. Position/articulation differences must remain deterministic and seed-sensitive without randomizing authored timing.
6. Actual 2/4 backbeat + ghost-note groove is the primary listening gate; isolated hits are diagnostics.
7. Existing S19 core and S27-B/Cymbal surfaces must remain exact-preserved.

## Deferred

- continuous snare-strainer tension/off state,
- brush sweep,
- positional continuum beyond the explicit center/ghost/rim techniques,
- stick-hand limb occupancy (S27-F).
