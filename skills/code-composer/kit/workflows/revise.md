# Revise Workflow

1. Freeze the current Performance Score and compute its exact fingerprint.
2. Listen to the render and inspect evidence only to locate the narrowest musical problem.
3. Write a Composer-authored `code-composer-revision-plan/v1`:
   - describe the critique;
   - name what must remain unchanged;
   - state acceptance in musical terms;
   - select explicit revision operations.
4. Run:
   ```bash
   code-composer-song revise PERFORMANCE_SCORE.json REVISION_PLAN.json REVISED_SCORE.json REVISION_RECORD.json
   ```
5. The runtime must reject the plan if the source score fingerprint does not match exactly.
6. For matched listening evidence, run:
   ```bash
   code-composer-song compare-revision SONG.json PERFORMANCE_SCORE.json REVISION_PLAN.json OUTPUT_DIR/
   ```
7. Listen to `before.wav` and `after.wav`. Use `revision_record.json` to verify only the intended score scope changed.
8. Accept, refine, or reopen from listening. Metric deltas are evidence only.

Current CR04 operations:
- `scale_velocity` — beat-range velocity scaling, optionally narrowed to explicit note IDs;
- `thin_accompaniment` — remove explicitly named note events only;
- `set_track_mix_gain` — set one score-track mix gain;
- `shift_register` — move notes in an explicit beat range by whole octaves.

Analysis modules must never author or apply these operations. Do not recreate the removed issue→proposal→patch architecture.

Do not use bundled fixture note/rhythm values as revision ideas.
