# Compose Workflow

1. Extract explicit musical intent and constraints from the current user request; do not imitate bundled fixtures.
2. Decide whether a seed IR exists. If none exists, create only the structural seed required by the current task.
3. Author/validate a Composition Brief using `kit/contracts/composition-brief.md` and the schema.
4. Compile with `code-composer-compose`.
5. Render with `code-composer`.
6. Inspect analysis/evidence and the actual render.
7. If revision is needed, author an explicit structured revision; analyzers must not mutate music.
8. Repeat until the requested quality/closure gate is met.

Reopen upstream structure when silhouette-level musical form, major relationships, or core intent is wrong; do not polish a bad premise.
