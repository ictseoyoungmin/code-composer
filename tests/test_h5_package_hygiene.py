import importlib.util
import re
from pathlib import Path
import code_composer
from _paths import REPO_ROOT as ROOT, KIT_ROOT, SOURCE_ROOT, SCHEMA_ROOT, PACKAGED_SCHEMA_ROOT

def test_package_version_has_one_declared_source():
    pyproject=(KIT_ROOT/"pyproject.toml").read_text(encoding="utf-8")
    init=(SOURCE_ROOT/"__init__.py").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in pyproject
    assert 'version = {attr = "code_composer.__version__"}' in pyproject
    assert re.search(r'^version\s*=\s*"[^"]+"',pyproject,re.M) is None
    m=re.search(r'^__version__\s*=\s*"([^"]+)"',init,re.M)
    assert m and m.group(1)==code_composer.__version__
    assert re.fullmatch(r"\d+\.\d+\.\d+", code_composer.__version__)
    v116=(ROOT/"docs/history/status/V1.16_DESIGN_STATUS.json").read_text(encoding="utf-8")
    assert '"version": "1.16.0"' in v116 and '"v1.16_final_closed": true' in v116

def test_current_headers_describe_s0_repository_and_preserve_v116_architecture_history():
    assert (ROOT/"README.md").read_text(encoding="utf-8").splitlines()[0]=="# Code Composer"
    assert (ROOT/"docs/STRUCTURE.md").read_text(encoding="utf-8").splitlines()[0]=="# Code Composer repository structure"
    assert (ROOT/"docs/architecture/ARCHITECTURE.md").read_text(encoding="utf-8").splitlines()[0]=="# Code Composer Architecture v1.16"

def test_repository_examples_are_explicitly_maintainer_only_and_not_skill_taste():
    text=(ROOT/"examples/README.md").read_text(encoding="utf-8")
    assert "maintainer-facing" in text
    assert "excluded from the installed agent skill" in text
    assert "Legacy compatibility fixtures" in text

def test_true_orphan_mix_analysis_surface_is_removed():
    assert not (SOURCE_ROOT/"analysis/mix_analysis.py").exists()
    assert not (SOURCE_ROOT/"mix_analysis.py").exists()
    assert importlib.util.find_spec("code_composer.analysis.mix_analysis") is None
    assert importlib.util.find_spec("code_composer.mix_analysis") is None

def test_offline_build_path_is_preserved_in_maintainer_docs():
    text=(ROOT/"docs/BUILD.md").read_text(encoding="utf-8")
    assert "--no-build-isolation" in text and "setuptools>=68" in text and "code_composer.__version__" in text

def test_packaged_reference_surface_contains_schemas_but_no_musical_examples():
    pairs=[]
    for p in sorted(PACKAGED_SCHEMA_ROOT.glob("*.json")):
        pairs.append((SCHEMA_ROOT/p.name,p))
    assert pairs
    for source,packaged in pairs:
        assert source.exists() and source.read_bytes()==packaged.read_bytes()
    assert not list((SOURCE_ROOT/"reference"/"examples").glob("*.json"))
