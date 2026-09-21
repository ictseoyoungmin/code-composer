# S27-A Cymbal Strike Mechanics — coherent stick-to-plate excitation

Status: ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN  
Date: 2026-09-20  
Baseline: S19 dry core + R5 cymbal tail/presence recovery + S26 optional kit integration

## Bottleneck

The user-visible failure was not primarily cymbal decay. Ride and crash sounded as if a stick was placed against the metal instead of striking it. The previous source path used short band-limited stochastic contact plus plate banks whose modes started at independent random phases. That can create metallic energy, but it does not represent one mechanical impact coherently exciting one plate.

S27-A opens only the first tens of milliseconds of ride/crash excitation. It does not reopen the preserved S19 kick/snare/closed-hi-hat core, and it does not lengthen the approved R2/R3 cymbal tails.

## Causal model

```text
player gesture / authored velocity
        ↓
short stick contact force pulse
        ↓
contact radiation + coherent plate-mode excitation
        ↓
ride bow body OR crash low/mid/high plate field
        ↓
existing delayed metallic bloom
        ↓
existing bounded tail
        ↓
optional S26 shared overhead / room / bus layer
```

The production implementation is an engineering approximation, not a finite-element cymbal simulator. Research establishes causal targets; Code Composer independently implements a compact deterministic model suitable for real-time/offline composition rendering.

## Implementation

### 1. Velocity-dependent stick force pulse

`_impact_force_pulse()` creates a bounded short contact pulse. Higher authored velocity shortens contact duration and changes the force shape instead of acting as gain alone.

Current S27-A preset ranges:

- ride: about 1.8 ms soft → 0.85 ms hard;
- crash: about 2.4 ms soft → 1.15 ms hard.

This is intentionally far shorter than cymbal decay. Strike mechanics and resonator decay remain separate controls.

### 2. Coherent modal excitation

`_coherent_plate_bank()` uses one impact event to excite all selected plate modes. Modal weights may differ and seeded variation is retained, but modes no longer begin at arbitrary independent time phases in the S27-A strike path.

### 3. Acoustic output uses a velocity/radiation-like response

An initial S27-A experiment drove the coherent modal bank with a displacement-like sine response. That caused each mode to start from zero displacement and, at the chosen output boundary, also made the audible onset too weak:

- ride first-5-ms RMS fell to roughly 0.021 from about 0.076 in the prior path;
- crash first-5-ms RMS fell to roughly 0.023 from about 0.050.

That experiment was rejected.

The retained implementation uses a cosine/velocity-like damped modal response as a compact proxy for surface velocity / radiated-pressure behavior. The intent is not that cymbal displacement is maximal at impact; the intent is that the acoustic radiation proxy must not be forced to zero simply because structural displacement begins at zero.

### 4. Contact radiation is not a noise burst

`_stick_contact_radiation()` derives the short contact component from the impact force and its slope. Seeded stochasticity may still exist elsewhere in the cymbal sound field, but broadband white noise is no longer the primary representation of stick contact in `physical_v1`.

### 5. Tail and bloom remain bounded

S27-A deliberately preserves the short-tail recovery achieved before this slice:

- ride event tail: 1.35 s;
- crash event tail: 1.65 s;
- ride principal plate decay: 0.72 s;
- crash low/mid/high plate decay remains within the R5/S26 contract.

The strike may become more authoritative without solving power by extending sustain.

## Current 24 kHz evidence

Matched direct-hit measurements for the selected engineering candidate:

| Event | Metric | R5/S26 source | S27-A |
| --- | ---: | ---: | ---: |
| ride v=.82 | RMS, 0–5 ms | 0.06840 | 0.07404 |
| ride v=.82 | RMS, 20–80 ms | 0.05160 | 0.03910 |
| ride v=.82 | RMS, 0.8–1.2 s | 0.00977 | 0.00781 |
| crash v=.98 | RMS, 0–5 ms | 0.06793 | 0.09044 |
| crash v=.98 | RMS, 20–80 ms | 0.07565 | 0.06618 |
| crash v=.98 | RMS, 0.8–1.2 s | 0.03079 | 0.02581 |

The desired movement is visible: energy moves toward the actual strike while late energy does not increase.

At 125 BPM, the actual-performance dogfood keeps crash as an accent substitution rather than automatically stacking it on the same downbeat as the ride timekeeping hit. This separates sound-source authenticity from impossible/unnatural performance orchestration.

## Guardrails

S27-A must satisfy all of the following before closure:

1. S19 kick/snare/closed-hi-hat remain byte-identical under the new preset.
2. Existing R5/S26 presets remain behaviorally unchanged; `physical_v1` is opt-in.
3. Ride repeated at musical tempo has an individually readable stick attack, not a continuous wash.
4. Strong crash produces `impact → plate/bloom`, not `noise wash → long tone`.
5. 0.8–1.2 s tail energy may not regress above the previous approved path in focused tests.
6. Authored velocity changes onset/body relationship, not only output amplitude.
7. S26 room is evaluated only after the dry source passes; room may enhance a correct strike but may not manufacture one.

## What S27-A does not solve

This slice intentionally does not add:

- ride bell articulation;
- continuous hi-hat openness / pedal collision;
- snare ghost/rimshot/cross-stick geometry;
- high/mid/floor tom family;
- drummer limb scheduling in Music IR;
- nonlinear finite-element cymbal simulation.

Those remain later S27 slices. Historical S20–S24 articulation names are useful semantic evidence, but their later sound model is not restored wholesale.

## Research basis

The design is informed by, but not copied from:

- Sofia Dahl, percussion striking-movement research;
- Dahl & Altenmüller, movement/contact-force/sound-characteristic research;
- Kaselouris et al., motion-driven cymbal–drumstick FEM/BEM simulation;
- Nguyen & Touzé plus Ducceschi & Touzé, nonlinear impacted plate/cymbal modeling;
- Avanzini & Marogna and related coupled percussion research for later membrane slices.

Detailed citations and licensing/reimplementation policy are recorded in `CREDITS.md` and `S27_DRUM_AUTHENTICITY_RESEARCH.md`.
