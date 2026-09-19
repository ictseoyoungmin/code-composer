# Code Composer

> Current percussion closure: **S24 Cymbal Presence & Excitation Hardening — CLOSED**. `drums.acoustic_kit_modeled_cymbal_presence@1.0.0` strengthens metallic cymbal body/presence while reducing independent static-like wash; S23 remains unchanged.

Code Composer is a deterministic music composition/rendering engine packaged as a self-contained agent skill.

## Repository layout

- `skills/code-composer/` — **canonical installable skill**. It is self-contained and must never reference repository-parent files.
- `.codex_plugins/` — Codex plugin adapter source; release tooling injects the canonical skill into an installable plugin artifact.
- `.claude_plugins/` — Claude plugin adapter source; release tooling injects the canonical skill into an installable plugin artifact.
- `docs/` — maintainer architecture, validation, maintenance history and design decisions.
- `examples/` — maintainer-only regression/showcase/integration material. **Not shipped in the agent skill.**
- `tests/` — repository regression and packaging tests.
- `tools/` — build/validation/release helpers.
- `CREDITS.md` — research acknowledgements, external-reference provenance, and third-party attribution policy.

## Agent-facing boundary

Normal agents start at `skills/code-composer/SKILL.md`, then use the progressive-disclosure graph under `kit/`. They should not inspect `kit/src/` unless a source-level exception applies.

The installed skill follows the policy: **Examples teach operation, never taste.** Completed songs, polished MIDI/WAV, dogfood compositions and showcase material remain outside `skills/code-composer/`.

## Development

```bash
PYTHONPATH=skills/code-composer/kit/src pytest -q
python skills/code-composer/kit/scripts/self_check.py
python tools/validate_skill.py
```

Build standalone artifacts with:

```bash
python tools/build_skill.py
python tools/build_plugins.py
```

Current music-engine feature baseline: v1.17.0 (M1 MIDI export, M2 `.ccx` exchange, M3 external delivery, S1 instrument-engine extensibility, S2 factory preset system, S3 violin performance model, S4 violin double-stop realization, S5 bowed-string sound hardening, S6 continuous bowed-string state/bow-change transients, S7 physical string-crossing continuity/coupling, S8 bridge admittance & body feedback hardening, S9 measured bridge-admittance ERA fitting, S10 violin performance-to-timbre expression hardening, S11 expressive phrase modeling, S12 violin realism hardening, S13 articulation expansion, S14 acoustic-piano release/resonance hardening, S15 ensemble/orchestration realism, S16 modeled bass acoustic fidelity, S17 modeled percussion acoustic fidelity, S18 predictable track-gain semantics, S19 stereo-preserving track-pan semantics, S20 drum articulation foundation, S21 drum acoustic-core realism hardening, S22 drum acoustic voicing & timbre polish, S23 drum performance-to-timbre dynamics, S24 cymbal presence & excitation hardening).

Repository packaging closure: **S0R1 Canonical Skill Hygiene — CLOSED**. Instrument architecture closure: **S1 Instrument Engine Extensibility — CLOSED**. Factory sound-resource closure: **S2 Factory Preset System — CLOSED**. Violin physical-realization closure: **S3 Violin Performance Model — CLOSED**. Double-stop realization closure: **S4 Violin Double-Stop Realization — CLOSED**. Bowed-string sound closure: **S5 Bowed-String Sound Hardening — CLOSED**. Continuous bowed-state closure: **S6 Continuous Bowed-String State & Bow-Change Transients — CLOSED**. String-crossing coupling closure: **S7 Physical String-Crossing Continuity & Coupling — CLOSED**. Bridge/body feedback closure: **S8 Bridge Admittance & Body Feedback Hardening — CLOSED**. Measured-response fitting closure: **S9 Measured Bridge-Admittance ERA Fitting — CLOSED**. Performance-to-timbre expression closure: **S10 Violin Performance-to-Timbre Expression Hardening — CLOSED**. Phrase-level expression closure: **S11 Expressive Phrase Modeling — CLOSED**. Player-mechanics realism closure: **S12 Violin Realism Hardening — CLOSED**. Articulation closure: **S13 Articulation Expansion — CLOSED**. Acoustic-piano release closure: **S14 Acoustic Piano Release & Resonance Hardening — CLOSED**. Ensemble interaction closure: **S15 Ensemble / Orchestration Realism — CLOSED**. Mixer predictability closures: **S18 Track Gain Semantics — CLOSED**, **S19 Track Pan / Stereo Integrity — CLOSED**. Percussion articulation closure: **S20 Drum Articulation Foundation — CLOSED**. Drum dry-source acoustic-core closure: **S21 Drum Acoustic Core Realism Hardening — CLOSED**. Drum dry-source voicing closure: **S22 Drum Acoustic Voicing & Timbre Polish — CLOSED**. Drum performance-to-timbre closure: **S23 Drum Performance-to-Timbre Dynamics — CLOSED**. Cymbal presence/excitation closure: **S24 Cymbal Presence & Excitation Hardening — CLOSED**. The next planned slice is **S25 Non-Cymbal Drum Core Hardening** (kick → snare → tom), and Stateful Kit Interaction remains deferred until dry-source hardening is complete. The canonical skill contains one implementation tree (`kit/src`) and no persisted build output.


### Factory presets

S2 adds a small versioned factory preset catalog. Presets are sonic resources only; composition content remains agent-authored from the user brief/current song. The installed Skill exposes capability metadata through `kit/presets/CATALOG.json` and `code-composer-presets`.


## License and output policy

Code Composer software is licensed under **GNU AGPL v3.0 only (`AGPL-3.0-only`)**. See `LICENSE`.

- `COPYRIGHT_POLICY.md` — user responsibility for lawful inputs, references, and publication/distribution of outputs.
- `OUTPUT_POLICY.md` — explains that ordinary musical outputs are not intended to become AGPL-licensed merely because they were generated or rendered with Code Composer.
- `CREDITS.md` — research/reference provenance and third-party attribution policy.

These policy documents do not modify the AGPL. If Code Composer is later operated as a hosted web/API service, service-specific terms can be added separately without changing the software license.

## Repository policy

`main` is the stable source baseline. Generated wheels, plugin ZIPs, dogfood audio, and other release artifacts are not committed to source history; release tooling regenerates them from the canonical Skill and adapter sources. Feature work proceeds on branches and lands through validated commits/PRs.