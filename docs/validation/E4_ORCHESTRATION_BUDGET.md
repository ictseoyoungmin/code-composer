# v1.16 E4 — Orchestration Budget

Status: CLOSED

## Execution position

```text
arrangement / transition / pre-hook material
→ motif development
→ register & voicing
→ orchestration budget
→ phrase expression
→ renderer
```

This placement is deliberate: material generated downstream of the base arrangement cannot silently reintroduce a role the Agent declared silent.

## Implemented contracts

### Role classes

- primary
- secondary
- decorative

Budget arbitration preserves them in that priority order.

### Hard silence

`silence_roles` removes matching section events even when they came from transition/pre-hook generation. A sustain beginning in the previous section is truncated at the silent-section boundary.

### Phrase-gap decorative roles

A role listed in `phrase_gap_only_roles` is removed whenever its event overlaps an authored primary phrase body.

### Simultaneous role budget

`max_simultaneous_roles` counts unique sounding roles over actual event intervals, not notes. A three-note pad chord is one role.

### Allowed overlaps

`allowed_overlaps` is an authored preservation preference during budget arbitration. It does not make all unlisted role pairs globally illegal.

## Dogfood

Three sections were rendered:

1. `solo`: lead only; deliberately injected pad tail, bass anticipation, arp pre-hook and drum pickup.
2. `dialogue`: lead + pad, with arp restricted to lead-phrase gaps.
3. `bloom`: five available roles but a three-role simultaneous budget.

Results:

- solo non-lead event count: `0`
- solo removed by hard silence: `4`
- dialogue arp removed for phrase overlap: `11`
- bloom events removed for simultaneous-role budget: `14`
- final max simultaneous roles: `{'solo': 1, 'dialogue': 2, 'bloom': 3}`
- final dialogue arp starts: `[11.5, 12, 12.5, 15, 15.5]`

Final WAV SHA-256:
`f28efa91a4a5856fb0add56a2dae092f854aab34954bad9d36a488cb9d3101fe`

Repeated render SHA-256:
`f28efa91a4a5856fb0add56a2dae092f854aab34954bad9d36a488cb9d3101fe`

Deterministic repeat: `True`

## Regression

- pytest: 170 / 170 PASS
- runtime modules: 111
- import edges: 126
- import cycles: 0
- import failures: 0

## Backward compatibility

Direct Music IR without Performance IR remains E3 byte-identical:
`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

E3 register dogfood also remains byte-identical under E4:
`002f9ba2511ac082d803ba2e3421d112cc425f386a4cd9be8a254c532c7b0607`

## Scope boundary

E4 does not compose transition pickups, anticipations, silence or cadence extensions. It only enforces the orchestration budget around whatever material exists. Compositional transition generation is E5.
