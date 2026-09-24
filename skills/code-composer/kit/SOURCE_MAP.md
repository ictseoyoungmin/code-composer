# Source Map

Do not read source to learn normal usage. Use this map only after a source-inspection exception in `SKILL.md` applies.

| Need | Narrow source area |
|---|---|
| Composer-first Song contract | `src/code_composer/core/song.py`, `src/code_composer/song_validation.py`, `app/song_cli.py` |
| Song → Execution Plan lowering | `src/code_composer/execution/plan.py`, `src/code_composer/execution/lowering.py` |
| Authored Performance Score / render bridge | `src/code_composer/execution/performance_score.py`, `execution/render_bridge.py`, `execution/artistic_render.py` |
| Pre-refactor Composition brief validation/compiler | `src/code_composer/agent/composition_brief.py`, `agent/composer_planner.py` |
| Expressive score/performance contracts | `src/code_composer/agent/expressive_score_plan.py`, `agent/performance_ir.py` |
| Deterministic arrange/resolve | `src/code_composer/composition/arrange.py`, `composition/resolve.py` |
| Performance realization | `src/code_composer/composition/performance.py` |
| Instrument engine registry | `src/code_composer/audio/engines/registry.py`, then one engine module only |
| Modeled bowed-string synthesis | `src/code_composer/audio/engines/bowed_waveguide.py` |
| Percussion synthesis / modeled acoustic kit | `src/code_composer/audio/percussion.py`, `src/code_composer/audio/engines/percussion.py` |
| S26 drum-kit overhead / room / bus integration | `src/code_composer/audio/drum_kit.py` |
| Measured bridge-admittance ERA fitting | `src/code_composer/audio/bridge_admittance_fit.py`, `app/admittance_fit_cli.py` |
| Low-level synthesis/DSP | `src/code_composer/audio/generic_synth.py`, `src/code_composer/audio/piano.py`, or the selected engine module |
| Mixing | `src/code_composer/mix/` |
| Analysis evidence | `src/code_composer/analysis/` |
| S27-F drummer limb/performance feasibility | `src/code_composer/analysis/drummer_performance_analysis.py` |
| Render pipeline | `src/code_composer/pipeline/` |
| MIDI export | `src/code_composer/export/midi.py` |
| `.ccx` exchange | `src/code_composer/exchange/package.py`, `app/exchange_cli.py` |
| External delivery/stems | `src/code_composer/export/delivery.py`, `app/delivery_cli.py` |
| Public CLIs | `src/code_composer/app/` |
| Core IR validation | `src/code_composer/core/ir.py`, `validation_contracts.py` |

Never broad-scan `src/` first when a narrower route is known.

- Factory preset registry/materialization -> `src/code_composer/presets.py`
- Preset CLI -> `src/code_composer/app/presets_cli.py`
- Bundled runtime preset data -> `src/code_composer/reference/presets/` (do not inspect for normal composition; use `presets/CATALOG.json`)

- Violin physical performance planner -> `src/code_composer/performance/violin.py`, `src/code_composer/performance/violin_double_stop.py`, `app/violin_cli.py`
