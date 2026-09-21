# S28-G — Subtle Treble Unison Decoherence

Status: **LISTENING CANDIDATE / PERCEPTUAL GATE OPEN**

## Evidence

User listening isolated the synthetic `지아옹/wah` character to the current high-register 3-string fixed-detune model: it was present in the current E5 rendering, absent in forced 1-string and detune=0 diagnostics, but those two diagnostics also reduced piano realism. Therefore S28-G preserves three strings and the existing mean detune.

## Implementation

New opt-in preset: `piano.concert_grand_natural_unison_subtle@1.0.0`.

Only 3-string notes at/above the authored start register receive tiny deterministic asymmetry:

- partial-level mistuning,
- string-level inharmonicity spread,
- string-level decay spread,
- string-level excitation/level spread.

The offsets are bounded and symmetric across the outer strings, preserving center pitch and authored mean detune. There is no random LFO/chorus, pitch sweep, 1-string substitution, or detune=0 shortcut. The canonical `piano.concert_grand_natural` remains byte-compatible.

## Exact problem reproduction

`tools/s28g_exact_problem_phrase_ab.py` reconstructs the exact S28-D treatment context. It first requires a fresh A render to be byte-identical to the previously evaluated problem WAV. Only after that proof does it render B by swapping the piano preset to the S28-G candidate.

Preserved: score, global seed, sustain-pedal timeline, S28-B strike identity semantics, S28-C chord hand-roll, S28-D phrase timing/gate, track gain, drive, ceiling, and tail.

## Closure rule

Do not close from modulation metrics alone. User listening must confirm that B reduces the electronic periodicity while retaining A's acoustic unison width and realism.
