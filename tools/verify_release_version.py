from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "code-composer"
KIT = SKILL / "kit"
sys.path.insert(0, str(KIT / "src"))

import code_composer  # noqa: E402


def main() -> int:
    version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "1.18.1", f"unexpected release version: {version}"
    assert code_composer.__version__ == version, "package / Skill VERSION mismatch"

    for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert manifest["version"] == version, f"{relative} version mismatch"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"version-v{version}-" in readme, "README version badge mismatch"
    assert f'alt="Version v{version}"' in readme, "README version alt mismatch"

    build_skill = (ROOT / "tools/build_skill.py").read_text(encoding="utf-8")
    assert "VERSION=(SKILL/'VERSION')" in build_skill
    assert "code-composer-skill-v1.17.0.zip" not in build_skill

    notes = ROOT / "docs" / "releases" / f"v{version}.md"
    assert notes.exists(), f"missing release notes: {notes}"

    print(json.dumps({"status": "PASS", "version": version}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
