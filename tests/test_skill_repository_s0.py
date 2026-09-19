import json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from _paths import REPO_ROOT, SKILL_ROOT, KIT_ROOT, SOURCE_ROOT

def test_skill_is_self_contained_and_has_progressive_disclosure_surface():
    assert (SKILL_ROOT/"SKILL.md").exists()
    assert (KIT_ROOT/"INDEX.md").exists()
    assert (KIT_ROOT/"SOURCE_MAP.md").exists()
    assert (KIT_ROOT/"EXAMPLE_POLICY.md").exists()
    assert (KIT_ROOT/"src/code_composer").is_dir()
    assert "Do **not** inspect `kit/src/` by default" in (SKILL_ROOT/"SKILL.md").read_text(encoding="utf-8")

def test_skill_has_no_parent_repo_references_or_rich_media_examples():
    forbidden_ext={".wav",".mp3",".flac",".ogg",".m4a",".mid"}
    bad=[]
    for p in SKILL_ROOT.rglob("*"):
        if not p.is_file(): continue
        if p.suffix.lower() in forbidden_ext: bad.append(str(p.relative_to(SKILL_ROOT)))
        if p.suffix.lower() in {".md",".json",".toml",".py",".txt"}:
            if "../" in p.read_text(encoding="utf-8",errors="ignore"):
                bad.append(str(p.relative_to(SKILL_ROOT))+":parent-ref")
    assert bad==[]

def test_examples_teach_operation_never_taste_policy_is_enforced():
    policy=(KIT_ROOT/"EXAMPLE_POLICY.md").read_text(encoding="utf-8")
    assert "Examples teach operation, never taste" in policy
    assert not list((SOURCE_ROOT/"reference"/"examples").glob("*.json"))
    manifest=json.loads((KIT_ROOT/"fixtures/fixture-manifest.json").read_text())
    assert manifest
    assert all(v["synthetic"] is True and v["musical_reference"] is False and v["event_count"]<=8 for v in manifest.values())

def test_surface_maps_all_public_entrypoints():
    surface=json.loads((KIT_ROOT/"surface.json").read_text())
    got={v["entrypoint"] for v in surface["capabilities"].values()}
    assert got=={"code-composer","code-composer-compose","code-composer-midi","code-composer-collab","code-composer-exchange","code-composer-delivery","code-composer-presets","code-composer-violin","code-composer-admittance-fit"}

def test_platform_adapter_manifests_use_standard_manifest_locations():
    codex=REPO_ROOT/".codex-plugin/plugin.json"
    claude=REPO_ROOT/".claude-plugin/plugin.json"
    claude_marketplace=REPO_ROOT/".claude-plugin/marketplace.json"
    agent_marketplace=REPO_ROOT/".agents/plugins/marketplace.json"
    openai=SKILL_ROOT/"agents/openai.yaml"
    icon=SKILL_ROOT/"assets/icon.svg"

    assert json.loads(codex.read_text())["name"]=="code-composer"
    assert json.loads(codex.read_text())["skills"]=="./skills/"
    assert json.loads(claude.read_text())["name"]=="code-composer"
    assert json.loads(claude.read_text())["skills"]=="./skills/"
    assert json.loads(claude_marketplace.read_text())["plugins"][0]["source"]=="./skills/"
    assert json.loads(agent_marketplace.read_text())["plugins"][0]["source"]=={"source":"local","path":"./skills/"}
    assert openai.exists() and icon.exists()
    assert not (REPO_ROOT/".codex_plugins").exists()
    assert not (REPO_ROOT/".claude_plugins").exists()

def test_skill_self_check_passes_when_skill_is_copied_alone():
    with tempfile.TemporaryDirectory() as td:
        lone=Path(td)/"code-composer"
        shutil.copytree(SKILL_ROOT,lone,ignore=shutil.ignore_patterns("__pycache__","*.pyc","*.egg-info",".pytest_cache",".coverage"))
        subprocess.run([sys.executable,str(lone/"kit/scripts/self_check.py")],cwd=lone,check=True,capture_output=True,text=True)



def test_canonical_skill_contains_no_persistent_build_outputs():
    assert not (KIT_ROOT/"build").exists()
    assert not (KIT_ROOT/"dist").exists()
    assert not [p for p in KIT_ROOT.rglob("*.egg-info") if p.is_dir()]

def test_built_skill_contains_no_build_or_cache_artifacts():
    subprocess.run([sys.executable, str(REPO_ROOT/"tools/build_skill.py")], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    artifact=REPO_ROOT/"dist/code-composer-skill-v1.17.0.zip"
    assert artifact.exists()
    with zipfile.ZipFile(artifact) as z:
        names=z.namelist()
    bad=[n for n in names if "/build/" in n or "/dist/" in n or "__pycache__" in n or ".egg-info/" in n or n.endswith(".pyc") or n.endswith("/.coverage")]
    assert bad==[]

def test_plugin_distribution_verifier_passes():
    subprocess.run(
        [sys.executable, str(REPO_ROOT/"tools/verify_plugin_distribution.py")],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

def test_built_plugins_use_root_manifest_layout_and_canonical_icon():
    subprocess.run([sys.executable, str(REPO_ROOT/"tools/build_plugins.py")], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    for platform in ("codex", "claude"):
        artifact=REPO_ROOT/f"dist/code-composer-{platform}-plugin-v1.17.0.zip"
        assert artifact.exists()
        with zipfile.ZipFile(artifact) as z:
            names=set(z.namelist())
        assert f"code-composer/.{platform}-plugin/plugin.json" in names
        assert "code-composer/skills/code-composer/assets/icon.svg" in names
        assert "code-composer/skills/code-composer/agents/openai.yaml" in names
