import json
from pathlib import Path

from code_composer.pipeline.service import render_state


def _minimal_ir():
    return {
        "meta":{"global_seed":1,"sample_rate":8000},
        "transport":{"bpm":120,"beats_per_bar":4},
        "tonal":{"root":"C","scale":"major"},
        "form":[{"id":"main","start_bar":0,"bars":1,"energy":1.0}],
        "materials":{"motifs":{"m":{"intervals":[0],"rhythm":[1.0]}},"progressions":{"p":{"degrees":[1]}},"rhythms":{}},
        "instruments":{"lead":{"graph":{
            "oscillators":[{"waveform":"sine","gain":1.0}],
            "envelope":{"attack":0.001,"decay":0.01,"sustain":0.5,"release":0.01},
            "output_gain":0.2
        }}},
        "tracks":[{"id":"lead","instrument":"lead","source":{"type":"resolved"},"events":[
            {"start_beat":0.0,"duration_beats":0.5,"midi":60,"velocity":0.5}
        ]}],
        "mix":{"drive":1.0,"ceiling":0.9},
    }


def test_pipeline_renders_in_process(tmp_path):
    state=render_state(_minimal_ir(),tmp_path,"tiny")
    assert state["wav_path"].exists()
    assert state["resolved"]["tracks"][0]["source"]["type"]=="resolved"
    assert state["analysis"]["global"]["clipped_sample_ratio"]==0.0
