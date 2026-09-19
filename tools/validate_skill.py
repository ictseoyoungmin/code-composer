from pathlib import Path
import json, re, subprocess, sys, tempfile, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills'/'code-composer'
KIT=SKILL/'kit'

def run(*args, cwd=None):
    subprocess.run(list(args), cwd=cwd or ROOT, check=True)

def main():
    run(sys.executable, str(KIT/'scripts/self_check.py'))
    # Ensure no repository-parent references are needed: copy the skill alone and validate there.
    with tempfile.TemporaryDirectory() as td:
        lone=Path(td)/'code-composer'; shutil.copytree(SKILL,lone)
        run(sys.executable, str(lone/'kit/scripts/self_check.py'), cwd=lone)
        # Syntax-compile the isolated source.
        run(sys.executable, '-m', 'compileall', '-q', str(lone/'kit/src'))
    surface=json.loads((KIT/'surface.json').read_text())
    assert set(surface['capabilities'])=={'render','compose','midi','collab_bundle','exchange','delivery','presets','violin_performance','bridge_admittance_fit'}
    print('PASS: skill validation')
if __name__=='__main__': main()
