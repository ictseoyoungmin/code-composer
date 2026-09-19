# Render and QA Workflow

Use `code-composer` to validate, resolve and render. Treat resolved IR and analysis as evidence for the agent, not as automatic creative mutation instructions.

Minimum closure checks:
- validation succeeds;
- render completes deterministically;
- clipping/artifact checks are acceptable for the task;
- important user constraints remain true in resolved IR;
- before/after comparisons use matched conditions when revising;
- hashes are recorded when compatibility/reproducibility matters.
