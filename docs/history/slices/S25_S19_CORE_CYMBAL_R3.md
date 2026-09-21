# S25 — S19 Core Cymbal Extension R3

Status: **CLOSURE CANDIDATE — perceptual gate open**

## Preservation anchor

The user-selected `code-composer-v1.17.0-s19-track-pan-stereo-integrity-repository` is the canonical pre-S20 drum checkpoint. R3 preserves S19 kick, snare, and closed hi-hat behavior byte-identically. It does not import later non-cymbal coupled-head/cavity hardening into this path.

## R2 defect closure

R2 addressed the long tonal ringing heard during the bar-5 crash + repeated ride entrance by shortening sparse ride/crash low/mid modal decay. The artifact was treated as a defect, not as intended cymbal sustain.

## R3 musical-context polish

R3 changes **ride voicing only** relative to R2:

- `plate_gain`: `0.55 -> 0.62`
- `contact_gain`: `0.14 -> 0.16`
- `wash_gain`: `0.12 -> 0.09`
- `output_gain`: `0.44 -> 0.47`
- ride decay/tail are unchanged from R2 (`0.72 s` modal decay, `1.35 s` event tail)
- crash parameters are unchanged from R2

Matched-groove evidence at 24 kHz shows cymbal 2–6 kHz energy fraction moving from about `0.422` to `0.446`, while 6–11.5 kHz moves from about `0.283` to `0.212`. At equal bar-5 attack level, the 1.5–2.0 s tail/onset ratio is essentially unchanged (`0.552` R2 vs `0.555` R3), so the R2 long-tail fix is not reopened.

## Verification

- focused regression: **64 / 64 PASS**
- standalone skill self-check: **PASS**
- skill validation: **PASS**
- compileall: **PASS**
- standalone Skill/Codex/Claude plugin builds: **PASS**
- full pytest: execution limit at about 15%; no failures observed before timeout
- original S19 vs R3 function-body SHA-256: `_legacy_kick`, `_legacy_snare`, `_legacy_hat`, `_modeled_kick`, `_modeled_snare`, `_modeled_hat` all identical

Do not mark S25 cymbal work CLOSED until the R2 -> R3 musical-context audition passes perceptual review.
