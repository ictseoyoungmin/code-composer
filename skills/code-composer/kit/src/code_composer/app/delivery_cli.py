import argparse
import json
from pathlib import Path

from ..export.delivery import export_external_delivery
from ..export.midi import DEFAULT_PPQ
from ..pipeline.service import render_to_files


def build_parser():
    p = argparse.ArgumentParser(
        prog="code-composer-delivery",
        description="Render an external DAW delivery: reference mix, full/per-track MIDI, aligned float stems, resolved IR, and manifest.",
    )
    p.add_argument("ir_json", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--ppq", type=int, default=DEFAULT_PPQ)
    p.add_argument("--stem", default=None, help="Base filename for the full-song MIDI.")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    ir = json.loads(args.ir_json.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = args.out_dir / "reference_mix.wav"
    resolved_path = args.out_dir / "resolved_ir.json"
    render_result = render_to_files(ir, wav_path, resolved_path, None)
    delivery = export_external_delivery(
        render_result["resolved"],
        args.out_dir,
        reference_wav=wav_path,
        ppq=args.ppq,
        stem=args.stem,
    )
    manifest = delivery["manifest"]
    print(json.dumps({
        "out_dir": str(args.out_dir),
        "reference_mix": manifest["files"]["reference_mix"],
        "full_midi": manifest["files"]["full_midi"],
        "per_track_midi": len(manifest["tracks"]),
        "stems": len(manifest["tracks"]),
        "stem_sample_format": manifest["stems"]["sample_format"],
        "manifest": Path(delivery["manifest_path"]).name,
        "ppq": args.ppq,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
