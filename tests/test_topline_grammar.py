import json
from pathlib import Path
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.topline_grammar_analysis import analyze_topline_grammar

def test_topline_phrase_grammar():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/topline_ir.json").read_text())
    ir["topline_grammar"]={
        "enabled":True,
        "phrase_bars":2,
        "breathing_beats":0.35,
        "pickup_beats":0.25,
        "response_scale_steps":-1,
        "tension_scale_steps":1,
    }
    a=arrange_ir(ir); b=arrange_ir(ir)
    assert a==b
    q=analyze_topline_grammar(a)
    assert q["role_counts"].get("call",0)+q["role_counts"].get("tension_call",0)>0
    assert q["role_counts"].get("response",0)+q["role_counts"].get("release_response",0)>0
    assert q["pickup_count"]>0
    assert q["hook_anchor_count"]>0
    assert q["mean_phrase_gap_beats"]>0
    assert 0.0 <= q["mean_call_response_contour_similarity"] <= 1.0
