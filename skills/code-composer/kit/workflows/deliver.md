# External Delivery Workflow

Use this only when internal Code Composer work is ready to leave the system.

1. Run `code-composer-delivery` on the approved canonical IR.
2. Verify the output manifest and hashes.
3. Verify the reference mix opens and matches the approved render.
4. Verify full-song and per-track MIDI parse.
5. Verify stems share sample rate, frame count and alignment.
6. Tell the collaborator that stems are aligned source/track-route exports; shared sends, sidechains, buses and master nonlinear processing remain represented by the reference mix/resolved state.

Do not infer external DAW edits back into canonical Music IR unless a future explicit round-trip contract exists.
