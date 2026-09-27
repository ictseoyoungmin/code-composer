# Build and Packaging

Code Composer has two layers:

1. repository maintainer workspace;
2. canonical standalone skill at `skills/code-composer/`.

The Python package itself is rooted at `skills/code-composer/kit/` and uses `setuptools` with PEP 517.

## Version source

`code_composer.__version__` is the single Python package version source. `skills/code-composer/kit/pyproject.toml` declares:

```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "code_composer.__version__"}
```

The skill `VERSION` file must match the package version for the current release line. Codex and Claude plugin manifests must match it as well; `tools/verify_release_version.py` enforces the release-facing version surfaces.

## Runtime wheel

Connected build:

```bash
python -m pip wheel skills/code-composer/kit --no-deps -w dist/
```

Offline build when `setuptools>=68` is already available:

```bash
python -m pip wheel skills/code-composer/kit --no-deps --no-build-isolation -w dist/
```

## Standalone skill

```bash
python tools/validate_skill.py
python tools/build_skill.py
```

The resulting ZIP contains only `code-composer/` and must remain valid when extracted without the repository around it.

## Platform plugin artifacts

```bash
python tools/build_plugins.py
```

Repository-root `.codex-plugin/` and `.claude-plugin/` directories store thin platform manifests, while `.agents/plugins/` provides generic marketplace discovery. All three route to the canonical `./skills/` tree. The build copies the canonical `skills/code-composer/` tree into generated platform artifacts; there is no independently edited duplicate skill source.

## Release checks

1. `pytest -q`
2. `python skills/code-composer/kit/scripts/self_check.py`
3. `python tools/validate_skill.py`
4. `python tools/verify_plugin_distribution.py`
5. `python -m compileall -q skills/code-composer/kit/src`
6. build the runtime wheel with `--no-build-isolation` when offline;
7. install the wheel outside the repository source path and verify `importlib.metadata.version("code-composer") == code_composer.__version__`;
8. smoke all public entry points;
9. verify standalone skill and generated plugin ZIPs contain no root showcase/dogfood assets;
10. verify skill examples contain no polished audio/MIDI and fixtures are declared synthetic/non-reference;
11. run engine regression/compatibility hashes required by the active release.

For historical compatibility checks, verify the **wheel-shipped reference assets** that still exist in S0 (schemas only), keep **explicitly removed legacy mutation surfaces** unimportable, and compare any promised compatibility render against its **established baseline**.

## Public entry points

```text
code-composer
code-composer-compose
code-composer-midi
code-composer-collab
code-composer-exchange
code-composer-delivery
code-composer-presets
code-composer-violin
code-composer-admittance-fit
```

The package deliberately does not ship the repository's completed musical examples. Wheel package data contains current schemas, not a musical reference corpus.

## GitHub Release automation

`.github/workflows/release.yml` listens only to successful **push-triggered main CI** runs.

For a version that does not already have a GitHub Release it:

1. checks out the exact CI-validated main SHA;
2. verifies package / Skill / plugin / README version parity;
3. validates the standalone Skill and plugin distribution;
4. builds the runtime wheel, standalone Skill ZIP and Codex/Claude plugin ZIPs;
5. writes a release provenance manifest and portable SHA-256 manifest;
6. creates tag `v<VERSION>` at that exact validated SHA and publishes the GitHub Release using `docs/releases/v<VERSION>.md`.

If the release already exists, the workflow exits without mutating it.
