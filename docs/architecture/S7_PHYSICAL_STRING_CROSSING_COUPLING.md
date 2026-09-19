# S7 — Physical String-Crossing Continuity & Coupling

S7 extends the S6 stateful bowed-waveguide path across physical violin-string changes without modifying the S5/S6 presets.

## Research basis

The design follows established bowed-instrument physical-model decomposition: bowed-string dynamics feed a bridge input/admittance stage and a radiation/body stage. Empirical violin models explicitly combine a digital-waveguide string model with bridge mechanical response and radiativity. Multi-string bowed-instrument studies likewise treat the bridge/soundbox as the mechanical interface that couples string vibration.

References consulted:

- Sterling & Bocko, *Empirical physical modeling for bowed string instruments*, ICASSP 2010 — digital waveguide + measured bridge admittance + radiation transfer.
- Michon et al., *Mobile Music, Sensors, Physical Modeling, and Digital Fabrication*, Applied Sciences 2017 — Faust violin model composition: bowed string → bridge → modal body.
- Sorge, *Vibratory Coupling Between Strings and Soundbox in Bowed Instruments*, 2023 — four-string/soundbox coupling through the bridge.

S7 implements a conservative deterministic approximation rather than claiming a measured-instrument or finite-element coupling model.

## Architecture

`bowed.violin.modeled_coupled@1.0.0` enables `continuous.string_crossing` inside `bowed_waveguide`.

- independent waveguide memories are retained for G, D, A and E as they become active;
- adjacent-string crossings use a finite bow-contact transfer from outgoing to incoming string;
- the released string continues free decay for a bounded residual window;
- residual bridge motion is summed with the incoming string before the common body/radiativity stage;
- same-string bow grouping/direction continues to come from S3/S4 violin realization;
- non-adjacent changes do not claim simultaneous physical contact when `adjacent_only=true`.

This provides bridge/body continuity at string changes while keeping the central renderer and violin planner free of sound-engine special cases.

## Compatibility

`bowed.violin.modeled_open@1.0.0` and `bowed.violin.modeled_continuous@1.0.0` are unchanged. S7 is opt-in through the new preset/configuration. Continuous double-stop physics, explicit measured bridge admittance, torsional/polarisation coupling, pizzicato and advanced bow bounce remain future work.
