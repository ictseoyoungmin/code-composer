# S32 — Phrase Continuity / Generic Noise Safety / Endpoint Safety

Status: ENGINEERING CANDIDATE — perceptual gate open

## Observed regressions

A fresh-worker song exposed three independent base-path failures:

1. `compose_phrase()` shortened every ordinary note to `rhythm * 0.82` before E1 Phrase Expression. At 68 BPM this inserted repeated 79–318 ms gaps and then allowed E1 to shorten the already-short note again.
2. A generic bowed-description patch combined broadband breath, a saw layer and an amplifying waveshaper/output chain. The graph was structurally valid even though the result read as television static.
3. Independently rendered generic notes could end while their authored ADSR/filter output was still non-zero, creating click/static energy at note boundaries.

## Contract

- Motif rhythm owns the neutral note cell. `PhraseConfig.gate` is explicit and defaults to `1.0`.
- Short or legato base gates remain possible only when authored. E1 continues to own phrase-level gate curves and articulation multipliers.
- Generic breath is a low-level air layer, not an unrestricted broadband source. Authoring breath is capped at `0.03`.
- Breath above `0.015` may not be combined with saw gain above `0.10` and waveshaper drive above `1.0`.
- The effective breath chain (`breath * drive * output gain`, gains below unity treated as unity for risk accounting) may not exceed `0.03`.
- The same guard runs at authoring validation and direct IR validation, so a pre-resolved IR cannot bypass it.
- Independently rendered generic notes receive a minimum 2 ms endpoint declick guard. This is numerical boundary safety, not phrase articulation.

## Compatibility

- Existing material that explicitly authors `gate=0.82` retains the historical short-note behavior.
- Material that omitted a phrase gate now receives the neutral full-cell duration. This is the intended regression fix.
- Small air layers such as the v1.5 whistle design remain valid.
- This slice does not force a generic lead into the modeled bowed engine. Bowed-role routing and same-bow state continuity remain a separate evidence-gated slice.

## Closure gate

Engineering tests are necessary but not sufficient. S32 remains open until a controlled full-song A/B demonstrates that the fixed path removes syllabic chopping, broadband static, and note-end clicks without smearing intended phrase boundaries.
