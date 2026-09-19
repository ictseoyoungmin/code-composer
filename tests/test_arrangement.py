import json
from pathlib import Path
from code_composer.arrange import arrange_ir
from code_composer.arrangement_analysis import analyze_arrangement, section_contrast_score

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/arrangement_ir.json").read_text(encoding="utf-8"))
    a=arrange_ir(ir)
    b=arrange_ir(ir)
    assert a==b

    report=analyze_arrangement(a)
    needed={"intro","build","main","break","final"}
    assert needed.issubset(set(report))

    assert "bass" not in report["intro"]["roles_present"]
    assert "arp" not in report["intro"]["roles_present"]
    assert "bass" in report["main"]["roles_present"]
    assert "arp" in report["main"]["roles_present"]
    assert report["final"]["lead_mean_pitch"] > report["intro"]["lead_mean_pitch"]
    assert report["main"]["event_count"] > report["intro"]["event_count"]
    assert report["break"]["event_count"] < report["main"]["event_count"]
    assert section_contrast_score(report) > 0.25

    print("test_arrangement: OK")
    print(json.dumps(report, indent=2))
    print("contrast_score:", round(section_contrast_score(report),4))

if __name__=="__main__":
    run()


def test_regression():
    run()
