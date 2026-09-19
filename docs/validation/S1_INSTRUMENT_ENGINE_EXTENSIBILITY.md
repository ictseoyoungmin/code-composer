# S1 — Instrument Engine Extensibility Closure

Status: **CLOSED**  
Engine version: **1.17.0**  
Date: **2026-09-17**

S1 replaces family-specific pitched-instrument branching with a registry-routed engine boundary. The central renderer now asks the selected engine to render notes, reserve tail, optionally post-process a track, and validate engine-specific patch state.

Built-in engines are `generic`, `piano`, and `bowed_string`. Existing generic/piano DSP was preserved: the v1.16 A/B/C closure renders remain byte-identical to S0R1.

The first extension dogfood is a deterministic bowed-string family engine. A repository-only validation patch uses semantic family `violin`, but no polished violin preset or completed musical example is shipped in the installed Skill. Agent-facing content contains only contracts, legal ranges, schema, and a placeholder template.

## Validation

- Focused S1/S0 policy: **29/29 PASS**
- Full regression: **310/310 PASS**
- Coverage: **89.49%**
- Bowed-string engine coverage: **88.65%**
- Registry coverage: **86.44%**
- Import sweep: **115/115 PASS**
- Static graph: **115 modules / 161 edges / 0 cycles**
- compileall: **PASS**
- Standalone Skill self-check: **PASS**
- Clean wheel bowed-string render: **PASS**
- External-delivery integration with bowed-string track: **PASS**

## Compatibility

- A lyrical piano: `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B rhythm centered: `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C sparse chamber electronic: `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

All three are byte-identical between S0R1 and S1.

## Packaging

Standalone Skill: **162 files**. Codex/Claude plugins: **164 files each**. Plugin Skill subtrees are byte-identical to the standalone Skill. Forbidden build/cache/audio/MIDI artifacts inside the Skill: **0**.

Repository dogfood WAV SHA-256: `5ad2f64ab85642001c074b688c7005961b8c08eccfb0cc060dce6371ec4b50b0`.
