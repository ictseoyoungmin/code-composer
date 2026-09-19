import importlib.util
from pathlib import Path
from _paths import SOURCE_ROOT

from code_composer.analysis import analyze_expressive_qa, compare_expressive_qa
from code_composer.pipeline.service import render_state


ROOT=Path(__file__).resolve().parents[1]


def test_legacy_revision_modules_are_not_importable_or_packaged():
    assert importlib.util.find_spec("code_composer.revision") is None
    assert importlib.util.find_spec("code_composer.revision_runner") is None
    assert not (SOURCE_ROOT/"revision").exists()
    assert not (SOURCE_ROOT/"revision_runner.py").exists()


def test_canonical_revision_surface_is_evidence_only():
    before={
        "issues":[
            {"code":"FLAT_DYNAMICS","severity":"medium","phrase_id":"p"},
        ]
    }
    after={"issues":[]}
    result=compare_expressive_qa(before,after,["FLAT_DYNAMICS"])
    assert result["target_improved"] is True
    assert result["regression_free"] is True
    assert result["improved"] is True


def test_analysis_public_api_exposes_evidence_not_mutators():
    import code_composer.analysis as analysis
    assert analysis.analyze_expressive_qa is analyze_expressive_qa
    assert analysis.compare_expressive_qa is compare_expressive_qa
    for forbidden in (
        "propose_from_issue","apply_proposal","try_proposal",
        "PatchOp","Proposal",
    ):
        assert not hasattr(analysis,forbidden)


def test_pipeline_render_state_remains_the_single_render_analyze_service(tmp_path):
    ir={
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
        "tracks":[{
            "id":"lead","instrument":"lead","source":{"type":"resolved"},
            "events":[{"start_beat":0.0,"duration_beats":0.5,"midi":60,"velocity":0.5}],
        }],
        "mix":{"drive":1.0,"ceiling":0.9},
    }
    state=render_state(ir,tmp_path,"tiny")
    assert state["wav_path"].exists()
    assert state["analysis"]["global"]["clipped_sample_ratio"]==0.0
