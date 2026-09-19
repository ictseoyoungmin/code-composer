from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "code-composer"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
VERSION = (SKILL / "VERSION").read_text(encoding="utf-8").strip()

ADAPTERS = {
    "codex": ROOT / ".codex-plugin",
    "claude": ROOT / ".claude-plugin",
}

EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist"}


def include_file(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in path.parts):
        return False
    if path.name == ".coverage" or path.suffix == ".pyc":
        return False
    return path.is_file()


for platform, source in ADAPTERS.items():
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "code-composer"
        stage.mkdir(parents=True)
        shutil.copytree(source, stage / source.name)
        shutil.copytree(
            SKILL,
            stage / "skills" / "code-composer",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", ".pytest_cache", ".coverage"),
        )

        out = DIST / f"code-composer-{platform}-plugin-v{VERSION}.zip"
        if out.exists():
            out.unlink()

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if include_file(path):
                    archive.write(path, Path("code-composer") / path.relative_to(stage))
        print(out)
