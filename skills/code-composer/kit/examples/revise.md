# Revision usage

Use revision as an explicit artistic operation, not analyzer-driven mutation.

```bash
code-composer-song revise score.json revision-plan.json revised-score.json revision-record.json
code-composer-song compare-revision song.json score.json revision-plan.json comparison/
```

The plan must bind the exact source score fingerprint, state the critique/preserve/acceptance intent, and name the targeted operations. The record exposes before/plan/after fingerprints and every changed event/mix scope.

Listen to the matched A/B. Metrics can support the critique, but they do not determine whether the revision is musically better.
