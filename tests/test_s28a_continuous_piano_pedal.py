import copy

import numpy as np
import pytest

from code_composer.audio.engines.piano import PianoEngine
from code_composer.audio.piano import (
    render_piano_note,
    render_piano_track_with_controls,
    resolve_sustain_pedal_position,
)
from code_composer.validation_contracts import (
    ContractValidationError,
    validate_piano_control_events,
)

SR = 12000
BEAT_S = 0.5


def _patch():
    return {
        'kind':'piano',
        'piano_graph':{
            'strings':{
                'max_partials':12,'base_decay_s':2.8,'decay_keytrack':.55,
                'partial_decay_power':.58,'spectral_rolloff':1.36,
                'velocity_brightness':.72,'inharmonicity':.00016,
                'low_strings':1,'mid_strings':2,'high_strings':3,
                'detune_cents':.65,'stereo_width':.72,
            },
            'hammer':{
                'gain':.11,'noise_gain':.055,'decay_s':.018,
                'low_cutoff_hz':700,'soft_high_cutoff_hz':3200,
                'hard_high_cutoff_hz':11000,'tonal_gain':.03,
            },
            'damper':{'release_s':.18,'pedal_release_s':1.65},
            'resonance':{'gain':.02,'pedal_gain':.07,'decay_s':2.4},
            'soundboard':{'gain':.012,'pedal_gain':.035,'cross':.30},
            'body_filter':{'soft_cutoff_hz':3600,'hard_cutoff_hz':11000},
            'declick_ms':.35,'output_gain':.55,
        }
    }


def _ctl(start, dur, points):
    return {
        'event_type':'piano_control', 'control':'sustain_pedal',
        'start_beat':float(start), 'duration_beats':float(dur),
        'points':[{'offset_beats':float(x),'position':float(y)} for x,y in points],
    }


def _note(start=0.0, dur=.5, midi=60, pedal=False):
    return {
        'midi':midi,'start_beat':float(start),'duration_beats':float(dur),
        'velocity':.72,'performance':{'pedal':pedal},
    }


def _rms(x, a, b):
    i=int(a*SR); j=min(len(x),int(b*SR))
    if j<=i:
        return 0.0
    return float(np.sqrt(np.mean(np.asarray(x)[i:j]**2)+1e-30))


def test_pedal_position_persists_between_authored_curves_and_repeds():
    events=[
        _ctl(0,2,[(0,1),(1.9,1),(2,0)]),
        _ctl(2.1,1.9,[(0,1),(1.9,1)]),
    ]
    assert resolve_sustain_pedal_position(events,.5) == pytest.approx(1.0)
    assert resolve_sustain_pedal_position(events,2.05) == pytest.approx(0.0)
    assert resolve_sustain_pedal_position(events,2.5) == pytest.approx(1.0)
    assert resolve_sustain_pedal_position(events,5.0) == pytest.approx(1.0)


def test_explicit_pedal_up_uses_natural_release_instead_of_one_tau_hard_cut():
    patch=_patch()
    patch['piano_graph']['damper']['release_floor_db']=-72.0
    events=[
        _note(dur=.5,pedal=True),
        _ctl(0,2,[(0,1),(1.9,1),(2,0)]),
    ]
    n=int(3.0*SR)
    explicit=render_piano_track_with_controls(events,n,SR,patch,BEAT_S)
    # Pedal-up occurs at 1.0 s and ordinary release tau is 180 ms.  The historical
    # path effectively disappeared around one tau.  A natural release must still
    # carry energy after one tau, then continue decaying smoothly.
    one_tau=_rms(explicit,1.16,1.24)
    three_tau=_rms(explicit,1.50,1.62)
    late=_rms(explicit,2.05,2.20)
    assert one_tau > 1e-5
    assert one_tau > three_tau > late


def test_repedal_does_not_resurrect_a_note_already_damped_at_pedal_up():
    patch=_patch(); n=int(3.0*SR)
    first=[
        _note(dur=.5),
        _ctl(0,2,[(0,1),(1.9,1),(2,0)]),
        _ctl(2.1,1.9,[(0,1),(1.9,1)]),
    ]
    no_repedal=[_note(dur=.5),_ctl(0,2,[(0,1),(1.9,1),(2,0)])]
    a=render_piano_track_with_controls(first,n,SR,patch,BEAT_S)
    b=render_piano_track_with_controls(no_repedal,n,SR,patch,BEAT_S)
    # With no new note, a later pedal-down must not revive the old string energy.
    assert np.array_equal(a,b)


def test_explicit_control_overrides_legacy_note_pedal_boolean_without_hard_cut():
    patch=_patch(); n=int(2.5*SR)
    patch['piano_graph']['damper']['release_floor_db']=-72.0
    down_then_up=[_note(dur=.5,pedal=True),_ctl(0,1,[(0,1),(.9,1),(1,0)])]
    a=render_piano_track_with_controls(down_then_up,n,SR,patch,BEAT_S)
    # Despite performance.pedal=True, the explicit pedal-up at .5 s owns the release.
    # It must decay naturally instead of becoming numerically silent almost at once.
    early=_rms(a,.55,.68)
    mid=_rms(a,.82,.95)
    late=_rms(a,1.35,1.50)
    assert early > mid > late
    assert mid > 1e-6


def test_legacy_track_without_piano_control_stays_on_legacy_note_renderer():
    engine=PianoEngine()
    assert engine.render_track([_note()],int(2*SR),SR,_patch(),BEAT_S) is None
    a=render_piano_note(64,.7,SR,_patch(),velocity=.61,performance={'pedal':True})
    b=render_piano_note(64,.7,SR,_patch(),velocity=.61,performance={'pedal':True})
    assert np.array_equal(a,b)


def _ir(events, patch=None):
    return {
        'instruments':{'p': patch or _patch()},
        'tracks':[{'id':'piano','instrument':'p','events':events}],
    }


def test_piano_control_contract_accepts_sequential_curves():
    validate_piano_control_events(_ir([
        _ctl(0,2,[(0,0),(0.1,1),(1.9,1),(2,0)]),
        _ctl(2,2,[(0,0),(0.08,1),(1.9,1),(2,0)]),
    ]))


def test_piano_control_contract_rejects_overlap_and_bad_points():
    with pytest.raises(ContractValidationError):
        validate_piano_control_events(_ir([
            _ctl(0,2,[(0,0),(2,1)]),
            _ctl(1.9,1,[(0,1),(1,0)]),
        ]))
    bad=_ctl(0,1,[(0,0),(1,1)])
    bad['points'][1]['position']=1.2
    with pytest.raises(ContractValidationError):
        validate_piano_control_events(_ir([bad]))


def test_piano_control_rejects_electric_piano_for_this_slice():
    electric={'kind':'piano','piano_engine':'electric','electric_piano_graph':{'tone':{'mechanism':'tine'}}}
    with pytest.raises(ContractValidationError):
        validate_piano_control_events(_ir([_ctl(0,1,[(0,0),(1,1)])],electric))


def test_explicit_pedal_release_damps_complete_unison_without_s14_side_string_collapse():
    events=[
        _note(dur=.5,midi=72),
        _ctl(0,2,[(0,1),(1.9,1),(2,0)]),
    ]
    n=int(2.0*SR)
    a=_patch(); b=copy.deepcopy(a)
    a['piano_graph']['strings']['release_detune_damping_s']=.025
    b['piano_graph']['strings']['release_detune_damping_s']=.40
    explicit_a=render_piano_track_with_controls(events,n,SR,a,BEAT_S)
    explicit_b=render_piano_track_with_controls(events,n,SR,b,BEAT_S)
    # Explicit pedal-up is a common damper event for the whole unison.  The legacy
    # per-side-string release-collapse time must not color this release.
    assert np.array_equal(explicit_a,explicit_b)

    # The S14 no-pedal safeguard remains active on the legacy/direct note path.
    legacy_a=render_piano_note(72,.5*BEAT_S,SR,a,velocity=.72,performance={'pedal':False})
    legacy_b=render_piano_note(72,.5*BEAT_S,SR,b,velocity=.72,performance={'pedal':False})
    assert not np.array_equal(legacy_a,legacy_b)



def test_explicit_release_note_buffer_reaches_quiet_floor_before_final_declick():
    patch=_patch()
    patch['piano_graph']['damper']['release_s']=.20
    patch['piano_graph']['damper']['release_floor_db']=-72.0
    note=render_piano_note(
        64,.5,SR,patch,velocity=.72,
        performance={'pedal':True,'pedal_controlled':True},
    )
    # 72 dB exponential settling requires ~8.29 tau, not one tau.
    assert len(note)/SR > .5 + 1.5
    peak=float(np.max(np.abs(note)))
    tail=float(np.max(np.abs(note[-max(8,int(.002*SR)):])) )
    assert tail < peak*0.001


def test_explicit_pedal_release_does_not_use_second_105ms_unison_envelope():
    patch=_patch()
    # Historical string-level knobs must not become a second release authority.
    patch['piano_graph']['strings']['pedal_damper_unison_decay_s']=.035
    a=render_piano_note(
        72,.5,SR,patch,velocity=.72,
        performance={'pedal':True,'pedal_controlled':True},
    )
    patch['piano_graph']['strings']['pedal_damper_unison_decay_s']=.18
    b=render_piano_note(
        72,.5,SR,patch,velocity=.72,
        performance={'pedal':True,'pedal_controlled':True},
    )
    assert np.array_equal(a,b)
