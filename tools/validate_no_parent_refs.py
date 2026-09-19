from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]/'skills'/'code-composer'
pat=re.compile(r'(?:^|[\s'"`(])\.\./')
bad=[]
for p in ROOT.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.md','.json','.toml','.py','.txt'}:
        text=p.read_text(encoding='utf-8',errors='ignore')
        if pat.search(text): bad.append(str(p.relative_to(ROOT)))
if bad: raise SystemExit('parent refs: '+', '.join(bad))
print('PASS: no parent references')
