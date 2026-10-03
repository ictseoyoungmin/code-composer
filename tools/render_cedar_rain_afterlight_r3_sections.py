#!/usr/bin/env python3
"""R3 production wrapper for Cedar Rain, Afterlight.

Uses the accepted R2 section-tail capture method, but swaps in the R3
multi-string fingerstyle authoring and adds a hard certificate that no exposed
melody peak is realized as an isolated high-string pluck.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import compose_cedar_rain_afterlight_r3 as r3
import render_cedar_rain_afterlight_sections as renderer

# The original production renderer is intentionally reused so sample-rate,
# section-tail, headroom, clipping, and artifact behavior stay unchanged.
renderer.comp = r3


def _output_path(argv):
    if "--output" not in argv:
        raise SystemExit("--output is required")
    return Path(argv[argv.index("--output") + 1])


def main():
    texture = r3.validate_guitar_native_texture()
    renderer.main()

    out = _output_path(sys.argv)
    metrics_path = out / "metrics.json"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    data["revision"] = "SOLO-ACOUSTIC-PROD-R3"
    data["r3_guitar_native_texture"] = texture
    data["human_listening_focus"] = [
        "melody peaks must feel embedded in p-i-m-a arpeggio gestures",
        "reject piano-one-finger high-string impression",
        "reject repetitive identical arpeggio cells",
        "retain one-guitar continuity through bridge/percussive/recap",
    ]
    metrics_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    provenance = out / "PROVENANCE.md"
    if provenance.exists():
        text = provenance.read_text(encoding="utf-8")
        text += (
            "\n## R3 fingerstyle revision\n"
            "- R2 human listening rejected the exposed upper single-string texture as piano-like.\n"
            "- R3 removes the independent upper-note layer and embeds every fingerstyle melody peak inside a 3- or 4-contact multi-string arpeggio gesture.\n"
            "- p/i/m/a-style player authority and physical string/fret identity are explicit.\n"
            "- A hard gate rejects isolated melody peaks and gestures spanning fewer than three physical strings.\n"
        )
        provenance.write_text(text, encoding="utf-8")

    print(json.dumps({"r3_guitar_native_texture": texture}, indent=2))


if __name__ == "__main__":
    main()
