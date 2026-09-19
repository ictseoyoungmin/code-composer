import json
from pathlib import Path
from code_composer.arrange import arrange_ir
from code_composer.rhythm_analysis import analyze_rhythm, rhythmic_contrast

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/rhythm_ir.json").read_text(encoding="utf-8"))
    a=arrange_ir(ir)
    b=arrange_ir(ir)
    assert a==b

    report=analyze_rhythm(a)
    sections=report["sections"]
    assert set(["intro","build","main","break","final"]).issubset(sections)
    assert sections["main"]["events"] > sections["build"]["events"]
    assert sections["main"]["events"] > sections["break"]["events"]
    assert sections["final"]["events"] >= sections["main"]["events"]
    assert sections["final"]["fills"] > 0
    assert report["bass_kick_coupling"]["main"] >= 0.5
    assert report["bass_kick_coupling"]["final"] >= 0.5
    assert rhythmic_contrast(report) > 0.15

    print("test_rhythm: OK")
    print(json.dumps(report, indent=2))
    print("rhythmic_contrast:", round(rhythmic_contrast(report),4))

if __name__=="__main__":
    run()


def test_regression():
    run()
