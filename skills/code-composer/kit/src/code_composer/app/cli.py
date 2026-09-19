import json
import sys
from pathlib import Path
from ..pipeline.service import render_to_files

def main():
    if len(sys.argv) not in (3,4,5):
        print("usage: python -m code_composer.cli <ir.json> <out.wav> [resolved_ir.json] [analysis.json]")
        raise SystemExit(2)
    ir_path,out_path=sys.argv[1],sys.argv[2]
    resolved_path=sys.argv[3] if len(sys.argv)>=4 else None
    analysis_path=sys.argv[4] if len(sys.argv)==5 else None
    ir=json.loads(Path(ir_path).read_text(encoding="utf-8"))
    result=render_to_files(ir,out_path,resolved_path,analysis_path)
    print(json.dumps(result["metrics"],indent=2))

if __name__=="__main__":
    main()
