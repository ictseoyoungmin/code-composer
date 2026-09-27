from pathlib import Path
import json

import code_composer


ROOT=Path(__file__).resolve().parents[1]


def test_release_version_surfaces_are_synchronized():
    version=(ROOT/"skills/code-composer/VERSION").read_text(encoding="utf-8").strip()
    assert version=="1.18.1"
    assert code_composer.__version__==version
    for relative in (".codex-plugin/plugin.json",".claude-plugin/plugin.json"):
        manifest=json.loads((ROOT/relative).read_text(encoding="utf-8"))
        assert manifest["version"]==version
    readme=(ROOT/"README.md").read_text(encoding="utf-8")
    assert f"version-v{version}-" in readme
    assert f'alt="Version v{version}"' in readme


def test_standalone_skill_builder_uses_version_source():
    source=(ROOT/"tools/build_skill.py").read_text(encoding="utf-8")
    assert "VERSION=(SKILL/'VERSION')" in source
    assert "code-composer-skill-v{VERSION}.zip" in source
    assert "code-composer-skill-v1.17.0.zip" not in source
