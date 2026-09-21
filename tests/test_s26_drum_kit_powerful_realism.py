import hashlib
import json
from pathlib import Path

import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.drum_kit import integrate_drum_kit
from code_composer.audio.engines import engine_for_patch

ROOT=Path(__file__).resolve().parents[1]
SR=24000


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _events(velocity=.9):
    return [
        {'event_type':'drum','start_beat':0.0,'duration_beats':.25,'drum':'kick','velocity':velocity},
        {'event_type':'drum','start_beat':1.0,'duration_beats':.25,'drum':'snare','velocity':velocity},
    ]


def test_s26_preset_registered_and_source_blocks_preserve_r5_exactly():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert 'drums.s19_core_powerful_room' in ids
    r5=get_preset('drums.s19_core_cymbal_extension')['patch']['drum_graph']
    s26=get_preset('drums.s19_core_powerful_room')['patch']['drum_graph']
    for key in ('kick','snare','hat','ride','crash','cymbal_extension'):
        assert s26[key] == r5[key]
    assert s26['kit_integration']['enabled'] is True


def test_s26_direct_event_sources_are_byte_exact_to_r5_before_track_integration():
    r5=materialize_preset('drums.s19_core_cymbal_extension',role='drums')
    s26=materialize_preset('drums.s19_core_powerful_room',role='drums')
    for kind, dur, vel, seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
        ('ride',1.35,.83,29),('crash',1.65,.96,31),
    ):
        a=render_drum_event(kind,dur,SR,vel,seed=seed,patch=r5)
        b=render_drum_event(kind,dur,SR,vel,seed=seed,patch=s26)
        assert _sha(a)==_sha(b)


def test_s26_kit_integration_is_deterministic_and_adds_shared_late_energy():
    patch=materialize_preset('drums.s19_core_powerful_room',role='drums')
    cfg=patch['drum_graph']['kit_integration']
    n=int(1.8*SR)
    dry=np.zeros((n,2),dtype=np.float64)
    hit=render_drum_event('snare',.25,SR,.95,seed=41,patch=patch)
    dry[:len(hit)] += hit
    events=[{'event_type':'drum','start_beat':0.0,'duration_beats':.25,'drum':'snare','velocity':.95}]
    a,ra=integrate_drum_kit(dry,SR,events,.5,cfg)
    b,rb=integrate_drum_kit(dry,SR,events,.5,cfg)
    assert np.array_equal(a,b)
    assert ra==rb
    dry_late=float(np.sqrt(np.mean(dry[int(.18*SR):int(.50*SR)]**2)))
    wet_late=float(np.sqrt(np.mean(a[int(.18*SR):int(.50*SR)]**2)))
    assert wet_late > dry_late * 1.25
    assert ra['room_rms'] > 0


def test_s26_authored_velocity_increases_room_excitation_without_changing_dry_input():
    patch=materialize_preset('drums.s19_core_powerful_room',role='drums')
    cfg=patch['drum_graph']['kit_integration']
    n=int(1.2*SR)
    rng=np.random.default_rng(123)
    dry=np.zeros((n,2),dtype=np.float64)
    burst=rng.standard_normal(int(.08*SR))*np.exp(-np.arange(int(.08*SR))/(.018*SR))
    dry[:len(burst),0]=burst*.08
    dry[:len(burst),1]=burst*.08
    soft=[{'event_type':'drum','start_beat':0.0,'duration_beats':.25,'drum':'snare','velocity':.40}]
    hard=[{'event_type':'drum','start_beat':0.0,'duration_beats':.25,'drum':'snare','velocity':1.00}]
    _,rs=integrate_drum_kit(dry,SR,soft,.5,cfg)
    _,rh=integrate_drum_kit(dry,SR,hard,.5,cfg)
    assert rh['room_rms'] > rs['room_rms'] * 1.12


def test_s26_close_transient_remains_present_and_output_is_bounded_on_short_groove():
    patch=materialize_preset('drums.s19_core_powerful_room',role='drums')
    cfg=patch['drum_graph']['kit_integration']
    beat_s=.5
    n=int(2.4*SR)
    dry=np.zeros((n,2),dtype=np.float64)
    events=_events(.96)
    for i,ev in enumerate(events):
        hit=render_drum_event(ev['drum'],ev['duration_beats']*beat_s,SR,ev['velocity'],seed=61+i*13,patch=patch)
        st=int(ev['start_beat']*beat_s*SR); en=min(n,st+len(hit))
        dry[st:en]+=hit[:en-st]
    integrated,report=integrate_drum_kit(dry,SR,events,beat_s,cfg)
    m=int(.020*SR)
    dry_on=float(np.sqrt(np.mean(dry[:m]**2)))
    wet_on=float(np.sqrt(np.mean(integrated[:m]**2)))
    assert wet_on > dry_on*.82
    assert report['peak'] < 1.35
    assert report['output_rms'] > report['input_rms']*.90


def test_s26_engine_exposes_track_post_process_and_room_tail():
    patch=materialize_preset('drums.s19_core_powerful_room',role='drums')
    engine=engine_for_patch(patch)
    assert engine.capabilities().track_post_process is True
    assert engine.tail_seconds(patch) >= 1.10
