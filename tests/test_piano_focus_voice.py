"""Physical/contract regression only. These tests do not approve timbre quality."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from code_composer.audio import piano
from code_composer.audio.piano_design import resolve_piano_design, PianoDesignError
from code_composer.presets import materialize_preset, get_preset

ROOT=Path(__file__).resolve().parents[1]


def _patch(name='piano.concert_grand_focused'):
    return resolve_piano_design(materialize_preset(name,role='piano'))


def test_alignment_is_explicit_validated_and_has_no_musical_content():
    p=get_preset('piano.concert_grand_focused')
    assert p['musical_content'] is False
    design=p['patch']['piano_design']
    assert design['controls']['unison_hammer_phase_alignment']==1.
    for path in [ROOT/'skills/code-composer/kit/schemas/piano_design.schema.json',
                 ROOT/'skills/code-composer/kit/src/code_composer/reference/schemas/piano_design.schema.json']:
        Draft202012Validator(json.loads(path.read_text())).validate(design)
    assert _patch()['piano_graph']['strings']['hammer_phase_alignment']==1.
    old=_patch('piano.concert_grand_natural')['piano_graph']['strings']
    assert old.get('hammer_phase_alignment',0.)==0.


@pytest.mark.parametrize('value',[-.01,1.01,float('nan'),float('inf')])
def test_invalid_alignment_is_rejected_by_design_and_direct_engine(value):
    patch=materialize_preset('piano.concert_grand_focused',role='piano')
    patch['piano_design']['controls']['unison_hammer_phase_alignment']=value
    with pytest.raises(PianoDesignError):resolve_piano_design(patch)
    with pytest.raises(ValueError):piano._hammer_unison_phase(84,3,0,value)


def test_hammer_alignment_preserves_mean_and_reduces_initial_differential_energy():
    previous=[]
    for midi in range(60,85):
        phases=np.array([piano._hammer_unison_phase(midi,3,i,1.) for i in range(3)])
        assert phases.mean()==pytest.approx(.53,abs=1e-15)
        z=np.exp(1j*phases)
        previous.append(float(np.sum(np.abs(z-z.mean())**2)))
    assert np.max(np.diff(previous))<=1e-14
    assert previous[0]>.4 and previous[-1]<1e-25
    phases=np.array([piano._hammer_unison_phase(84,3,i,1.) for i in range(3)])
    np.testing.assert_array_equal(phases,np.full(3,.53))


@pytest.mark.parametrize('midi',[36,60,72,84,88])
@pytest.mark.parametrize('pedal',[False,True])
def test_default_render_keeps_previous_phase_path_exactly(midi,pedal,monkeypatch):
    p=_patch('piano.concert_grand_natural');perf={'pedal':pedal,'piano_strike_seed':2820}
    current=piano.render_piano_note(midi,.25,24000,p,.75,perf)
    monkeypatch.setattr(piano,'_hammer_unison_phase',lambda midi,count,i,alignment=0.:.53*i)
    previous=piano.render_piano_note(midi,.25,24000,p,.75,perf)
    np.testing.assert_array_equal(current,previous)


@pytest.mark.parametrize('midi,count',[(36,1),(60,2),(72,1),(84,2)])
def test_alignment_does_not_change_single_or_double_string_voices(midi,count):
    p=_patch();p['piano_graph']['strings'].update({'low_strings':count,'mid_strings':count,'high_strings':count})
    a=piano.render_piano_note(midi,.3,24000,p,.75)
    p['piano_graph']['strings']['hammer_phase_alignment']=0.
    b=piano.render_piano_note(midi,.3,24000,p,.75)
    np.testing.assert_array_equal(a,b)


def test_alignment_does_not_rewrite_frequencies_decays_or_levels(monkeypatch):
    original=piano._coupled_unison_state;seen=[]
    def inspect(t,f,phase,decays,levels,coupling):
        seen.append((np.array(f),np.array(decays),np.array(levels),np.array(phase)))
        return original(t,f,phase,decays,levels,coupling)
    monkeypatch.setattr(piano,'_coupled_unison_state',inspect)
    p=_patch();perf={'pedal_controlled':True,'piano_strike_seed':2820};frozen=deepcopy((p,perf))
    piano.render_piano_note(84,.4,24000,p,.75,perf);n=len(seen)
    assert (p,perf)==frozen
    p['piano_graph']['strings']['hammer_phase_alignment']=0.
    piano.render_piano_note(84,.4,24000,p,.75,perf)
    assert n and len(seen)==2*n
    for a,b in zip(seen[:n],seen[n:]):
        for i in range(3):np.testing.assert_array_equal(a[i],b[i])
        assert not np.array_equal(a[3],b[3])


@pytest.mark.parametrize('midi',[48,60,72,84,88])
def test_focused_voice_keeps_velocity_response_and_per_note_headroom(midi):
    p=_patch();values=[]
    for velocity in [.35,.75,1.]:
        x=piano.render_piano_note(midi,.3,24000,p,velocity,{'piano_strike_seed':2820})
        assert np.isfinite(x).all() and np.max(np.abs(x))<.99
        values.append(float(np.sqrt(np.mean(x[:2400]**2))))
    assert values[0]<values[1]<values[2]
    half=deepcopy(p);half['piano_graph']['output_gain']/=2.
    a=piano.render_piano_note(midi,.3,24000,p,1.,{'piano_strike_seed':2820})
    b=piano.render_piano_note(midi,.3,24000,half,1.,{'piano_strike_seed':2820})
    np.testing.assert_array_equal(a,2.*b)  # catches hidden per-note normalization


def test_factory_track_soundboard_release_and_inputs_are_preserved():
    p=_patch();sr=24000
    events=[{'midi':76,'start_beat':0.,'duration_beats':.4,'velocity':.7},
        {'midi':78,'start_beat':.5,'duration_beats':.4,'velocity':.65},
        {'event_type':'piano_control','control':'sustain_pedal','start_beat':0.,'duration_beats':1.,
         'points':[{'offset_beats':0.,'position':1.},{'offset_beats':.9,'position':1.},{'offset_beats':1.,'position':0.}]}]
    frozen=deepcopy((p,events));n=sr*4
    a=piano.render_piano_track_with_controls(events,n,sr,p,1.)
    b=piano.render_piano_track_with_controls(events,n,sr,p,1.)
    np.testing.assert_array_equal(a,b)
    body=piano.apply_piano_soundboard(a,sr,p,events,1.)
    assert body.shape==(n,2) and np.isfinite(body).all()
    assert np.max(np.abs(body-a))>1e-6
    assert np.sqrt(np.mean(body[-sr//4:]**2)) < np.sqrt(np.mean(body[:sr]**2))*1e-4
    assert (p,events)==frozen


def test_acoustic_schema_controls_match_runtime_bounds():
    from code_composer.audio.piano_design import ACOUSTIC_CONTROL_SPECS
    paths=[ROOT/'skills/code-composer/kit/schemas/piano_design.schema.json',
           ROOT/'skills/code-composer/kit/src/code_composer/reference/schemas/piano_design.schema.json']
    assert paths[0].read_bytes()==paths[1].read_bytes()
    schema=json.loads(paths[0].read_text())
    controls=schema['oneOf'][0]['properties']['controls']
    assert controls['additionalProperties'] is False
    assert set(controls['properties'])==set(ACOUSTIC_CONTROL_SPECS)
    for name,(_,lo,hi,cast) in ACOUSTIC_CONTROL_SPECS.items():
        assert controls['properties'][name]=={'type':'integer' if cast is int else 'number',
                                               'minimum':lo,'maximum':hi}
