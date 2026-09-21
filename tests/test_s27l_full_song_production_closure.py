import importlib.util
from pathlib import Path

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SCRIPT=Path(__file__).resolve().parents[1]/'tools'/'s27l_full_song_drum_chain.py'
spec=importlib.util.spec_from_file_location('s27l_full_song_drum_chain',SCRIPT)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_s27l_full_form_uses_locked_metal_hihat_chain():
    ir=mod.build_ir()
    assert mod.BARS==12 and mod.BPM==112.0
    assert ir['instruments']['drums']['preset_provenance']['preset_id']==mod.DRUM_PRESET
    assert [x['id'] for x in ir['form']]==['intro','verse','pre','chorus','outro']


def test_s27l_drum_performance_is_four_limb_clean():
    ir=mod.build_ir(); d=next(t for t in ir['tracks'] if t['id']=='drums')
    rep=analyze_drummer_performance({'transport':ir['transport'],'tracks':[d]})
    assert rep['playable'] is True
    assert rep['strained'] is False
    assert rep['issue_counts']=={'high':0,'medium':0,'low':0}
    assert rep['limb_event_counts']=={'hands':118,'right_foot':46,'left_foot':11}


def test_s27l_authored_drum_vocabulary_covers_full_chain():
    events=mod.drum_events()
    kinds={x.get('drum') for x in events if x.get('event_type')=='drum'}
    required={'kick','snare_cross_stick','snare_center','snare_rimshot','snare_ghost',
              'hat_tight_closed','hat_closed','hat_half_open','hat_open','ride','crash',
              'tom_high','tom_mid','tom_floor'}
    assert required <= kinds
    controls=[x for x in events if x.get('event_type')=='drum_control']
    assert len(controls)==11
    assert all(x['control']=='hi_hat_pedal_openness' for x in controls)


def test_s27l_is_deterministic_authored_score_not_runtime_grammar():
    assert mod.drum_events()==mod.drum_events()
    ir=mod.build_ir()
    counts={t['id']:len(t['events']) for t in ir['tracks']}
    assert counts=={'piano':109,'bass':46,'violin':42,'drums':175}
