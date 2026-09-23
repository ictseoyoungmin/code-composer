# CR00 — Composer Rebuild Boundary / Pre-refactor Freeze

Status: **CLOSED**

Issue: #16

## Decision

Code Composer is still pre-release. The composer-facing architecture will therefore be replaced **without a v2 compatibility track and without migration adapters for the current authoring model**.

> **Code Composer exists to make music. Contracts preserve and validate the artist's decisions; they do not dictate the composition.**

This is not a move toward a contract-free system. The target contract depth is approximately the rigor of v1.16.x: explicit canonical state, cross-reference validation, deterministic realization, provenance, hard/soft invariant separation, analyzer non-mutation, and listening evidence before musical closure.

The mistake being removed is that authoring and execution contracts became the same surface.

## Frozen pre-refactor references

- `main`: `d7d832085663eaa68b4ec671df938f27f6fbbee5` — S31 baseline.
- main CI: Python 3.10 / 3.12 **SUCCESS**, Actions run `35780352743`.
- S32 evidence: PR #15, HEAD `29d501c0725187eaf56eddb9a8fcf49c0aebb218`, draft/unmerged at CR00 freeze; then **closed unmerged as superseded by CR00** after its regression evidence was recorded.
- historical v1.16 source artifact: `code-composer-v1.16.0(1).zip`, 43,284,407 bytes.
- historical v1.16 integrated closure: **224/224 PASS**, **88% coverage**, three integrated dogfoods.

S32 is evidence, not a migration target. If the new architecture removes the failed path, the old implementation does not need to be transplanted; the regression requirement does.

## KEEP

Runtime assets that have independent value from the current authoring model are retained by default:

- piano/acoustic-piano engine and piano naturalism work;
- bowed-string / bowed-waveguide / violin mechanics and realizers;
- plucked-bass engine;
- percussion / modeled drum / hi-hat work;
- generic engine infrastructure where it remains useful;
- DSP primitives;
- mixer, buses, routing, and automation;
- deterministic render machinery;
- MIDI and external delivery export;
- CCX/lossless-handoff and provenance concepts;
- music-theory utilities;
- objective analyzers whose measurements remain valid.

KEEP does not mean immutable API. CR01 may change how these capabilities are requested or represented.

## REBUILD

The following are not architectural constraints for the rebuild:

- `CompositionBrief` as the mandatory first authoring surface;
- `composer_planner.py` seed-mutating Brief→Plan flow;
- `code-composer-compose SEED_IR BRIEF ...` as the new-song public contract;
- privileged `lead / topline / pad / bass / arp / drums` roles;
- role names doubling as musical function, instrument identity, priority, and engine routing;
- fixed-role arrangement/development/orchestration authority;
- current Music IR shape as a compatibility promise;
- current `validation_contracts.py` fixed-role/development vocabulary;
- metric-driven aesthetic acceptance.

Useful algorithms inside those files may survive only as lower-level utilities under the new Song Model.

## DELETE / DO NOT BUILD

- no legacy CompositionBrief → new Song Model migration layer;
- no six-role compatibility adapter for new composition;
- no requirement that a new song begin from a seed IR;
- no preservation of asymmetric `register_shift` semantics;
- no automatic “good music” pass/fail score;
- no self-certification where a worker changes the target instead of the music.

Historical docs and fixtures remain evidence only.

## Mandatory regression evidence

CR01+ must preserve these failures as tests or dogfood evidence:

1. **Hidden 0.82 phrase gate** — neutral authored rhythm must not be silently shortened.
2. **Generic TV-static path** — breath+saw+drive/gain hazard and wrong instrument routing must not recur.
3. **Generic endpoint safety** — independently rendered note buffers must close safely.
4. **Register/harmony divergence** — shared harmony must never silently become lead +12 / pad +6 / bass 0.
5. **Seed-role coupling** — new composition must create its own track/instrument ownership.
6. **Six-role lock-in** — arbitrary tracks/functions must be representable.
7. **QA self-certification** — unmet acceptance cannot be labeled final.
8. **Incomplete provenance** — deliverables must identify exact source/revision state.
9. **Non-portable checksums** — manifests use relative paths.
10. **Dirty fresh clone** — repository owns EOL policy.

## CR01 entry boundary

CR01 is **Minimal Song Model + Contract Foundation**.

It may begin only from these rules:

- composer-facing state is smaller and more musical than the current detailed Brief;
- lowered canonical state remains strict;
- track identity, musical function, instrument identity, and render engine are distinct concepts;
- arbitrary tracks are legal;
- new composition is seedless by default;
- renderer-specific details are lowering concerns unless explicitly locked by the user;
- invalid cross-references/harmonic ownership/instrument capability/provenance fail before render;
- no compatibility work for the unreleased old authoring model.

## CR00 closure

CR00 is **CLOSED**. It changes no synthesis or composition behavior, so no perceptual music gate was required.

Closure evidence:
- Issue #16: closed by merged PR #17.
- PR #17: merged via squash.
- CR00 merge on main: `213d43a7783a28be8b8e28bbaccf4b0e83680755`.
- pre-merge validation HEAD: `ecb6e8e900cf07fb0d4b048b420fc4c0d8f2bcbc`.
- pre-merge Actions run `35878514190`: Python 3.10 / 3.12 SUCCESS.
- no runtime implementation file changed in the CR00 boundary merge.
- checkout hygiene is now a blocking CI job: a fresh local clone under `core.autocrlf=true` must remain clean after `git add --renormalize .` and README must resolve to `eol=lf`.

The following requirements are satisfied:

Required:

- exact pre-refactor checkpoint recorded;
- KEEP / REBUILD / DELETE / EVIDENCE_ONLY boundaries recorded;
- S32/fresh-worker regressions frozen as mandatory evidence;
- legacy architecture docs marked historical/pre-refactor;
- cross-platform EOL policy owned by the repository;
- CI success on Python 3.10 and 3.12.
