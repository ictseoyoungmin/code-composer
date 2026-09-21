from copy import deepcopy

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance


def _ir(events, bpm=120):
    return {
        "transport": {"bpm": bpm, "beats_per_bar": 4},
        "tracks": [{
            "id": "drums",
            "instrument": "drums",
            "events": [
                {
                    "event_type": "drum",
                    "drum": drum,
                    "start_beat": beat,
                    "duration_beats": 0.05,
                    "velocity": vel,
                    "section_id": "main",
                }
                for beat, drum, vel in events
            ],
        }],
    }


def _codes(report):
    return [i["code"] for i in report["issues"]]


def test_actual_eighth_note_groove_is_structurally_playable():
    events=[]
    for step in range(8):
        beat=step*0.5
        events.append((beat,"hat_closed",0.68 if step%2 else 0.76))
    events += [
        (0.0,"kick",0.88),(1.0,"snare_center",0.90),
        (2.0,"kick",0.86),(3.0,"snare_center",0.92),
        (2.5,"kick",0.72),
    ]
    report=analyze_drummer_performance(_ir(events))
    assert report["playable"] is True
    assert report["issue_counts"]["high"] == 0
    assert report["limb_event_counts"] == {"hands":10,"right_foot":3,"left_foot":0}
    assert {a["limb"] for a in report["assignments"] if a["drum"]=="snare_center"} <= {"left_hand","right_hand"}


def test_three_exact_simultaneous_stick_hits_exceed_two_hand_capacity():
    report=analyze_drummer_performance(_ir([
        (1.0,"hat_closed",0.8),(1.0,"snare_rimshot",0.95),(1.0,"crash",0.95),
    ]))
    assert report["playable"] is False
    assert "DRUM_HAND_CAPACITY" in _codes(report)
    issue=next(i for i in report["issues"] if i["code"]=="DRUM_HAND_CAPACITY")
    assert issue["required_hands"]==3
    assert issue["available_hands"]==2


def test_same_foot_duplicate_events_are_hard_capacity_evidence():
    report=analyze_drummer_performance(_ir([
        (1.0,"kick",0.8),(1.0,"kick",0.7),
        (2.0,"hat_pedal",0.7),(2.0,"hat_foot_splash",0.8),
    ]))
    codes=_codes(report)
    assert "DRUM_RIGHT_FOOT_CAPACITY" in codes
    assert "DRUM_LEFT_FOOT_CAPACITY" in codes
    assert report["playable"] is False


def test_two_hands_plus_two_feet_can_coexist_on_same_downbeat():
    report=analyze_drummer_performance(_ir([
        (0.0,"snare_center",0.9),(0.0,"crash",0.95),
        (0.0,"kick",0.92),(0.0,"hat_pedal",0.65),
    ]))
    assert report["playable"] is True
    assert report["issue_counts"]["high"] == 0
    limbs={a["limb"] for a in report["assignments"]}
    assert {"left_hand","right_hand","left_foot","right_foot"} <= limbs


def test_fast_three_hit_burst_is_strain_not_automatic_rewrite_or_hard_rejection():
    report=analyze_drummer_performance(_ir([
        (0.0,"snare_ghost",0.35),
        (0.02,"snare_ghost",0.35),
        (0.04,"snare_center",0.75),
    ], bpm=120), burst_window_ms=25.0)
    assert report["playable"] is True
    assert any(i["code"]=="DRUM_HAND_BURST_STRAIN" and i["severity"]=="medium" for i in report["issues"])


def test_descending_high_mid_floor_fill_can_be_alternated_between_hands():
    report=analyze_drummer_performance(_ir([
        (2.0,"tom_high",0.82),(2.25,"tom_high",0.78),
        (2.5,"tom_mid",0.84),(2.75,"tom_mid",0.80),
        (3.0,"tom_floor",0.90),(3.25,"tom_floor",0.86),
    ]))
    assert report["playable"] is True
    assert report["issue_counts"]["high"] == 0
    toms=[a for a in report["assignments"] if a["family"].startswith("tom_")]
    assert len(toms)==6
    assert {a["limb"] for a in toms}=={"left_hand","right_hand"}


def test_analysis_is_evidence_only_and_does_not_mutate_ir():
    ir=_ir([(0.0,"kick",0.9),(1.0,"snare_center",0.9),(1.0,"hat_closed",0.7)])
    before=deepcopy(ir)
    report=analyze_drummer_performance(ir)
    assert ir==before
    assert report["semantics"]=="evidence_only_no_event_mutation"


def test_assignments_are_deterministic():
    ir=_ir([
        (0.0,"hat_closed",0.7),(0.0,"kick",0.9),
        (1.0,"snare_center",0.9),(1.5,"tom_high",0.75),
        (2.0,"tom_mid",0.78),(2.5,"tom_floor",0.85),(3.0,"ride",0.72),
    ])
    assert analyze_drummer_performance(ir)==analyze_drummer_performance(ir)


def test_pipeline_analysis_surfaces_drummer_performance_report(tmp_path):
    from code_composer.pipeline.service import render_to_files
    ir={
        "meta":{"global_seed":1,"sample_rate":8000},
        "transport":{"bpm":120,"beats_per_bar":4},
        "tonal":{"root":"C","scale":"major"},
        "form":[{"id":"main","start_bar":0,"bars":1,"energy":1.0}],
        "materials":{"motifs":{"m":{"intervals":[0],"rhythm":[1.0]}},"progressions":{"p":{"degrees":[1]}},"rhythms":{}},
        "instruments":{"drums":{"kind":"percussion"}},
        "tracks":[{"id":"drums","instrument":"drums","source":{"type":"resolved"},"events":[
            {"event_type":"drum","drum":"kick","start_beat":0.0,"duration_beats":0.05,"velocity":0.8,"section_id":"main"},
            {"event_type":"drum","drum":"hat","start_beat":0.0,"duration_beats":0.05,"velocity":0.6,"section_id":"main"},
            {"event_type":"drum","drum":"snare","start_beat":1.0,"duration_beats":0.05,"velocity":0.8,"section_id":"main"},
            {"event_type":"drum","drum":"hat","start_beat":1.0,"duration_beats":0.05,"velocity":0.6,"section_id":"main"},
        ]}],
        "mix":{"drive":1.0,"ceiling":0.9},
    }
    result=render_to_files(ir,tmp_path/"x.wav",analysis_path=tmp_path/"analysis.json")
    report=result["analysis"]["drummer_performance"]
    assert report["playable"] is True
    assert report["issue_count"]==0
    assert [i for i in result["analysis"]["issues"] if i.get("source")=="drummer_performance"]==[]
