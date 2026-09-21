import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.drum_kit import integrate_drum_kit
from code_composer.audio.engines import engine_for_patch

SR=24000
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated'
S26='drums.s19_core_powerful_room'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def _fixed_dry():
    n=int(1.25*SR)
    dry=np.zeros((n,2),dtype=np.float64)
    t=np.arange(int(.09*SR),dtype=np.float64)/SR
    burst=(np.sin(2*np.pi*220*t)*.06 + np.sin(2*np.pi*1700*t)*.025)*np.exp(-t/.028)
    dry[:len(burst),0]=burst
    dry[:len(burst),1]=burst*.94
    return dry


def _room_report(kind, velocity=.84):
    p=materialize_preset(NEW,role='drums')
    cfg=p['drum_graph']['kit_integration']
    ev=[{'event_type':'drum','start_beat':0.0,'duration_beats':.1,'drum':kind,'velocity':velocity}]
    _,rep=integrate_drum_kit(_fixed_dry(),SR,ev,.5,cfg)
    return rep


def test_s27g_preset_registered_and_only_integration_changes_from_s27d_source_graph():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    a=get_preset(OLD)['patch']['drum_graph']
    b=get_preset(NEW)['patch']['drum_graph']
    for key in a:
        if key!='kit_integration':
            assert b[key] == a[key]
    assert b['kit_integration']['overhead_predelay_ms'] > 0
    assert b['kit_integration']['articulation_room_weights']['snare_rimshot'] > b['kit_integration']['articulation_room_weights']['snare_ghost']


def test_s27g_direct_event_sources_are_byte_exact_to_s27d_before_track_integration():
    a=materialize_preset(OLD,role='drums')
    b=materialize_preset(NEW,role='drums')
    kinds=(
        'kick','ride','crash','hat_closed','hat_open','hat_pedal',
        'snare_center','snare_ghost','snare_rimshot','snare_cross_stick',
        'tom_high','tom_mid_edge','tom_floor',
    )
    for i,kind in enumerate(kinds):
        x=render_drum_event(kind,.07,SR,.82,seed=170+i,patch=a)
        y=render_drum_event(kind,.07,SR,.82,seed=170+i,patch=b)
        assert _sha(x)==_sha(y), kind


def test_s27g_room_send_follows_authenticated_snare_articulation_hierarchy():
    ghost=_room_report('snare_ghost')['room_rms']
    center=_room_report('snare_center')['room_rms']
    rim=_room_report('snare_rimshot')['room_rms']
    assert rim > center * 1.03
    assert center > ghost * 1.12


def test_s27g_room_send_follows_hihat_contact_state_without_touching_source():
    tight=_room_report('hat_tight_closed')['room_rms']
    closed=_room_report('hat_closed')['room_rms']
    half=_room_report('hat_half_open')['room_rms']
    opened=_room_report('hat_open')['room_rms']
    assert tight < closed < half < opened


def test_s27g_floor_tom_excites_room_more_than_high_tom_for_equal_authored_velocity():
    high=_room_report('tom_high')['room_rms']
    floor=_room_report('tom_floor')['room_rms']
    assert floor > high * 1.04


def test_s27g_overhead_propagation_preserves_close_attack_and_keeps_shorter_tail_than_s26():
    dry=_fixed_dry()
    ev=[{'event_type':'drum','start_beat':0.0,'duration_beats':.1,'drum':'snare_rimshot','velocity':.95}]
    p=materialize_preset(NEW,role='drums'); cfg=p['drum_graph']['kit_integration']
    s26=materialize_preset(S26,role='drums'); cfg26=s26['drum_graph']['kit_integration']
    wet,rep=integrate_drum_kit(dry,SR,ev,.5,cfg)
    old,_=integrate_drum_kit(dry,SR,ev,.5,cfg26)
    m=int(.0025*SR)
    assert _rms(wet[:m]) > _rms(dry[:m])*.80
    late=slice(int(.38*SR),int(.85*SR))
    assert _rms(wet[late]) < _rms(old[late])*.98
    assert rep['room_excitation_peak'] > rep['room_excitation_mean'] > 0
    assert rep['peak'] < 1.2


def test_s27g_engine_accepts_articulation_weights_and_track_postprocess():
    p=materialize_preset(NEW,role='drums')
    e=engine_for_patch(p)
    e.validate_ir_patch('drums',p)
    assert e.capabilities().track_post_process is True
    assert e.tail_seconds(p) >= 1.0
