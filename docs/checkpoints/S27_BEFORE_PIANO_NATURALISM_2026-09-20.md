# S27 checkpoint before piano naturalism reopen

Date: 2026-09-20 KST
Base: `main@2ee4d372c79b04bcc791c3ec42265438cdc576d3`

## Purpose

This checkpoint records the locally validated S27 drum-chain state before the project pivots to the larger piano-naturalism bottleneck. It is intentionally **reopenable** and must not be read as a final production-quality claim.

## Validated local baseline

- S27-B R1 resonant metal hi-hat: **user production PASS / CLOSED**
- S27-K R2 foot chick/splash coupling: **user production PASS / CLOSED**
- S27-L full-song authenticated drum-chain dogfood: engineering candidate
- Repository validation for S27-L local source: **87 test files / 589/589 PASS**
- Skill self-check / validate_skill / plugin distribution / compileall / Skill+Codex+Claude builds: PASS
- GitHub main was not overwritten during local development.

Canonical local source artifact:

- `code-composer-v1.17.0-s27l-full-song-production-engineering-candidate.zip`
- SHA-256: `c8104cbb9f3c2fdab75d682490f3fcdc495a02272ece324c1c8c870746b804f5`

Checkpoint record:

- `code-composer-s27l-full-song-production-checkpoint.txt`
- SHA-256: `e14975c347923ead588fc9fdb76596209e5c4f83fe3767db2a115c8ee8c1e57d`

## S27-M status

S27-M Ensemble / Production Integration remains **partial / reopenable**.

Implemented locally in the experiment:

- explicit `role_velocity_scales`
- explicit `targeted_onset_yields`
- kick-led onset ownership evaluated after authored S15 timing offsets
- no automatic sidechain/EQ inference
- first over-damped tuning rejected
- R1 kept drum/piano/violin levels near baseline while reducing bass attack occupancy around kick windows

Focused/maintenance gate reached **50/50 PASS**, but the full repository sweep was not completed before this checkpoint. Therefore S27-M is not promoted to a closed canonical source state here.

## Next P0: piano naturalism

Production listening indicates the larger current bottleneck is the acoustic-piano/performance chain rather than the now-stabilized hi-hat path.

### P0.1 Repeated-note excitation identity

The modeled acoustic piano can replay nearly the same internal excitation for repeated notes of the same pitch and similar length. Current phase/noise identity is too strongly tied to MIDI pitch and note length.

Desired direction:

- deterministic **per-strike** identity, not nondeterministic random humanization
- bounded hammer-contact variation
- bounded initial/unison-string phase variation
- bounded soundboard excitation variation
- damper-state-aware repeated-note behavior
- same project + seed remains reproducible

### P0.2 Chord micro-roll / hand attack

Wide voicings can currently begin on the exact same sample. A real pianist normally produces a small hand-dependent spread even when the chord is perceived as simultaneous.

Desired direction:

- explicit Composer-authored chord attack / hand roll semantics
- typical micro-spread on the order of roughly 5–18 ms when musically appropriate
- avoid turning ordinary chords into audible arpeggios
- no blanket random jitter

### P0.3 Directional phrase timing and gate variation

Repeated eighth-note figures can have perfectly equal onset intervals and identical gate lengths.

Desired direction:

- phrase-direction timing curves rather than random humanize
- bounded onset movement around roughly 5–15 ms where appropriate
- bounded gate variation around roughly 3–8%
- forward motion / resolution timing should be authored as musical intent

### P0.4 Continuous sustain-pedal semantics

This is the highest-impact engine-level piano issue identified at this checkpoint.

Current note-local `performance["pedal"] = true` semantics can allow a chord tail to continue well into the following harmony because a fixed pedal release tail is attached to each note. That is not equivalent to pianist behavior such as:

```text
pedal down
    -> pedal up at harmony change
    -> old resonance clears
    -> repedal
```

Desired direction:

- explicit continuous pedal-control events/state
- pedal down / up / repedal timeline
- damping of previously ringing notes at pedal release
- new harmony can repedal without carrying the full previous-harmony tail
- note-local pedal booleans retained only as legacy compatibility where required

### P1 Mix interaction after piano engine fix

The drum/music bus currently may produce small phrasing changes through ducking (about 1.8 dB, 8 ms attack, 150 ms release in the examined production path). This should be audited **after** the piano excitation and pedal semantics are fixed; it is not considered the primary cause of the synthetic-piano impression.

## Closure policy

Do not hide piano-engine artifacts with reverb, EQ, masking, or stronger ensemble ducking.

The next slice should first isolate piano source/performance behavior, then return to ensemble production listening.