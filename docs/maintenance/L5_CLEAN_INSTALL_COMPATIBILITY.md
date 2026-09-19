# Legacy Cleanup L5 — Clean Install / Compatibility

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L5 closes the post-release legacy-cleanup chain by validating the L4-cleaned package as an installed distribution outside the repository. No runtime or schema behavior is changed.

## Scope

L5 does not remove another runtime surface. Its purpose is to prove that L0–L4 cleanup did not leave a repository-only success state where imports, package data, entry points, or compatibility behavior work only from `src/`.

The gate covers:

- PEP 517 wheel build,
- installed metadata/version/dependency contract,
- source-tree-independent imports,
- the L1 public/flat compatibility boundary,
- continued absence of L2 superseded mutation surfaces,
- both public console entry points,
- wheel-shipped schemas/examples,
- representative v1.15 byte compatibility,
- v1.16 final dogfood determinism.

## Clean build and install

Built distribution:

```text
code_composer-1.16.0-py3-none-any.whl
SHA-256 edf09467944daa6dfee6699fc3008e548d5a0fca97d252a923556914e22d3b3c
```

Build path:

```text
python -m pip wheel . --no-deps --no-build-isolation
```

The wheel was installed into a target outside the repository. `code_composer.__file__` resolved from that installed target, and the repository `src/` directory was not on the import path.

The offline validation runner supplied pre-provisioned runtime dependencies rather than downloading them. Installed versions satisfy the wheel metadata contract:

```text
numpy 2.3.5  satisfies >=1.24
scipy 1.17.0 satisfies >=1.10
```

This is an environment provision detail only; Code Composer itself was loaded exclusively from the new wheel.

## Installed package contract

Version identity:

```text
code_composer.__version__             1.16.0
importlib.metadata.version(...)       1.16.0
wheel METADATA Version                1.16.0
```

Wheel payload:

```text
118 members
99 Python modules/files
4 packaged reference schemas
10 packaged reference examples
```

Both declared console entry points executed successfully:

```text
code-composer
code-composer-compose
```

`code-composer-compose` compiled the packaged seed/brief pair. `code-composer` rendered the packaged legacy `demo_ir` and emitted resolved/analysis outputs.

## Public import compatibility

The closed L1 audit defines 38 flat/public module decisions.

Installed-wheel result:

```text
L1 retained / deprecated-but-supported imports    34 / 34 PASS
L2 removed flat mutation imports                   4 / 4 ABSENT
L2 removed nested semantic mutation targets        4 / 4 ABSENT
```

This includes the intentional v1 compatibility surface `code_composer.resolve` and the retained `code_composer.transition_material_analysis` provenance analyzer alias.

The removed mutation stack remains unavailable:

```text
composition.transition_material
code_composer.transition_material

composition.pre_hook_build
code_composer.pre_hook_build

mix.transition_automation
code_composer.transition_automation

composition.section_calibration
code_composer.section_calibration
```

## Byte compatibility

The clean-installed public render entry point reproduced the established v1.15 representative baseline exactly:

```text
589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0
```

The same installed wheel rerendered all three v1.16 final dogfoods byte-identically:

```text
A  93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba
B  7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377
C  db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f
```

## Runtime/schema preservation

L5 makes documentation/test/maintenance-state changes only. The aggregate hash over `src/` and `schemas/` remains exactly the L4 value:

```text
bcee602c1f5d96246910acf1052496923fb4aafc52cf0a8becd84759f6318ea4
```

Therefore L4 → L5 runtime/schema payload change is **0**.

`tests/test_legacy_cleanup_l4.py` was narrowed only where its temporary handoff assertion required L4 to remain the current maintenance tip. Its durable L4 closure invariants remain intact. `tests/test_legacy_cleanup_l5.py` owns the final maintenance/installed-distribution closure guards.

## Verification

Machine-readable evidence: `docs/maintenance/L5_CLEAN_INSTALL_COMPATIBILITY.json`.

Closure results:

```text
Focused L3/L4/L5    17 / 17 PASS
Full regression    252 / 252 PASS
Coverage                    89%
compileall                  PASS
Import modules          98 / 0 failures
Static modules              99
Static edges                121
Cycles                        0
```

## Maintenance closure

```text
L0 Surface Inventory                    CLOSED
L1 Public Import / Compatibility        CLOSED
L2 Superseded Legacy Removal            CLOSED
L3 Historical / Fixture Classification  CLOSED
L4 Dead Test / Reference Cleanup        CLOSED
L5 Clean Install / Compatibility        CLOSED

v1.16.0                                 CLOSED
```

The legacy-cleanup maintenance chain is complete. Further changes should begin a new explicitly scoped maintenance or version-planning chain rather than silently extending L0–L5.
