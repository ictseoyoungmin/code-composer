# Song Contract Workflow

CR01 exposes the Composer-first Song model as a validation surface only.

1. Author a Song document using `kit/schemas/song.schema.json`.
2. Keep track IDs/functions arbitrary; do not map them onto the legacy six-role vocabulary.
3. Describe instrument identity with `family` / `variant`. Add `render_lock` only when the user or Composer explicitly intends to lock an engine/preset.
4. Run:
   ```bash
   code-composer-song validate SONG.json
   ```
5. Treat structural/cross-reference/lock errors as hard failures.
6. Treat `intent`, section intent, and part intent as soft musical context; the validator never converts them into presets, notes, or scores.
7. Use the returned SHA-256 fingerprint to identify the exact authored Song state.

CR01 does not render Song documents. Until Song lowering lands, rendering remains on the historical Music IR path. Do not build a compatibility adapter from the old CompositionBrief into Song.
