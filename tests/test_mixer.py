import json
from pathlib import Path
import numpy as np

from code_composer.mixer import mix_graph

def run():
    root = Path(__file__).resolve().parents[1]
    ir = json.loads((root/"tests/fixtures/mix_ir.json").read_text(encoding="utf-8"))
    graph = ir["mix"]["graph"]

    sr = 8000
    n = sr * 2
    t = np.arange(n) / sr

    # Synthetic dry tracks make the routing test fast and independent from composition.
    tone = np.sin(2*np.pi*220*t)
    pulse = np.zeros(n)
    pulse[::800] = 1.0

    tracks = {
        "lead": np.stack([tone*0.12, tone*0.11], axis=1),
        "pad": np.stack([tone*0.08, tone*0.09], axis=1),
        "arp": np.stack([tone*0.06, tone*0.055], axis=1),
        "bass": np.stack([np.sin(2*np.pi*55*t)*0.2]*2, axis=1),
        "drums": np.stack([pulse*0.7, pulse*0.7], axis=1),
    }

    a, ra = mix_graph(tracks, sr, graph)
    b, rb = mix_graph(tracks, sr, graph)

    assert np.array_equal(a, b)
    assert ra == rb
    assert ra["buses"]["delay"]["output_rms"] > 0
    assert ra["buses"]["reverb"]["output_rms"] > 0
    assert ra["buses"]["music"]["ducking"]
    assert ra["buses"]["music"]["ducking"][0]["min_gain"] < 0.95
    assert ra["master"]["clipped_sample_ratio"] == 0.0
    assert ra["master"]["output_peak"] <= 0.9200001

    print("test_mixer: OK")
    print({
        "delay_rms": round(ra["buses"]["delay"]["output_rms"], 6),
        "reverb_rms": round(ra["buses"]["reverb"]["output_rms"], 6),
        "music_duck_min_gain": round(ra["buses"]["music"]["ducking"][0]["min_gain"], 4),
        "master_peak": round(ra["master"]["output_peak"], 4),
        "headroom_db": round(ra["master"]["headroom_db"], 3),
    })

if __name__ == "__main__":
    run()


def test_regression():
    run()
