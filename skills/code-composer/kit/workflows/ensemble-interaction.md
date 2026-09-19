# Ensemble Interaction Workflow

Use this only after the notes, roles, register plans and orchestration budget are already correct.

1. Identify a section where ensemble coordination is audibly too grid-locked or support roles mask the musical leader.
2. Choose `leader_role` from the active roles for that section. Do not impose one permanent leader on every section unless the musical intent requires it.
3. Author small timing relationships in milliseconds. Start well inside the ±30 ms contract; use larger offsets only when listening evidence supports them.
4. If a support role masks the leader during actual overlap, author an `overlap_velocity_scale`. Do not reduce unrelated notes outside overlap.
5. Optionally author small role pan offsets in `performance_ir.realization.ensemble`; these add to existing pan rather than replacing the mix.
6. Realize Performance IR, render, and listen to control/treatment A/B. Confirm note content and orchestration identity before judging the interaction.
7. Inspect expressive QA for masking evidence. Treat it as evidence only; revise the authored interaction explicitly if needed.

Do not use S15 to repair bad composition, register planning, wrong instrumentation, or a defective instrument engine. Fix those upstream first.
