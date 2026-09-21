import copy
import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event, resolve_hi_hat_pedal_openness
from code_composer.render import _render_dry_track
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000
BPM=120.0
BEAT_S=60.0/BPM
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_persistent_hihat'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def _ev(kind,beat,vel=.84,dur=.12):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}


def _ctrl(start,duration,points):
    return {
        'event_type':'drum_control','control':'hi_hat_pedal_openness',
        'start_beat':float(start),'duration_beats':float(duration),
        'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points],
    }


def _render_track(preset,events,*,room=False,n_s=3.0,seed=272001):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch)
        patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':seed},'instruments':{'drums':patch}}
    track={'id':'drums','instrument':'drums','events':list(events)}
    return _render_dry_track(ir,track,int(n_s*SR),SR,BEAT_S,graph_mode=True)


def _window(x,a,b):
    return x[int(a*SR):int(b*SR)]


def test_s27j_preset_only_upgrades_s27i_hihat_state_model():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    a=get_preset(OLD)['patch']['drum_graph']
    b=get_preset(NEW)['patch']['drum_graph']
    assert {k:v for k,v in b.items() if k!='hi_hat_state'} == {k:v for k,v in a.items() if k!='hi_hat_state'}
    assert b['hi_hat_state']['closure']==a['hi_hat_state']['closure']
    assert b['hi_hat_state']['continuous']==a['hi_hat_state']['continuous']
    assert b['hi_hat_state']['model']=='authored_persistent_openness_v3'


def test_s27j_no_control_is_byte_exact_to_s27i_track_render():
    events=[_ev('hat_open',0,.86),_ev('kick',0,.92),_ev('snare_center',1,.90,.10),_ev('hat_half_open',1.5,.78)]
    assert _sha(_render_track(OLD,events)) == _sha(_render_track(NEW,events))


def test_s27j_direct_hit_api_without_state_override_is_byte_exact_to_s27i():
    a=materialize_preset(OLD,role='drums')
    b=materialize_preset(NEW,role='drums')
    for i,kind in enumerate(('hat_tight_closed','hat_closed','hat_half_open','hat_open','hat_pedal','hat_foot_splash','kick','snare_rimshot','ride')):
        x=render_drum_event(kind,.12,SR,.84,seed=550+i,patch=a)
        y=render_drum_event(kind,.12,SR,.84,seed=550+i,patch=b)
        assert _sha(x)==_sha(y),kind


def test_s27j_completed_curve_persists_to_later_strike_and_changes_source_from_onset():
    curve=_ctrl(0,.5,[(0,1),(.5,.22)])
    hit=_ev('hat_open',1.0,.88)
    yi=_render_track(OLD,[curve,hit],n_s=2.0)
    yj=_render_track(NEW,[curve,hit],n_s=2.0)
    start=int(1.0*BEAT_S*SR)
    # S27-I forgot the completed curve at the later strike; S27-J couples it.
    assert np.max(np.abs(yi[start:start+int(.025*SR)]-yj[start:start+int(.025*SR)])) > 1e-4
    assert _rms(_window(yj,.70,1.05)) < _rms(_window(yi,.70,1.05))*.75


def test_s27j_pedal_state_resolver_is_persistent_and_piecewise_linear():
    events=[_ctrl(0,1,[(0,1),(.5,.6),(1,.2)]),_ctrl(2,.5,[(0,.2),(.5,.8)])]
    assert abs(resolve_hi_hat_pedal_openness(events,.25)-.8)<1e-12
    assert abs(resolve_hi_hat_pedal_openness(events,1.5)-.2)<1e-12
    assert abs(resolve_hi_hat_pedal_openness(events,2.25)-.5)<1e-12
    assert abs(resolve_hi_hat_pedal_openness(events,3.0)-.8)<1e-12


def test_s27j_more_closed_persistent_state_shortens_and_darkens_same_open_hit():
    hit=_ev('hat_open',1.0,.88)
    open_ev=[_ctrl(0,.5,[(0,1),(.5,.90)]),hit]
    half_ev=[_ctrl(0,.5,[(0,1),(.5,.48)]),hit]
    closed_ev=[_ctrl(0,.5,[(0,1),(.5,.10)]),hit]
    yo=_render_track(NEW,open_ev,n_s=2)
    yh=_render_track(NEW,half_ev,n_s=2)
    yc=_render_track(NEW,closed_ev,n_s=2)
    # Absolute timeline after hit onset: 1 beat = 0.5 s.  Contact-state
    # interpolation is not a gain ladder: half-open may have stronger chatter.
    # The invariant is progressively shorter residual decay relative to onset.
    def tail_ratio(y):
        return _rms(_window(y,.68,.82))/_rms(_window(y,.50,.53))
    assert tail_ratio(yo) > tail_ratio(yh) > tail_ratio(yc)
    assert tail_ratio(yo) > tail_ratio(yc)*10.0


def test_s27j_pedal_control_cannot_make_authored_closed_hit_more_open():
    hit=_ev('hat_closed',1.0,.84)
    base=_render_track(NEW,[hit],n_s=1.5)
    open_pedal=_render_track(NEW,[_ctrl(0,.5,[(0,1),(.5,.95)]),hit],n_s=1.5)
    assert _sha(base)==_sha(open_pedal)


def test_s27j_future_curve_preserves_precontact_audio_then_uses_s27i_tail_logic():
    hit=_ev('hat_open',0,.88)
    curve=_ctrl(.5,.5,[(0,1),(.5,0)])
    a=_render_track(OLD,[hit,curve],n_s=1.5)
    b=_render_track(NEW,[hit,curve],n_s=1.5)
    pre=int((.5*BEAT_S-.005)*SR)
    assert np.max(np.abs(a[:pre]-b[:pre]))==0.0


def test_s27j_persistent_state_does_not_duck_unrelated_kick():
    curve=_ctrl(0,.5,[(0,1),(.5,.18)])
    hat=[curve,_ev('hat_open',1,.86)]
    combo=hat+[_ev('kick',1,.94)]
    yh=_render_track(NEW,hat,n_s=1.5)
    yc=_render_track(NEW,combo,n_s=1.5)
    yk=_render_track(NEW,[_ev('kick',1,.94)],n_s=1.5)
    assert np.max(np.abs((yc-yh)-yk)) < 1e-12


def test_s27j_four_limb_evidence_remains_explicit_and_playable():
    events=[
        _ctrl(0,.5,[(0,1),(.5,.25)]),_ev('hat_open',1,.82),_ev('kick',1,.92),
        _ev('snare_center',2,.90,.10),_ctrl(2.5,.5,[(0,.25),(.5,.78)]),_ev('hat_open',3.25,.80),
    ]
    ir={'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':events}]}
    rep=analyze_drummer_performance(ir)
    assert rep['playable'] is True and rep['strained'] is False
    assert rep['issue_counts']=={'high':0,'medium':0,'low':0}
    assert rep['limb_event_counts']=={'hands':3,'right_foot':1,'left_foot':2}
