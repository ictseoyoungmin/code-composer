# CR05 Dogfood — Lantern Current Incremental Preview

CR05 validates a separate draft-preview path for fast composition iteration.

The dogfood previews **bars 9–12** of Lantern Current at **24 kHz** with piano and
violin selected.

Sequence:

1. cold original preview → piano miss + violin miss;
2. identical warm preview → piano hit + violin hit;
3. accepted CR04 piano-only coda revision → piano miss + violin hit.

The cache stores **full-timeline dry stems**, not a stateful instrument starting at
bar 9. Piano pedal state and violin physical string/body state therefore develop from
the beginning of the piece. The range is sliced only after deterministic mixing.

Preview is explicitly not final/master authority. The normal final render path remains
unchanged.
