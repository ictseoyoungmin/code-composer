from pathlib import Path
import json, sys

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inspect_ir.py IR.json", file=sys.stderr); return 2
    data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps({
        "title": data.get("meta",{}).get("title"),
        "bpm": data.get("transport",{}).get("bpm"),
        "sections": [s.get("id") for s in data.get("form",[])],
        "tracks": [t.get("id") for t in data.get("tracks",[])],
        "events": sum(len(t.get("events",[])) for t in data.get("tracks",[])),
    }, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
