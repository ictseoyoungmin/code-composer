from copy import deepcopy
from pathlib import Path
import numpy as np

from code_composer.audio.engines import engine_for_patch, registered_engines
from code_composer.audio.instrument import synth_patch_note
from code_composer.presets import list_presets, materialize_preset
from code_composer.render import render


def _patch():
    return materialize_preset("resonant_pluck.zither_bright", role="zither")


def _rms(x):
    x=np.asarray(x,dtype=float)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.0


def test_cr08_resonant_engine_and_preset_surface():
    assert "resonant_pluck" in registered_engines()
    metas={x["preset_id"]:x for x in list_presets()}
    assert metas["resonant_pluck.zither_bright"]["engine"]=="resonant_pluck"
    patch=_patch()
    engine=engine_for_patch(patch)
    assert engine.name=="resonant_pluck"
    assert engine.capabilities().extended_tail is True
    assert abs(engine.tail_seconds(patch)-.72)<1e-12


def test_cr08_authored_gate_is_not_sample_buffer_length():
    sr=24000
    gate=.18
    patch=_patch()
    a=synth_patch_note(66,gate,sr,patch,velocity=.7)
    b=synth_patch_note(66,gate,sr,patch,velocity=.7)
    assert np.array_equal(a,b)
    assert len(a)==int((gate+.72)*sr)
    post=a[int(gate*sr):int((gate+.22)*sr)]
    late=a[int((gate+.52)*sr):int((gate+.68)*sr)]
    assert _rms(post) > 0.002
    assert _rms(late) < _rms(post)*.55
    assert np.isfinite(a).all()
    assert float(np.max(np.abs(a))) <= 1.0


def test_cr08_gate_cut_diagnostic_removes_only_resonator_tail():
    sr=24000
    gate=.18
    patch=_patch()
    resonant=synth_patch_note(66,gate,sr,patch,velocity=.7)
    cut=deepcopy(patch)
    cut["resonant_pluck_graph"]["natural_tail_s"]=0.0
    clipped=synth_patch_note(66,gate,sr,cut,velocity=.7)
    assert len(clipped)==int(gate*sr)
    assert np.array_equal(resonant[:len(clipped)], clipped) is False
    padded=np.zeros_like(resonant)
    padded[:len(clipped)]=clipped
    assert _rms(resonant[int(gate*sr):int((gate+.20)*sr)]) > _rms(padded[int(gate*sr):int((gate+.20)*sr)]) + .001


def test_cr08_renderer_allocates_engine_tail_past_last_note(tmp_path):
    patch=_patch()
    ir={
        "meta":{"title":"cr08-probe","sample_rate":24000,"global_seed":8},
        "transport":{"bpm":120.0,"beats_per_bar":4},
        "tonal":{"root":"F#","scale":"natural_minor"},
        "form":[{"id":"a","start_bar":0,"bars":1}],
        "materials":{"motifs":{},"progressions":{},"rhythms":{}},
        "instruments":{"z":patch},
        "tracks":[{
            "id":"z","instrument":"z","source":{"type":"resolved"},
            "events":[{"start_beat":3.5,"duration_beats":.2,"midi":66,"velocity":.65,"section_id":"a"}]
        }],
        "mix":{"tail_seconds":.05,"graph":{
            "tracks":{"z":{"gain":.5,"pan":0.0,"output":"music","sends":{"room":0.0}}},
            "buses":{"music":{"kind":"group","gain":1.0,"output":"master","fx":[]},"room":{"kind":"return","gain":0.0,"output":"master","fx":[]}},
            "sidechains":[],"master":{"gain":1.0,"fx":[]}
        }}
    }
    audio,sr,_=render(ir,tmp_path/"probe.wav")
    gate_end=(3.5+.2)*.5
    post=audio[int((gate_end+.04)*sr):int((gate_end+.24)*sr)]
    assert len(audio) >= int((gate_end+.70)*sr)
    assert _rms(post) > .0005


def test_cr08_invalid_tail_contract_is_rejected():
    patch=_patch()
    patch["resonant_pluck_graph"]["natural_tail_s"]=9.0
    import pytest
    with pytest.raises(Exception):
        engine_for_patch(patch).validate_authoring_patch("zither",patch)
