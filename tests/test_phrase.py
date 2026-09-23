import json
from pathlib import Path
from code_composer.phrase import PhraseConfig, compose_phrase, motif_identity_score
from code_composer.phrase_analysis import analyze_phrase

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/phrase_ir.json").read_text(encoding="utf-8"))
    cfg=PhraseConfig(
        bars=12, beats_per_bar=4, base_degree=1, octave=4,
        density=.82, tension=.72, cadence_strength=.9, max_leap_semitones=7
    )
    a=compose_phrase(ir["materials"],ir["tonal"],ir["meta"]["global_seed"],"main",cfg,"test")
    b=compose_phrase(ir["materials"],ir["tonal"],ir["meta"]["global_seed"],"main",cfg,"test")
    assert a==b
    qa=analyze_phrase(a["events"])
    assert qa["event_count"] > 20
    assert qa["cadence_resolves"] is True
    assert qa["large_leap_ratio"] < 0.25
    assert set(["opening","development","tension","cadence"]).issubset(set(qa["phase_counts"]))
    base=ir["materials"]["motifs"]["main"]["intervals"]
    assert motif_identity_score(base,base)==1.0
    print("test_phrase: OK")
    print(qa)

if __name__=="__main__":
    run()



def test_compose_phrase_preserves_authored_rhythm_before_expression_gate():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/phrase_ir.json").read_text(encoding="utf-8"))
    cfg=PhraseConfig(
        bars=2, beats_per_bar=4, base_degree=1, octave=4,
        density=1.0, tension=.6, cadence_strength=.85, max_leap_semitones=7
    )
    out=compose_phrase(ir["materials"],ir["tonal"],123,"main",cfg,"gate-regression")
    first=out["events"][0]
    authored=ir["materials"]["motifs"]["main"]["rhythm"][0]
    assert first["duration_beats"]==authored


def test_regression():
    run()
