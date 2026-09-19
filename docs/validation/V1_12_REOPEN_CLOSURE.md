# v1.12 Reopen Closure

## Status

**CLOSED again after architectural replacement.**

## Revoked path

- vocabulary/alias driven prompt parser
- mood keyword map
- style -> fixed motif
- style -> fixed progression
- style -> fixed groove

## Canonical path

`Prompt -> Composer Agent -> CompositionBrief -> validator/compiler -> Music IR -> render/analyze -> Agent critique`

## Dogfood

1. Night-road brief: sparse final lead, topline 0, analyzer issues 0.
2. Dark broken-rhythm brief: hard forbidden lead/topline, both event counts 0, analyzer issues 0.
3. Bright syncopated-pop brief: lead-forward, topline 0, analyzer issues 0.

## Regression

- pytest: 45 / 45 PASS
- package imports: 102 modules / 0 failures
- forbidden canonical parser tokens in `src/`: 0
- representative SHA-256: `3cfd7e3507739b338da0d6a90b568efacf53fcd7bf86df6b04c66170d14a2e71`
- repeat SHA-256: `3cfd7e3507739b338da0d6a90b568efacf53fcd7bf86df6b04c66170d14a2e71`
- byte-identical: true
