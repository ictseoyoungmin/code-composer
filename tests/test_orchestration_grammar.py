import json
from pathlib import Path
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.orchestration_analysis import analyze_orchestration

def _fixture():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/"tests/fixtures/topline_ir.json").read_text())

def _section_counts(ir, mode, sparse_role="lead"):
    sid=ir["form"][0]["id"]
    ir["orchestration_grammar"]={
        "enabled":True,
        "default":{"foreground_mode":"none"},
        "sections":{
            sid:{
                "foreground_mode":mode,
                "sparse_role":sparse_role,
                "sparse_density_scale":0.20,
            }
        }
    }
    q=analyze_orchestration(arrange_ir(ir))
    return next(s for s in q["sections"] if s["section_id"]==sid)

def test_orchestration_none():
    c=_section_counts(_fixture(),"none")
    assert c["lead_events"]==0
    assert c["topline_events"]==0

def test_orchestration_lead():
    c=_section_counts(_fixture(),"lead")
    assert c["lead_events"]>0
    assert c["topline_events"]==0

def test_orchestration_topline():
    c=_section_counts(_fixture(),"topline")
    assert c["lead_events"]==0
    assert c["topline_events"]>0

def test_orchestration_sparse_lead():
    full=_section_counts(_fixture(),"lead")["lead_events"]
    sparse=_section_counts(_fixture(),"sparse","lead")["lead_events"]
    assert sparse>0
    assert sparse<full

def test_orchestration_absent_preserves_legacy_behavior():
    a=arrange_ir(_fixture())
    ir2=_fixture()
    ir2["orchestration_grammar"]={"enabled":False}
    b=arrange_ir(ir2)
    assert a["tracks"]==b["tracks"]
