import math
import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch, registered_engines
from code_composer.audio.instrument import synth_patch_note
from code_composer.presets import list_presets, materialize_preset


def _patch(**graph):
    return materialize_preset(
        "bass.electric_finger_modeled",
        role="bass",
        patch_overrides={"plucked_bass_graph": graph} if graph else None,
    )


def _mono(y):
    y=np.asarray(y,dtype=float)
    return y.mean(axis=1) if y.ndim==2 else y


def _centroid(x,sr):
    x=np.asarray(x,dtype=float)
    w=np.hanning(len(x))
    s=np.abs(np.fft.rfft(x*w))
    f=np.fft.rfftfreq(len(x),1/sr)
    return float((s*f).sum()/(s.sum()+1e-12))


def _band_ratio(x,sr,lo,hi):
    x=np.asarray(x,dtype=float)
    s=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
    f=np.fft.rfftfreq(len(x),1/sr)
    return float(s[(f>=lo)&(f<hi)].sum()/(s.sum()+1e-12))


def _dominant(x,sr,lo=40,hi=500):
    x=np.asarray(x,dtype=float)
    s=np.abs(np.fft.rfft(x*np.hanning(len(x))))
    f=np.fft.rfftfreq(len(x),1/sr)
    m=(f>=lo)&(f<=hi)
    return float(f[m][np.argmax(s[m])])


def test_s16_plucked_bass_engine_and_factory_preset_surface():
    assert "plucked_bass" in registered_engines()
    metas={x["preset_id"]:x for x in list_presets(role="bass")}
    assert "bass.electric_finger_modeled" in metas
    assert metas["bass.electric_finger_modeled"]["engine"]=="plucked_bass"
    p=_patch()
    assert engine_for_patch(p).name=="plucked_bass"
    assert p["preset_provenance"]["preset_id"]=="bass.electric_finger_modeled"


def test_s16_modeled_bass_is_deterministic_and_bounded():
    p=_patch(); sr=24000
    a=synth_patch_note(36,1.0,sr,p,velocity=.78)
    b=synth_patch_note(36,1.0,sr,p,velocity=.78)
    assert np.array_equal(a,b)
    assert a.shape==(sr,2)
    assert .02 < float(np.max(np.abs(a))) <= 1.0
    assert np.isfinite(a).all()


def test_s16_frequency_dependent_damping_darkens_the_tail():
    sr=24000; y=_mono(synth_patch_note(36,1.2,sr,_patch(),velocity=.8))
    early=y[int(.01*sr):int(.15*sr)]
    late=y[int(.75*sr):int(1.0*sr)]
    assert _centroid(early,sr) > _centroid(late,sr)*1.45
    assert _band_ratio(early,sr,700,4000) > _band_ratio(late,sr,700,4000)*6.0


def test_s16_pluck_position_controls_brightness_without_new_pitch():
    sr=24000
    bridge=_mono(synth_patch_note(36,.8,sr,_patch(pluck_position=.08),velocity=.8))[100:7000]
    finger=_mono(synth_patch_note(36,.8,sr,_patch(pluck_position=.19),velocity=.8))[100:7000]
    assert _centroid(bridge,sr) > _centroid(finger,sr)*1.20
    assert _band_ratio(bridge,sr,700,4000) > _band_ratio(finger,sr,700,4000)*2.0
    # Both remain anchored to the authored note rather than a fixed resonator pitch.
    f0=65.40639132514966  # C2 / MIDI 36
    for x in (bridge,finger):
        dom=_dominant(x,sr,45,180)
        nearest=min((f0*h for h in range(1,4)),key=lambda z:abs(z-dom))
        assert abs(1200*math.log2(dom/nearest)) < 55


def test_s16_pickup_position_changes_spectrum_deterministically():
    sr=24000
    neck=_mono(synth_patch_note(36,.8,sr,_patch(pickup_position=.37),velocity=.8))[100:7000]
    bridge=_mono(synth_patch_note(36,.8,sr,_patch(pickup_position=.11),velocity=.8))[100:7000]
    assert not np.array_equal(neck,bridge)
    assert abs(_centroid(neck,sr)-_centroid(bridge,sr)) > 25.0


def test_s16_existing_bass_pitch_approach_maps_to_physical_string_pitch():
    sr=24000; p=_patch()
    plain=_mono(synth_patch_note(36,.5,sr,p,velocity=.8))
    slide=_mono(synth_patch_note(36,.5,sr,p,velocity=.8,performance={
        "pitch_start_cents":0.0,"pitch_end_cents":200.0,"pitch_time_s":.16,
        "attack_scale":.78,"release_scale":.50,
    }))
    assert not np.array_equal(plain,slide)
    early=_dominant(slide[int(.02*sr):int(.10*sr)],sr,45,180)
    late=_dominant(slide[int(.22*sr):int(.38*sr)],sr,45,180)
    assert late > early*1.025


def test_s16_attack_release_expression_changes_excitation_without_randomness():
    sr=24000; p=_patch()
    accent=synth_patch_note(40,.55,sr,p,velocity=.82,performance={"attack_scale":.72,"release_scale":.86})
    ghost=synth_patch_note(40,.55,sr,p,velocity=.30,performance={"attack_scale":.90,"release_scale":.42})
    assert not np.array_equal(accent,ghost)
    assert float(np.sqrt(np.mean(accent[:int(.08*sr)]**2))) > float(np.sqrt(np.mean(ghost[:int(.08*sr)]**2)))*1.8


def test_s16_invalid_physical_parameters_are_rejected():
    p=_patch(); p["plucked_bass_graph"]["pluck_position"]=.9
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch("bass",p)
    p=_patch(); p["plucked_bass_graph"]["finger_noise_low_hz"]=5000; p["plucked_bass_graph"]["finger_noise_high_hz"]=1000
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch("bass",p)
