# S27-D — Tom Family Authenticity

Status: **CLOSED / USER PERCEPTUAL PASS — 2026-09-20**

## Goal

Make high, mid and floor toms read as differently sized two-head drums, not pitch-shifted copies. Preserve every pre-S27-D renderer byte-exactly.

## Research basis

Randy Worland's 2011 JASA demonstration notes that toms and snares use two circular membranes on a cylindrical shell and that the enclosed air/shell strongly couples lower membrane modes while higher modes remain more independent (DOI `10.1121/1.3654611`). Drum-shell modal research likewise describes vibration transfer from batter head to shell and enclosed air to the lower head, with lower modes contributing strongly to timbre.

Code Composer uses those causal relationships only. No paper code, sample, IR, or measured modal table is copied.

## Model

`stick force -> batter head -> enclosed-air transfer -> resonant head -> cavity projection + shell response`

Family parameters differ in:
- head fundamental and decay;
- bottom-head delay/transfer;
- cavity weighting and bandwidth;
- shell modal frequencies/decay;
- output bandwidth and event tail.

Center strokes emphasize low radiating membrane modes. Edge strokes suppress the fundamental/cavity and expose higher membrane, shell and stick-contact content.

## Explicit events

- `tom_high`, `tom_high_edge`
- `tom_mid`, `tom_mid_edge`
- `tom_floor`, `tom_floor_edge`

MIDI: high 50, mid 47, floor 43.

## 24 kHz source evidence

At equal authored velocity/seed, dominant low-frequency body is approximately:
- high: 179 Hz
- mid: 133 Hz
- floor: 92 Hz

Late energy increases with drum size, while edge strokes shift spectral centroid upward by roughly 30% without becoming simple gain changes.

## Closure gate

1. High/mid/floor must read as one family with clearly different physical size.
2. Floor tom must have longer/heavier low body without a synthetic sine tail.
3. Center/edge must be recognizably different contacts.
4. A descending high->mid->floor fill must sound like a drummer moving across the kit.
5. No pre-S27-D event may change byte output.
6. Listening in actual groove outranks isolated metrics.
