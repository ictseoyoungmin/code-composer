# Code Composer Documentation / Reference Index — S0

Status: **CURRENT**  
Engine feature baseline: **v1.17.0 — M1/M2/M3 + S1/S2/S3/S4/S5/S6 CLOSED**  
Repository packaging state: **S0R1 Canonical Skill Hygiene — CLOSED**
Instrument architecture state: **S1 Instrument Engine Extensibility — CLOSED**
Bowed-string sound state: **S5 Bowed-String Sound Hardening — CLOSED**
Continuous bowed-state: **S6 Continuous Bowed-String State & Bow-Change Transients — CLOSED**

## Current authority

For agent operation, the authority is the self-contained skill:

- `../skills/code-composer/SKILL.md`
- `../skills/code-composer/kit/INDEX.md`
- `../skills/code-composer/kit/CAPABILITIES.md`
- `../skills/code-composer/kit/COMMANDS.md`
- `../skills/code-composer/kit/EXAMPLE_POLICY.md`
- `../skills/code-composer/kit/SOURCE_MAP.md`

For repository maintainers, use:

- `../README.md` — repository/product overview.
- `../CREDITS.md` — research acknowledgements, provenance, and future third-party asset attribution policy.
- `../STRUCTURE.md` — current repository/skill boundary.
- `architecture/SKILL_REPOSITORY_S0.md` — S0 design decision.
- `BUILD.md` — current build/install/release procedure.
- `validation/S0R1_CANONICAL_SKILL_HYGIENE.md` — current packaging hygiene closure.
- `validation/S1_INSTRUMENT_ENGINE_EXTENSIBILITY.md` — instrument engine architecture closure.
- `architecture/S5_BOWED_STRING_SOUND_HARDENING.md` — modeled bowed-string sound design.
- `validation/S5_BOWED_STRING_SOUND_HARDENING.md` — sustained-note modeled bowed-string closure.
- `architecture/S6_CONTINUOUS_BOWED_STRING_STATE.md` — continuous state / bow-change design.
- `architecture/S7_PHYSICAL_STRING_CROSSING_COUPLING.md` — multi-string state / crossing coupling design.
- `validation/S6_CONTINUOUS_BOWED_STRING_STATE.md` — current continuous bowed-state closure.
- `validation/S7_PHYSICAL_STRING_CROSSING_COUPLING.md` — current string-crossing coupling closure.
- `../REPOSITORY_STATUS.json` — machine-readable S0 status.

## Current engine architecture

The S0 reframe does not replace the closed music-engine architecture. Relevant current/historical domain documents remain:

- `architecture/ARCHITECTURE.md`
- `architecture/MIDI_COLLAB_EXPORT_V117.md`
- `architecture/CODE_COMPOSER_EXCHANGE_V117.md`
- `architecture/EXTERNAL_DELIVERY_V117.md`
- `validation/V117_M1_MIDI_COLLAB_EXPORT.md`
- `validation/V117_M2_CODE_COMPOSER_EXCHANGE.md`
- `validation/V117_M3_EXTERNAL_DELIVERY.md`

## Repository examples are not agent references

`../examples/` is maintainer-only regression, compatibility, dogfood and showcase evidence. It may contain complete music. It is deliberately excluded from `skills/code-composer/` and from standalone skill/plugin artifacts except for the skill's tiny synthetic protocol fixtures.

The installed skill follows: **Examples teach operation, never taste.**

## Schemas

Agent-facing schemas live at `../skills/code-composer/kit/schemas/`. Wheel-packaged copies live at `../skills/code-composer/kit/src/code_composer/reference/schemas/` and are byte-identical.

Polished musical examples are **not** mirrored into the installed Python package in S0.

## Historical evidence

The following remain immutable/interpretive historical records rather than current navigation authority:

- v1.16 L0-L5 legacy cleanup reports in `maintenance/`;
- older validation closure reports in `validation/`;
- superseded roadmaps in `roadmap/`;
- `../V1.16_DESIGN_STATUS.json` and `../V1.17_DESIGN_STATUS.json` as version-era status evidence;
- `../examples/v1.16/final_closure/` as v1.16 dogfood/closure evidence.

S0 changes packaging and agent-facing information architecture. It does not reopen v1.16 or v1.17 M1-M3 music behavior.

- `architecture/S8_BRIDGE_ADMITTANCE_BODY_FEEDBACK.md` — causal bridge-admittance/body-feedback design.
- `validation/S8_BRIDGE_ADMITTANCE_BODY_FEEDBACK.md` — S8 closure evidence.
