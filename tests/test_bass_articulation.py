import json
from pathlib import Path
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.bass_analysis import analyze_bass_articulation

def test_bass_articulation():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/topline_ir.json").read_text())
    ir["bass_articulation"]={
        "enabled":True,"ghost_notes":True,"approach_notes":True,
        "base_duration_beats":0.70
    }
    a=arrange_ir(ir); b=arrange_ir(ir)
    assert a==b
    q=analyze_bass_articulation(a)
    kinds=q["articulation_counts"]
    assert kinds.get("accent",0)>0
    assert kinds.get("legato",0)+kinds.get("short",0)>0
    assert kinds.get("ghost",0)>0
    assert kinds.get("approach",0)>0
    assert q["velocity_min"] < q["velocity_max"]
