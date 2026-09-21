# S25 — S19 Core Cymbal Extension R4

Status: **ENGINEERING CANDIDATE — musical-context perceptual gate open**

## Preservation anchor

The user-selected pre-S20 S19 repository remains the drum-core checkpoint. R4 does not alter S19 legacy kick, snare, or closed hi-hat synthesis, and it does not import later coupled-head/cavity hardening.

## R4 objective

R3 removed the long tonal smear but remained too recessed against current GitHub main in the 2–6 kHz cymbal presence band. R4 recovers presence by redistributing existing modal energy and wash bandwidth only. It does **not** lengthen ride/crash decay or event tails.

### Ride changes relative to R3

- low plate modes (610–1980 Hz): gain redistribution factor ~0.90
- presence plate modes (2580–5960 Hz): factor ~1.15
- upper modes (7140–9720 Hz): factor ~0.80
- wash bandwidth: 3500–9800 Hz -> 3200–8500 Hz
- decay remains `0.72 s`
- event tail remains `1.35 s`
- contact/plate gains remain unchanged from R3
- output gain: `0.47 -> 0.57` to recover moderate musical-context level while staying below GitHub-main onset/tail energy

### Crash changes relative to R3

- lower mid modes (1260–1910 Hz): factor ~0.80
- presence mid modes (2310–3840 Hz): factor ~1.35
- lower high modes (3450–5940 Hz): factor ~1.25
- upper high modes (6710–10200 Hz): factor ~0.70
- low/mid/high/shimmer/contact component gains, bloom timing, decay constants, and event tail remain unchanged from R2/R3
- output gain: `0.36 -> 0.42` for moderate context recovery while retaining shorter absolute tail than GitHub main

## Intended gate

At 24 kHz, single-hit evidence should show:

- ride 2–6 kHz fraction > 0.52
- ride 6–11 kHz fraction < 0.22
- ride onset RMS (30–120 ms, v=.9) > 0.05
- ride late/onset RMS ratio < 0.24
- crash 2–6 kHz fraction > 0.44
- crash 6–11 kHz fraction < 0.15
- crash onset RMS (30–120 ms, v=.9) > 0.058
- crash delayed high-frequency bloom remains low-first at onset
- crash late/onset RMS ratio < 0.48

Final acceptance remains musical-context listening, not metrics alone.
