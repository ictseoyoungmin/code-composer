import copy
import pytest

from code_composer.core.ir import validate_ir as validate_core_ir
from code_composer.ir import validate_ir as validate_legacy_ir
from code_composer.pipeline.validation import validate_ir as validate_pipeline_ir
from code_composer.mix.mixer import MixGraphError


def _ir_with_invalid_mix():
    return {
        "meta":{"global_seed":1,"sample_rate":8000},
        "transport":{"bpm":120,"beats_per_bar":4},
        "tonal":{"root":"C","scale":"major"},
        "form":[{"id":"main","start_bar":0,"bars":1,"energy":1.0}],
        "materials":{
            "motifs":{"m":{"intervals":[0],"rhythm":[1.0]}},
            "progressions":{"p":{"degrees":[1]}},
            "rhythms":{},
        },
        "instruments":{"lead":{"graph":{
            "oscillators":[{"waveform":"sine","gain":1.0}],
            "envelope":{"attack":0.001,"decay":0.01,"sustain":0.5,"release":0.01},
            "output_gain":0.2,
        }}},
        "tracks":[{"id":"lead","instrument":"lead","source":{"type":"resolved"},"events":[
            {"start_beat":0.0,"duration_beats":0.5,"midi":60,"velocity":0.5}
        ]}],
        "mix":{"graph":{
            "tracks":{"lead":{"gain":1.0,"pan":0.0,"output":"missing_bus","sends":{}}},
            "buses":{"music":{"kind":"group","gain":1.0,"output":"master","fx":[]}},
            "sidechains":[],
            "master":{"gain":1.0,"fx":[]},
        }},
    }


def test_aggregate_validation_preserves_domain_split():
    ir=_ir_with_invalid_mix()
    # Core owns structural/music-IR validation only.
    validate_core_ir(ir)
    # Aggregate/legacy validation must still reject the invalid mix graph.
    with pytest.raises(MixGraphError):
        validate_pipeline_ir(ir)
    with pytest.raises(MixGraphError):
        validate_legacy_ir(ir)


def test_aggregate_validation_accepts_fixed_mix():
    ir=_ir_with_invalid_mix()
    ir["mix"]["graph"]["tracks"]["lead"]["output"]="music"
    validate_pipeline_ir(ir)
    validate_legacy_ir(ir)
