# Code Composer repository structure

```text
code-composer/
├─ README.md                    # user-facing project entry point
├─ LICENSE
├─ COPYRIGHT_POLICY.md
├─ OUTPUT_POLICY.md
├─ CHANGELOG.md
├─ CREDITS.md
├─ .agents/plugins/             # generic agent marketplace discovery
├─ .claude-plugin/              # Claude plugin + marketplace metadata
├─ .codex-plugin/               # Codex plugin metadata and product interface
├─ .github/workflows/           # CI
├─ skills/
│  └─ code-composer/            # canonical self-contained agent skill
│     ├─ SKILL.md
│     ├─ VERSION
│     ├─ agents/
│     │  └─ openai.yaml         # OpenAI product discovery metadata
│     ├─ assets/
│     │  └─ icon.svg            # canonical Code Composer icon
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

`skills/code-composer/` is the single canonical agent-skill source. The repository-root discovery manifests route every supported platform to the same `./skills/` tree:

- `.codex-plugin/`
- `.claude-plugin/`
- `.agents/plugins/`

There is no platform-specific duplicate copy of the skill in source control. `skills/code-composer/agents/openai.yaml` and `skills/code-composer/assets/icon.svg` travel with the canonical skill itself.

`tools/build_plugins.py` may assemble installable plugin ZIPs by combining one thin root platform manifest with that canonical skill tree, but generated plugin artifacts are never source authority.

The Python package is rooted at `skills/code-composer/kit/`.

## Generated artifacts

Generated wheels, plugin ZIPs, standalone-skill ZIPs, rendered dogfood audio, build directories, caches, and `*.egg-info` are not canonical source and must not be committed to the repository.

## Examples and historical evidence

Repository-level `examples/` is maintainer-facing and is not bundled into the agent skill. The installed skill contains only operational examples and tiny synthetic protocol fixtures.

Historical slice reports and release evidence live under `docs/history/`, `docs/validation/`, and `docs/maintenance/`, not at repository root. This keeps the public project entry surface separate from internal closure history.
