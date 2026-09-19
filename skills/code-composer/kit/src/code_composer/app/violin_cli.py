from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..performance.violin import ViolinPerformanceError, realize_violin_performance


def build_parser():
    p = argparse.ArgumentParser(
        prog="code-composer-violin",
        description="Plan human-violin fingering and bow realization for monophonic lines and synchronous double stops.",
    )
    p.add_argument("ir_json", type=Path)
    p.add_argument("track_id")
    p.add_argument("out_json", type=Path)
    p.add_argument("--allow-challenging", action="store_true")
    p.add_argument("--max-bow-duration-s", type=float, default=5.0)
    p.add_argument("--contact-point", type=float)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    ir = json.loads(args.ir_json.read_text(encoding="utf-8"))
    config = {
        "strict_comfort": not args.allow_challenging,
        "max_bow_duration_s": args.max_bow_duration_s,
        "default_contact_point": args.contact_point,
    }
    try:
        out = realize_violin_performance(ir, args.track_id, config=config)
    except ViolinPerformanceError as exc:
        raise SystemExit(f"violin planning failed: {exc}") from exc
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(out["violin_performance_report"], indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
