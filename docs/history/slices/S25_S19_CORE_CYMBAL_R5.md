# S25 — S19 Core Cymbal Extension R5

Status: **ENGINEERING CANDIDATE — drummer-performance perceptual gate open**

## Why R5 exists

R4 recovered useful 2–6 kHz presence and kept the long tonal smear under control, but ride and crash still felt under-struck when judged as parts of a real drum performance. R5 therefore changes the evaluation target from "does the isolated cymbal sound plausible?" to "does authored drummer-like velocity produce believable timekeeping and accents inside a groove?"

## Preservation anchor

- Pre-S20 S19 repository remains the drum-core checkpoint.
- Legacy kick, snare and closed hi-hat remain locked.
- R2/R4 ride and crash decay constants and event-tail lengths remain unchanged.
- R5 does not introduce a compressor, limiter, reverb, or master normalization into the engine.

## R5 performance model

### Ride

Authored velocity changes excitation balance as well as amplitude:

- soft timekeeping keeps the short stick-contact component subdued;
- medium hits retain the R4 plate/presence balance;
- strong accents bring the contact transient forward disproportionately;
- plate and wash sustain do not lengthen with stronger hits.

### Crash

Strong section accents gain authority through excitation rather than sustain:

- low/low-mid impact remains present at the initial strike;
- contact is intentionally band-limited so the full bright field is not exposed at t=0;
- mid/high modal bloom still arrives after the initial impact;
- strong velocity opens contact, bloom and shimmer more than soft velocity;
- decay/tail remains bounded at the R2/R4 values.

## Drummer-like dogfood context

The external 24 kHz validation performance uses a deterministic 12-bar arrangement:

- bars 1–4: closed-hi-hat pocket;
- bars 5–8: transition to ride timekeeping;
- bars 9–12: stronger ride chorus context;
- section-entry crash replaces the timekeeping cymbal on the downbeat and ride resumes on the following subdivision rather than stacking crash and ride at the same instant;
- snare is slightly behind the grid and cymbal subdivisions carry authored accent hierarchy.

This dogfood is evidence only. The engine does not invent musical hits or performance patterns.

## Engineering gates

At 24 kHz with the canonical preset and seed 17:

- ride v=1.0 / v=.45 first-30-ms RMS ratio > 2.70;
- crash v=1.0 / v=.45 first-30-ms RMS ratio > 2.80;
- soft ride onset remains < .030 RMS;
- soft crash onset remains < .023 RMS;
- ride late/onset ratio remains < .24 at strong velocity;
- crash late/onset ratio remains < .48 at strong velocity;
- crash retains delayed high-frequency bloom and low-first onset.

Final acceptance remains listening in the authored performance context, not metric closure alone.

## Validation state

- Focused S17/S18/S19/S25 + factory/engine/MIDI regression: **66/66 PASS**.
- `skills/code-composer/kit/scripts/self_check.py`: PASS.
- `tools/validate_skill.py`: PASS.
- `python -m compileall -q skills/code-composer/kit/src`: PASS.
- standalone Skill/Codex/Claude plugin builds: PASS.
- full pytest was attempted and reached roughly 15% with no failure before the execution timeout; this is not recorded as a full-suite pass.
- Original S19 `_legacy_kick`, `_legacy_snare`, `_legacy_hat`, `_modeled_kick`, `_modeled_snare`, and `_modeled_hat` function-body SHA-256 hashes all match the R5 workspace exactly.
