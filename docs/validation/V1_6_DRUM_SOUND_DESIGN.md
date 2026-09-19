# v1.6 Drum Sound Design

## Goal

Replace minimal procedural percussion with inspectable, configurable drum synthesis while keeping deterministic rendering.

## Isolated QA highlights

- Snare centroid: 15078.5 -> 4108.9 Hz
- Snare body ratio (120-500 Hz): 0.0285 -> 0.4977
- Snare onset click score: 15.97 -> 6.92
- Hat air ratio (7-16 kHz): 0.4356 -> 0.5246
- Hat onset click score: 16.57 -> 12.27

## Whole-song dogfood

- Analyzer issues: 0 -> 0
- Energy correlation: 0.9921 -> 0.9889
- Verse transition discontinuity: 0.4403 -> 0.4183

The cleaner snare no longer supplies accidental broadband energy to the Verse transition. The correct fix was to recalibrate transition-material strength from 0.045 to 0.10, not to make the snare noisy again.

## Determinism

SHA-256: `d7531474ce5c7bff7c29871e68966093e2f702200d3e304e9dd0164157a09acb`

Repeated full-song render is byte-identical.
