# v1.16 H3 — E2 Semantic Closure

Status: CLOSED

## Audit defects closed

### 1. `call` was an alias of `exact`

Before H3:

```python
if kind in {'exact','call'}:
    pass
```

H3 makes call/response explicit musical relations:

```text
call
  → explicit intervals
  → explicit rhythm

response
  → explicit intervals
  → explicit rhythm
  → responds_to: earlier call statement ID
```

A response reference must:
- name an existing statement,
- point to an earlier statement,
- point to a statement that contains an explicit `call` transform.

The compiled motif report stores:

```text
relation.role = call | response
relation.responds_to = <statement_id>   # response only
```

### 2. `identity_floor` contradicted E6 QA

Before H3, E2 stopped compilation when `identity.score < identity_floor`, which made E6 `MOTIF_IDENTITY_LOSS` unreachable in the canonical render→QA→revision loop.

H3 separates two meanings:

```text
identity_floor
= Agent-authored QA target
= render remains allowed
= E6 emits MOTIF_IDENTITY_LOSS when missed

identity_hard_min (optional)
= explicit source-aware validity barrier
= compile fails only below this threshold
```

Contract invariant:

```text
0 <= identity_hard_min <= identity_floor <= 1
```

No automatic transform fallback is ever substituted.

## H3 dogfood

One explicit call is followed by a response that references the call.

Before Agent revision:
- call identity: 0.774
- response identity: 0.2967
- response target met: False
- QA: `{'MOTIF_IDENTITY_LOSS': 1}`

After Agent rewrites only the response intervals:
- call identity: 0.774
- response identity: 0.6579
- response target met: True
- QA: `{}`

Revision comparison:
- target issues: 1 → 0
- introduced non-target issues: 0
- regression-free: True
- improved: True

Both before/after renders:
- sample rate: 44.1 kHz
- clipped sample ratio: 0
- deterministic repeat render: byte-identical

WAV SHA-256:
- before: `02402daa21ae04b966851f1aa7775552e9c7d267a93e53edf94f4d915b64642e`
- after: `0023687bde334c2b4bc44b4b89eb83c8fb9c38b298fdf12e94c4adc7a07bf960`

## Regression

- H3 focused semantic suite: 59 PASS during implementation
- full regression: 209 / 209 PASS
- coverage: 87%
- runtime modules: 113
- import edges: 132
- import cycles: 0
- import failures: 0

## Backward compatibility

The pre-H3 E2 five-section motif dogfood, which uses no `call` transform and whose statements already satisfy their identity targets, is byte-identical between H2 and H3:

- Music IR SHA-256: `ec97bd6baad35a77d8a45894f635691a850ca0023b9b30ed915e00e9a51ad0f9`
- WAV SHA-256: `d82ded5566351576bc2c903bdeef7a15668c7d2d59afc7cac31b0452060e3bed`

The representative legacy v1.15.6 path remains inherited from H2 unchanged.

## Next hardening

H4 — canonical revision-surface cleanup.
