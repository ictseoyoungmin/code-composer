# Code Composer repository structure

```text
code-composer/
├─ README.md                    # user-facing project entry point
├─ LICENSE
├─ COPYRIGHT_POLICY.md
├─ OUTPUT_POLICY.md
├─ CHANGELOG.md
├─ CREDITS.md
├─ .github/workflows/           # CI
├─ skills/
│  └─ code-composer/            # canonical self-contained agent skill
│     ├─ SKILL.md
│     ├─ VERSION
│     └─ kit/
│        ├─ INDEX.md
│        ├─ CAPABILITIES.md
│        ├─ COMMANDS.md
│        ├─ workflows/
│        ├─ contracts/
│        ├─ schemas/
│        ├─ presets/
│        ├─ fixtures/
│        ├─ scripts/
│        └─ src/                # deterministic engine implementation
├─ .codex_plugins/              # Codex adapter metadata only
├─ .claude_plugins/             # Claude adapter metadata only
├─ docs/                        # user/developer docs + historical evidence
│  ├─ architecture/
│  ├─ validation/
│  ├─ maintenance/
│  ├─ history/
│  └─ internal/
├─ examples/                    # maintainer-facing regression/showcase material
├─ tests/
└─ tools/                       # validation/build/release helpers
```

## Source of truth

`skills/code-composer/` is the single canonical agent-skill source. Platform plugin directories contain adapter metadata only; `tools/build_plugins.py` injects the canonical skill into generated plugin artifacts.

The Python package is rooted at `skills/code-composer/kit/`.

## Generated artifacts

Generated wheels, plugin ZIPs, standalone-skill ZIPs, rendered dogfood audio, build directories, caches, and `*.egg-info` are not canonical source and must not be committed to the repository.

## Examples and historical evidence

Repository-level `examples/` is maintainer-facing and is not bundled into the agent skill. The installed skill contains only operational examples and tiny synthetic protocol fixtures.

Historical slice reports and release evidence live under `docs/history/`, `docs/validation/`, and `docs/maintenance/`, not at repository root. This keeps the public project entry surface separate from internal closure history.
