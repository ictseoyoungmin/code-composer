# PR81: treble ringing follow-up

The user heard an improvement from the per-string decay bug fix, but sustained electronic-sounding ringing remained. This follow-up intentionally changes acoustic three-string treble synthesis; it is not merely another unused control or an EQ cut.

## Model

Each partial now uses a passive complex-amplitude system in a common rotating frame:

`dz/dt = (diag(-1/tau + j*delta_omega) - g*ones(N,N)/N) z`.

The Hermitian part is negative definite for positive intrinsic lifetimes and nonnegative coupling. Consequently total modal energy cannot grow. The common radiating mode loses energy to the bridge; differential modes can persist more quietly. The authored string count, intrinsic lifetimes, detuning, phase identity, velocity, stereo placement, note duration and pedal-release envelopes are retained. Coupling fades in smoothly from MIDI 60 to 84 and is applied only to three-string notes. Its coefficient is a sound-model calibration, not an identification of a real instrument's impedance. This remains a reduced model: it does not implement track-wide acoustic-string energy exchange or a full bidirectional soundboard.

Treble reinforcement also follows stretched-string frequencies and frequency-dependent source decay plus radiation loss, instead of leaving an exactly harmonic oscillator bank with a common long lifetime. Existing low-register and single/two-string sample paths are retained. No preset, authored note, timeline, electric piano or mixer settings are rewritten.

## Evidence and scope

Baseline: PR81 head `25da01655889689370a730a096bd9a55365c15c5` (the first fix, not the original defect).

Ablation on the previously supplied diagnostic graph found that muting per-note resonance alone barely changed late RMS; independent unison oscillators dominated. A passive coupled model reduced the late high-frequency tail without a hard time gate or removing detuning.

At 48 kHz, velocity 0.75, note-local pedal, 2.5-second held C5/E5/C6/E6, shared output gain, the 2.5-kHz high-pass RMS over seconds 1.0-2.5 changed by -8.04/-11.09/-14.38/-16.30 dB versus the previous fix. First-50-ms RMS changed by -0.29/-0.48/-0.79/-0.87 dB. Attack-relative high-band reductions were -7.75/-10.61/-13.60/-15.44 dB, so the result is not explained by turning the whole track down.

These are diagnostic measurements, not a listening approval or a reconstruction of the user's composition. No assertion is made that all subjective ringing has disappeared. A full acoustic render was roughly twice as expensive in this local four-note probe; the exact source functions were used in a dependency-scoped offline harness, not a full installed package. Full repository CI is checked separately on this PR.

New tests compare the modal solver against an independent matrix exponential, enforce energy passivity, exercise ill-conditioned fallback, check attack/tail tradeoffs at 24/48 kHz, preserve input/deterministic/pedal behavior, and test source-bounded resonance. Existing per-string decay regressions remain. Preview epoch 3 invalidates both earlier stem generations.

Physical rationale: Julius O. Smith, Physical Audio Signal Processing, Coupled Strings: https://www.dsprelated.com/freebooks/pasp/Coupled_Strings.html . A simple sum of detuned strings produces beating but is not itself a model of coupled two-stage decay. This implementation is original reduced-model code, not copied from that text.
