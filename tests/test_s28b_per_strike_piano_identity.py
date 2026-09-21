import copy
import numpy as np

from code_composer.audio.piano import render_piano_note
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.presets import materialize_preset
from code_composer.render import _piano_events_with_strike_identity, _render_dry_track


def _legacy_patch():
    return resolve_piano_design(materialize_preset("piano.concert_grand", role="piano"))


def _natural_patch():
    return resolve_piano_design(materialize_preset("piano.concert_grand_natural", role="piano"))


def _attack_rms(x, sr=24000, seconds=.080):
    n=max(1,int(sr*seconds))
    return float(np.sqrt(np.mean(np.asarray(x[:n], dtype=np.float64) ** 2)))


def _centroid(x, sr=24000, seconds=.120):
    n=max(64,int(sr*seconds))
    mono=np.mean(np.asarray(x[:n], dtype=np.float64), axis=1)
    win=np.hanning(len(mono))
    spec=np.abs(np.fft.rfft(mono*win))
    freqs=np.fft.rfftfreq(len(mono), 1/sr)
    return float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))


def test_legacy_concert_grand_ignores_strike_identity_and_stays_byte_exact():
    patch=_legacy_patch()
    a=render_piano_note(60,.45,24000,patch,velocity=.74,performance={"piano_strike_seed":11})
    b=render_piano_note(60,.45,24000,patch,velocity=.74,performance={"piano_strike_seed":99991})
    assert np.array_equal(a,b)


def test_natural_preset_same_strike_seed_is_byte_exact():
    patch=_natural_patch()
    perf={"piano_strike_seed":123456,"piano_strike_ordinal":3}
    a=render_piano_note(60,.45,24000,patch,velocity=.74,performance=perf)
    b=render_piano_note(60,.45,24000,patch,velocity=.74,performance=perf)
    assert np.array_equal(a,b)


def test_natural_preset_repeated_strikes_are_different_but_bounded():
    patch=_natural_patch()
    a=render_piano_note(60,.45,24000,patch,velocity=.74,performance={"piano_strike_seed":101})
    b=render_piano_note(60,.45,24000,patch,velocity=.74,performance={"piano_strike_seed":202})
    assert not np.array_equal(a,b)
    ra,rb=_attack_rms(a),_attack_rms(b)
    assert 0.86 <= rb/(ra+1e-12) <= 1.16
    ca,cb=_centroid(a),_centroid(b)
    assert abs(cb-ca)/(ca+1e-12) < .12


def test_strike_identity_changes_phase_noise_not_fundamental_pitch():
    patch=_natural_patch()
    outs=[render_piano_note(60,.55,24000,patch,velocity=.8,performance={"piano_strike_seed":s}) for s in (1,2,3,4)]
    peaks=[]
    for x in outs:
        mono=np.mean(x[:int(.18*24000)],axis=1)
        spec=np.abs(np.fft.rfft(mono*np.hanning(len(mono))))
        freqs=np.fft.rfftfreq(len(mono),1/24000)
        band=(freqs>245)&(freqs<280)
        peaks.append(float(freqs[band][np.argmax(spec[band])]))
    assert max(peaks)-min(peaks) <= 6.0


def test_control_insertion_does_not_consume_piano_strike_ordinal():
    notes=[
        {"start_beat":0.0,"duration_beats":.5,"midi":60,"velocity":.7},
        {"start_beat":1.0,"duration_beats":.5,"midi":60,"velocity":.7},
    ]
    control={"event_type":"piano_control","control":"sustain_pedal","start_beat":.5,"duration_beats":.25,
             "points":[{"offset_beats":0.0,"position":0.0},{"offset_beats":.25,"position":0.0}]}
    a=_piano_events_with_strike_identity(notes,77,"piano")
    b=_piano_events_with_strike_identity([notes[0],control,notes[1]],77,"piano")
    seeds_a=[e["performance"]["piano_strike_seed"] for e in a if "midi" in e]
    seeds_b=[e["performance"]["piano_strike_seed"] for e in b if "midi" in e]
    assert seeds_a==seeds_b


def test_repeated_note_track_gets_distinct_physical_strike_identity_and_replays_exactly():
    patch=_natural_patch()
    ir={"meta":{"global_seed":9127},"instruments":{"p":patch}}
    track={"id":"piano","instrument":"p","gain":1.0,"pan":0.0,"events":[
        {"start_beat":0.0,"duration_beats":.45,"midi":60,"velocity":.74},
        {"start_beat":1.0,"duration_beats":.45,"midi":60,"velocity":.74},
        {"start_beat":2.0,"duration_beats":.45,"midi":60,"velocity":.74},
    ]}
    beat_s=60/92
    n=int(4*beat_s*24000)
    a=_render_dry_track(ir,track,n,24000,beat_s,graph_mode=False)
    b=_render_dry_track(ir,track,n,24000,beat_s,graph_mode=False)
    assert np.array_equal(a,b)
    starts=[int(i*beat_s*24000) for i in (0,1,2)]
    attacks=[a[s:s+1200] for s in starts]
    assert not np.array_equal(attacks[0],attacks[1])
    assert not np.array_equal(attacks[1],attacks[2])


def test_factory_natural_preset_resolves_bounded_strike_identity_controls():
    patch=_natural_patch()
    cfg=patch["piano_graph"]["strike_identity"]
    assert 0 < cfg["phase_jitter_rad"] <= .8
    assert 0 < cfg["unison_phase_jitter_rad"] <= .5
    assert 0 < cfg["hammer_noise_mix"] <= 1
    assert cfg["hammer_gain_variation"] <= .2
    assert cfg["hammer_decay_variation"] <= .3


def test_global_seed_changes_strike_identity_but_not_authored_notes():
    events=[{"start_beat":0.0,"duration_beats":.5,"midi":60,"velocity":.7}]
    a=_piano_events_with_strike_identity(copy.deepcopy(events),1,"piano")
    b=_piano_events_with_strike_identity(copy.deepcopy(events),2,"piano")
    assert a[0]["midi"]==b[0]["midi"]==60
    assert a[0]["start_beat"]==b[0]["start_beat"]==0.0
    assert a[0]["performance"]["piano_strike_seed"] != b[0]["performance"]["piano_strike_seed"]
