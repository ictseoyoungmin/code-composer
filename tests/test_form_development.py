import json
from pathlib import Path
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.form_development_analysis import analyze_form_development

def _fixture():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/"tests/fixtures/topline_ir.json").read_text())

def test_development_disabled_preserves_legacy():
    a=arrange_ir(_fixture())
    b_ir=_fixture()
    b_ir["arrangement_development"]={"enabled":False}
    b=arrange_ir(b_ir)
    assert a["tracks"]==b["tracks"]

def test_development_changes_profile_and_rhythm_deterministically():
    ir=_fixture()
    sid=ir["form"][0]["id"]
    ir["arrangement_development"]={
        "enabled":True,
        "families":{"demo":[sid]},
        "sections":{
            sid:{
                "stage":"culminate",
                "lead_density_scale":1.2,
                "lead_fragment_scale":1.0,
                "register_shift_add":12,
                "rhythm_density_scale":1.0,
                "fill_scale":1.0,
            }
        }
    }
    a=arrange_ir(ir); b=arrange_ir(ir)
    assert a==b
    q=analyze_form_development(a)
    assert q["sections"][0]["stage"]=="culminate"
    lead=next(t for t in a["tracks"] if t["id"]=="lead")
    assert lead["events"]
    assert min(e["midi"] for e in lead["events"] if e.get("section_id")==sid) >= 60

def test_family_reports_distinct_development_signatures():
    ir=_fixture()
    # Duplicate the fixture section so the same material can be compared at two stages.
    first=dict(ir["form"][0]); first["id"]="hook_a"; first["start_bar"]=0
    second=dict(ir["form"][0]); second["id"]="hook_b"; second["start_bar"]=first["bars"]
    ir["form"]=[first,second]
    base_profile={
        "energy":0.7,"lead_density":0.55,"lead_octave":4,"lead_fragment":0.8,
        "pad_gain":1.0,"bass":True,"arp":False,"register_shift":0,
        "topline_active":False,
    }
    ir["arrangement"]["profiles"]={"hook_a":dict(base_profile),"hook_b":dict(base_profile)}
    ir["rhythm_engine"]["section_profiles"]={
        "hook_a":{"density":0.55,"kick":.8,"snare":.8,"hat":.7,"fill":.2},
        "hook_b":{"density":0.55,"kick":.8,"snare":.8,"hat":.7,"fill":.2},
    }
    ir["arrangement_development"]={
        "enabled":True,
        "families":{"hook":["hook_a","hook_b"]},
        "sections":{
            "hook_a":{"stage":"establish","lead_density_scale":.75,"rhythm_density_scale":.75},
            "hook_b":{"stage":"develop","lead_density_scale":1.15,"register_shift_add":12,"rhythm_density_scale":1.0},
        }
    }
    q=analyze_form_development(arrange_ir(ir))
    fam=q["families"]["hook"]
    assert fam["distinct_signatures"]>=2
    assert fam["lead_register_delta"] is not None and fam["lead_register_delta"]>6


def test_form_analysis_reports_motif_lineage_when_authored():
    ir=_fixture()
    ir["materials"]["motifs"]["final_variant"]={
        "intervals":[0,2,4,7,4,3,2,1],
        "rhythm":[.5]*8,
        "source_motif_id":"main",
        "identity_floor":.5,
    }
    ir["arrangement_development"]={
        "enabled":True,
        "families":{"arc":["verse","final"]},
        "default":{"stage":"develop"},
        "sections":{
            "verse":{"stage":"establish"},
            "final":{"stage":"culminate","motif_variant":"final_variant"},
        },
    }
    q=analyze_form_development(arrange_ir(ir))
    rows={r["section_id"]:r for r in q["sections"]}
    assert rows["verse"]["motif_id"]=="main"
    assert rows["final"]["motif_id"]=="final_variant"
    assert q["families"]["arc"]["distinct_motifs"]==2
    assert q["families"]["arc"]["minimum_motif_identity"] is not None
