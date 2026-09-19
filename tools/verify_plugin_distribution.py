from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "code-composer"
VERSION = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
SKILL_SOURCE = "./skills/"
ICON_PATH = "./skills/code-composer/assets/icon.svg"


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def require(relative: str):
    path = ROOT / relative
    assert path.exists(), f"missing required plugin-distribution path: {relative}"
    return path


def assert_identity(plugin: dict, label: str):
    assert plugin["name"] == "code-composer", f"{label} name"
    assert plugin["version"] == VERSION, f"{label} version"
    assert plugin["license"] == "AGPL-3.0-only", f"{label} license"
    assert plugin["homepage"] == "https://github.com/ictseoyoungmin/code-composer", f"{label} homepage"
    assert plugin["repository"] == "https://github.com/ictseoyoungmin/code-composer", f"{label} repository"
    assert plugin["author"]["name"] == "ictseoyoungmin", f"{label} author"


def main():
    required = [
        "skills/code-composer/SKILL.md",
        "skills/code-composer/agents/openai.yaml",
        "skills/code-composer/assets/icon.svg",
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".agents/plugins/marketplace.json",
    ]
    for relative in required:
        require(relative)

    assert not (ROOT / ".codex_plugins").exists(), "legacy .codex_plugins layout must remain absent"
    assert not (ROOT / ".claude_plugins").exists(), "legacy .claude_plugins layout must remain absent"

    codex = read_json(".codex-plugin/plugin.json")
    claude = read_json(".claude-plugin/plugin.json")
    claude_marketplace = read_json(".claude-plugin/marketplace.json")
    agent_marketplace = read_json(".agents/plugins/marketplace.json")

    assert_identity(codex, "Codex plugin")
    assert_identity(claude, "Claude plugin")

    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"^name:\s*code-composer\s*$", skill, re.MULTILINE)
    assert re.search(r"^description:\s*\S.+$", skill, re.MULTILINE)

    assert codex["skills"] == SKILL_SOURCE
    interface = codex["interface"]
    assert interface["displayName"] == "Code Composer"
    assert interface["developerName"] == "ictseoyoungmin"
    assert interface["category"] == "Creative Tools"
    assert interface["websiteURL"] == "https://github.com/ictseoyoungmin/code-composer"
    assert interface["brandColor"] == "#0D1422"
    assert interface["composerIcon"] == ICON_PATH
    assert interface["logo"] == ICON_PATH
    require(interface["composerIcon"].removeprefix("./"))
    require(interface["logo"].removeprefix("./"))

    assert claude["skills"] == SKILL_SOURCE
    assert claude_marketplace["name"] == "code-composer"
    assert claude_marketplace["owner"]["name"] == "ictseoyoungmin"
    assert len(claude_marketplace["plugins"]) == 1
    assert claude_marketplace["plugins"][0]["source"] == SKILL_SOURCE

    assert agent_marketplace["name"] == "code-composer"
    assert agent_marketplace["interface"]["displayName"] == "Code Composer"
    assert len(agent_marketplace["plugins"]) == 1
    agent_plugin = agent_marketplace["plugins"][0]
    assert agent_plugin["source"] == {"source": "local", "path": SKILL_SOURCE}
    assert agent_plugin["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert agent_plugin["category"] == "Creative Tools"

    openai = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for token in (
        'display_name: "Code Composer"',
        'icon_small: "./assets/icon.svg"',
        'icon_large: "./assets/icon.svg"',
        'brand_color: "#0D1422"',
        "allow_implicit_invocation: true",
    ):
        assert token in openai, f"agents/openai.yaml missing {token}"

    print(json.dumps({
        "status": "PASS",
        "version": VERSION,
        "skill_source": SKILL_SOURCE,
        "icon": ICON_PATH,
        "adapters": ["codex", "claude", "agents"],
    }, indent=2))


if __name__ == "__main__":
    main()
