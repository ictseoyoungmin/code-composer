# S8 — Bridge Admittance & Body Feedback Hardening

## Goal

S7 already retains G/D/A/E waveguide memories through string changes, but its body stage is downstream: bridge motion is filtered into radiation and does not load the string again. S8 adds a narrow causal feedback path without changing older presets.

## Research basis

Empirical bowed-string physical-model work separates three coupled pieces: bowed-string dynamics, driving-point bridge admittance, and body/radiation transfer. Sterling & Bocko describe combining measured bridge mechanical admittance and radiativity with a digital-waveguide bowed string. Maestre, Scavone & Smith later describe joint efficient modeling of bridge admittance and body radiativity for digital-waveguide string synthesis. Faust's physical-model library likewise exposes violin bow, bowed-string, bridge, and body blocks as distinct bidirectional components.

References:
- Sterling & Bocko, *Empirical physical modeling for bowed string instruments*, ICASSP 2010, DOI 10.1109/ICASSP.2010.5495754.
- Maestre, Scavone & Smith, *Joint Modeling of Bridge Admittance and Body Radiativity for Efficient Synthesis of String Instrument Sound by Digital Waveguides*, IEEE/ACM TASLP 2017, DOI 10.1109/TASLP.2017.2689241.
- Faust Physical Modeling Library: https://faustlibraries.grame.fr/libs/physmodels/

## S8 model

For `bowed.violin.modeled_admittance` only:

1. S7's multi-string waveguides generate summed bridge motion.
2. A causal modal body bank advances once per sample.
3. The same mode state produces two taps:
   - radiation: modal radiation gains + direct high-passed bridge path;
   - admittance: independent signed modal weights.
4. The admittance sum is scaled by a small `feedback_gain`, hard-limited by `max_feedback_velocity`, and applied one sample later to the bridge reflection of the physical strings.
5. Older S5/S6/S7 presets have no enabled feedback object and retain their previous numerical path.

This is a compact deterministic approximation. It does not claim measured impulse-response fitting, a named violin, or a finite-element soundbox.

## Stability policy

Factory `feedback_gain` is deliberately weak (`0.006`). Authoring validation caps the gain at `0.03` and the returned body velocity at `0.20` absolute maximum. The factory preset uses a tighter `max_feedback_velocity=0.012`. These limits prevent body feedback from becoming an uncontrolled resonant effect.

## Non-goals

S8 does not add melody, fingering rules, double-stop continuity, harmonics, pizzicato, ricochet/spiccato bounce, measured body fitting, or automatic acoustic-quality claims.
