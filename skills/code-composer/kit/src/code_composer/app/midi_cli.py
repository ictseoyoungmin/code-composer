import argparse
import json
from pathlib import Path

from ..export.midi import DEFAULT_PPQ, export_midi


def build_parser():
    p = argparse.ArgumentParser(
        prog="code-composer-midi",
        description="Export canonical Code Composer Music IR to deterministic Type 1 MIDI.",
    )
    p.add_argument("ir_json", type=Path)
    p.add_argument("out_mid", type=Path)
    p.add_argument("--ppq", type=int, default=DEFAULT_PPQ)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    ir = json.loads(args.ir_json.read_text(encoding="utf-8"))
    result = export_midi(ir, args.out_mid, ppq=args.ppq, resolve=True)
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
