# Code Composer Exchange Workflow

Use `.ccx` when both collaborators continue editing in Code Composer.

1. Export a checkpoint with author/status/request/locks as appropriate.
2. The receiving collaborator imports into a workspace.
3. Continue from canonical Music IR, not from MIDI.
4. Respect handoff locks and requested scopes.
5. Export the next checkpoint; this creates a new revision.
6. Import only by fast-forward. If both sides changed from the same parent, stop on divergence instead of silently merging.

The `.ccx` package is an internal lossless collaboration surface. Do not replace it with the external delivery package.
