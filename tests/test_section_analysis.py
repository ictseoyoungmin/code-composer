import json
from pathlib import Path
import numpy as np
from code_composer.section_analysis import analyze_sections

def run():
    root = Path(__file__).resolve().parents[1]
    ir = json.loads((root/"tests/fixtures/mix_ir.json").read_text(encoding="utf-8"))

    sr = 4000
    bpm = ir["transport"]["bpm"]
    beats_per_bar = ir["transport"]["beats_per_bar"]
    bar_s = beats_per_bar * 60.0 / bpm
    total_bars = max(s["start_bar"] + s["bars"] for s in ir["form"])
    n = int((total_bars * bar_s + 0.1) * sr)

    # Synthetic section signal that follows the intended energy curve.
    audio = np.zeros((n,2), dtype=np.float64)
    t = np.arange(n)/sr
    for sec in ir["form"]:
        start = int(sec["start_bar"]*bar_s*sr)
        end = int((sec["start_bar"]+sec["bars"])*bar_s*sr)
        amp = 0.20 * sec["energy"]
        tone = np.sin(2*np.pi*220*t[:end-start]) * amp
        audio[start:end,0] = tone
        audio[start:end,1] = tone*0.95

    report = analyze_sections(audio, sr, ir)
    assert set(["global","sections","transitions","energy_correlation","issues"]).issubset(report)
    assert report["energy_correlation"] > 0.97
    assert report["global"]["clipped_sample_ratio"] == 0.0
    assert len(report["sections"]) == len(ir["form"])
    assert all(s["centroid_hz"] > 100 for s in report["sections"].values())

    print("test_section_analysis: OK")
    print({
        "energy_correlation": round(report["energy_correlation"],4),
        "global_peak": round(report["global"]["peak"],4),
        "issue_count": len(report["issues"]),
    })

if __name__ == "__main__":
    run()


def test_regression():
    run()
