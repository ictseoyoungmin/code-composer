from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ..audio.bridge_admittance_fit import fit_era_wav, write_profile, BridgeAdmittanceFitError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fit a compact ERA model from a bridge-admittance impulse-response WAV")
    p.add_argument("input_wav", type=Path)
    p.add_argument("output_json", type=Path)
    p.add_argument("--order", type=int, default=24)
    p.add_argument("--channel", type=int, default=0)
    p.add_argument("--normalize-peak", action="store_true")
    p.add_argument("--source-id", default=None, help="Optional provenance identifier; does not alter the fit")
    return p


def main(argv=None) -> int:
    ns = build_parser().parse_args(argv)
    try:
        source = {"source_id": ns.source_id} if ns.source_id else {}
        profile = fit_era_wav(
            ns.input_wav,
            order=ns.order,
            channel=ns.channel,
            normalize_peak=ns.normalize_peak,
            source=source,
        )
        ns.output_json.parent.mkdir(parents=True, exist_ok=True)
        write_profile(profile, ns.output_json)
    except (BridgeAdmittanceFitError, OSError, ValueError) as exc:
        print(f"code-composer-admittance-fit: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": str(ns.output_json),
        "order": profile["order"],
        "nmse_time": profile.get("fit_metrics", {}).get("nmse_time"),
        "stabilized_poles": profile.get("stabilized_poles", 0),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
