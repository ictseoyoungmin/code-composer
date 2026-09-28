# AG00 — Acoustic Guitar Contract / Architecture

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

AG00 creates extensible instrument boundaries before acoustic-guitar fidelity work begins.

## Contract additions

- Performance Score notes may carry `instrument_performance`: structurally deterministic JSON whose semantics are owned by the resolved engine.
- Performance Score supports `instrument_action`: an authored non-note action identifier plus structured parameters.
- Unsupported engine-scoped note payloads/actions are hard errors; the system never silently discards performance intent.
- `InstrumentEngine.mechanics_realizer` is a declarative mechanics hook resolved by the performance-domain registry. Existing violin realization is selected by `BowedWaveguideEngine.mechanics_realizer = "violin"`, removing the family-specific realization branch without creating an audio→performance import cycle.
- `acoustic_guitar` is a registered engine with its own package boundary and tail contract.

## AG00 acoustic-guitar baseline

Factory preset `acoustic_guitar.steel_foundation@1.0.0` is deliberately provisional. It exists only to prove:

Song → Execution Plan → Performance Score → render IR → instrument mechanics → renderer → WAV.

It is **not** an AG01 listening candidate and must not be cited as steel-string fidelity closure.

## Deferred semantics

AG00 does not assign meaning to guitar-specific `instrument_performance` keys and does not accept built-in `instrument_action` names yet.

- AG02 owns string/fret authority.
- AG03 owns right-hand excitation controls.
- AG04 owns left-hand articulation/damping.
- AG06 owns strum traversal.
- AG07 owns percussive guitar actions.
- AG08 owns persistent six-string/body state.

This keeps future semantics behind the engine boundary instead of baking them into the canonical core prematurely.

## Closure gates

1. acoustic-guitar preset/engine resolves through normal Song lowering;
2. minimal acoustic-guitar note renders finite audio with an engine-owned tail;
3. schema and Python validation agree on the new optional surfaces;
4. unsupported payload/action semantics fail loudly at the resolved engine;
5. violin mechanics remain behaviorally covered while the central bridge contains no violin-family realization branch;
6. all existing blocking regressions pass.
