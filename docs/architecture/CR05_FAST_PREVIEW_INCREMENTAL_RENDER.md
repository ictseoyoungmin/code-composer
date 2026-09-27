# CR05 — Fast Preview / Incremental Render

Status: **CLOSED**

Issue: #30

## Purpose

CR05 separates fast composition iteration from final/master rendering.

```text
Song + Performance Score
    ↓
Execution Plan / physical realization
    ↓
deterministic full-timeline dry stems
    ↓
persistent track-local cache
    ↓
selected-track deterministic mix
    ↓
bar/beat range slice
    ↓
24 kHz draft preview
```

Preview is never final/master authority.

## Why full-timeline stems

Stateful piano and violin engines cannot be initialized safely at an arbitrary preview
bar. Pedal state, piano body resonance, violin string memory, and bow/body state depend
on earlier music.

CR05 therefore renders a cacheable **full-timeline dry stem** from piece start. A bar
or beat preview is sliced only after deterministic mixing.

This preserves physical state while still avoiding re-synthesis of unchanged tracks.

## Cache identity

`code-composer-preview-stem-cache/v1` keys include only dry-stem dependencies:

- explicit renderer epoch;
- sample rate;
- aligned full-timeline sample count;
- BPM / meter;
- global seed;
- graph-mode flag;
- full resolved track events/performance metadata;
- instrument ID and resolved patch.

Track mix gain is deliberately not part of dry-stem identity. A mix-only revision can
reuse the stem.

A different Performance Score fingerprint by itself does not invalidate every track.
A piano-only event revision changes the piano key while the identical violin key remains
reusable.

Any code/engine change that can alter dry-track samples must bump
`STEM_CACHE_RENDERER_EPOCH`.

## Public request

`code-composer-preview-request/v1` binds an exact Performance Score fingerprint and
selects:

- one bar range or beat range;
- one or more track IDs;
- draft sample rate.

CLI:

```bash
code-composer-song preview \
  SONG.json PERFORMANCE_SCORE.json PREVIEW_REQUEST.json \
  OUTPUT.wav CACHE_DIR [REPORT.json]
```

The generated `code-composer-preview-report/v1` records:

- source Song / score / Execution Plan fingerprints;
- request fingerprint;
- selected range and tracks;
- per-track cache keys and hit/miss state;
- preview metrics;
- WAV hash;
- `final_render_authority: false`.

## First dogfood — Lantern Current bars 9–12

24 kHz, piano + violin selected.

Sequence:

1. cold original preview → **0 hits / 2 misses**;
2. identical warm preview → **2 hits / 0 misses** and byte-identical WAV;
3. accepted CR04 piano-only coda revision → **1 hit / 1 miss**:
   - violin: hit;
   - piano: miss.

The revision therefore re-synthesizes only the changed instrument stem.

## Closure

Engineering gate:
- strict Preview Request/Report schemas with source/package parity;
- exact source-score binding;
- deterministic warm-cache byte equality;
- piano-only revision preserves violin cache identity;
- changed piano invalidates piano stem;
- selected bar range produces expected duration;
- clipping-free preview;
- normal final render path unchanged;
- Python 3.10 / 3.12, checkout, Skill/plugin/build PASS.

Perceptual gate:
- listen to original and revised bars 9–12 previews;
- verify that the preview is musically useful for iteration and does not introduce
  state-boundary artifacts relative to the full composition context.

Metrics and cache hits prove execution behavior, not artistic quality.


## Closure

CR05 is **CLOSED**.

Authoritative evidence:
- Issue #30: closed / completed.
- PR #32: merged after explicit perceptual usefulness PASS.
- validated candidate HEAD: `a9fc8a950a794ca6ab545b14a724248c135903c5`.
- implementation merge on main: `8536aa42cd6e6dffbeaafa31232fc9b2807111da`.
- pre-merge CI #100 / run `36233292733`: checkout-hygiene + Python 3.10 + Python 3.12 SUCCESS.
- Python 3.10 / 3.12 blocking suite: **730 passed / 3 deselected**.
- CR05 Preview Dogfood #9 / run `36233292766`: SUCCESS.
- artifact ID: `10903092615`.
- artifact digest: `sha256:0e5acc9d1020a538a0338973941b8b7aa60c30374774555da8ea5dc5f5c53c01`.
- cold original cache: **0 hit / 2 miss**.
- identical warm preview: **2 hit / 0 miss**, byte-identical WAV.
- CR04 piano-only revision: **violin hit / piano miss**.
- persistent cache verifies metadata + renderer epoch + cache key + identity + shape + stem SHA-256.
- original/revised preview clipping: 0.0.
- preview authority remains draft-only.
- post-merge main CI #101 / run `36307541776`: checkout-hygiene + Python 3.10 + Python 3.12 SUCCESS.
- perceptual usefulness verdict: PASS.

The CR05 preview path is intentionally separate from final/master render authority.

Next: **CR06 — Evidence-first QA**.
