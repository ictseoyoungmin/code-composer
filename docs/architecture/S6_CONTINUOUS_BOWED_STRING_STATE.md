# S6 — Continuous Bowed-String State & Bow-Change Transients

S6 connects the S3/S4 violin realization plan to S5's causal bowed-waveguide sound engine across note boundaries.

## Research basis

The design follows the established view of bowed strings as excitation-continuous instruments rather than a sequence of independent note attacks. Maestre et al. model bow velocity, pressing force and bow-bridge distance as time-varying contours and drive a digital-waveguide bowed-string model with those controls. STK-style bowed models likewise retain propagation state while pitch and bow controls change. Violin bow-change studies show that bow-direction reversals and string crossings are coordinated gestures rather than independent note-on events.

References used for S6 design:

- Maestre, Blaauw, Bonada, Guaus & Pérez, *Statistical Modeling of Bowing Control Applied to Violin Sound Synthesis*, IEEE TASLP 18(4), 2010.
- Smith/STK bowed-string digital-waveguide implementation lineage; SuperCollider sc3-plugins STK wrapper demonstrates continuous `setFrequency` and bow controls while the model keeps ticking.
- Schoonderwaldt & Altenmüller, *Coordination in fast repetitive violin-bowing patterns*, PLoS ONE, 2014.
- Schoonderwaldt et al., *Auditory perception of note transitions in simulated complex bowing patterns*, JASA, 2013.

## Architecture

`BowedWaveguideEngine` now has an optional whole-track rendering path. It activates only when:

1. `bowed_waveguide_graph.continuous.enabled=true`; and
2. events already carry explicit `performance.violin_realization` evidence.

The engine keeps one waveguide state through contiguous notes on the same physical string. Stopped-pitch changes alter the waveguide delay continuously instead of creating a fresh note oscillator/waveguide. Bow groups and directions come from the violin planner. A bow reversal changes signed bow velocity through zero with a finite time constant while string state remains alive.

String changes deliberately start a new string state in S6. Short same-string gaps may decay naturally without state reset. Unsupported double-stop/polyphonic material falls back to the S5 per-note renderer rather than claiming continuous two-string physics.

## Compatibility

`bowed.violin.modeled_open@1.0.0` remains the S5 note-reset preset and is not modified. S6 adds `bowed.violin.modeled_continuous@1.0.0` as a separate factory preset. Existing generic/piano/synthetic bowed and modeled-open material therefore retains prior rendering behavior.

## Closed scope

S6 closes:

- same-string continuous waveguide state across symbolic notes;
- same-bow legato without waveguide reinitialization;
- finite bow-direction reversal through zero;
- explicit consumption of S3/S4 bow group/direction evidence by `bowed_waveguide`;
- deterministic clean-install rendering.

S6 does not close:

- simultaneous continuous state for double stops;
- physical string-crossing overlap/coordination;
- spiccato/ricochet bounce;
- pizzicato/arco switching;
- harmonic excitation/fingering;
- a claim of sampled/concert-violin realism.
