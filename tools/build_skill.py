from pathlib import Path
import shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills'/'code-composer'
DIST=ROOT/'dist'; DIST.mkdir(exist_ok=True)

EXCLUDED_PARTS={"__pycache__",".pytest_cache",".mypy_cache",".ruff_cache","build","dist"}
def include_file(p: Path) -> bool:
    rel_parts=p.parts
    if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in rel_parts):
        return False
    if p.name==".coverage" or p.suffix==".pyc":
        return False
    return p.is_file()
out=DIST/'code-composer-skill-v1.17.0.zip'
if out.exists(): out.unlink()
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(SKILL.rglob('*')):
        if include_file(p):
            z.write(p, Path('code-composer')/p.relative_to(SKILL))
print(out)
