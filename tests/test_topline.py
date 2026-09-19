import json
from pathlib import Path
from code_composer.arrange import arrange_ir
from code_composer.topline_analysis import analyze_topline_space, topline_space_score

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/topline_ir.json").read_text(encoding="utf-8"))

    a=arrange_ir(ir)
    b=arrange_ir(ir)
    assert a==b

    top=next(t for t in a["tracks"] if t["id"]=="topline")
    assert len(top["events"]) > 0
    assert all(e["arrangement_role"]=="topline" for e in top["events"])

    report=analyze_topline_space(a)
    assert report["present"] is True
    assert "verse" in report["sections"]
    assert report["sections"]["verse"]["topline_event_count"] > 0
    assert topline_space_score(report) > 0.75

    print("test_topline: OK")
    print(report)
    print("space_score:", round(topline_space_score(report),4))

if __name__=="__main__":
    run()


def test_regression():
    run()
