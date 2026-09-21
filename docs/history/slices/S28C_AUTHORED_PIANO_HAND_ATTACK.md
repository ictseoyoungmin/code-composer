# S28-C — Authored Piano Hand Attack / Chord Micro-roll

Status: **ENGINEERING CANDIDATE / LISTENING GATE OPEN**

## Bottleneck

A wide voicing could place every hammer on the exact same sample. The resulting modeled attacks stack more like a sequencer than one physical hand.

## Surface

Optional note performance field:

```json
{"performance": {"piano_attack_offset_ms": 11.0}}
```

The field is explicitly authored, bounded to `[-20, +20] ms`, and applied only to render-local piano note copies. Canonical score `start_beat` remains unchanged. Controls are never shifted. A negative offset that would move a note before beat zero is rejected.

A representative six-note wide chord dogfood uses low-to-high offsets `[0, 4, 8, 11, 13, 15] ms`. The engine does not infer arpeggiation and does not add randomness.
