# Song Contract Workflow

CR01 establishes the Composer-first Song model. CR02 adds deterministic execution lowering without legacy seed IR.

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
8. When runtime planning is needed, run:
   ```bash
   code-composer-song lower SONG.json EXECUTION_PLAN.json
   ```
9. Treat lowering failures as explicit missing/unsupported execution information. Do not repair them by inventing a seed IR, generic instrument fallback, hidden voicing, or register shift.

The Execution Plan is still symbolic with respect to actual notes/voicings. CR02 does not render audio. Do not build a compatibility adapter from the old CompositionBrief into Song.
