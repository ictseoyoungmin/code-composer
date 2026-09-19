import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from code_composer.audio.bridge_admittance_fit import (
    EraAdmittanceState,
    fit_era_impulse_response,
    impulse_response_from_profile,
    validate_era_profile,
)
from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import materialize_preset

ROOT = Path(__file__).resolve().parents[1]
FMT = "code-composer-bridge-admittance-era/v1"


def _known_profile(sr=48000):
    poles=[]; residues=[]
    for f,r,a in [(280,.998,.12),(520,.996,.08),(2450,.985,.035)]:
        p=r*np.exp(1j*2*np.pi*f/sr)
        poles += [p, np.conj(p)]
        residues += [a/2, a/2]
    return {
        "format":FMT,"method":"era","reference_sample_rate_hz":sr,"order":6,
        "poles":[[z.real,z.imag] for z in poles],
        "residues":[[complex(z).real,complex(z).imag] for z in residues],
        "direct":0.0,"output_scale":1.0,"stabilized_poles":0,
        "hankel_rows":64,"hankel_cols":64,"source":{"kind":"synthetic_protocol_fixture"},
    }


def test_era_recovers_known_compact_response_without_musical_content():
    truth=_known_profile()
    y=impulse_response_from_profile(truth,4096)
    fitted=fit_era_impulse_response(y,48000,order=6,hankel_rows=80,hankel_cols=80,source={"kind":"synthetic_protocol_fixture"})
    assert fitted["format"]==FMT and fitted["order"]==6
    assert fitted["fit_metrics"]["nmse_time"] < 1e-12
    freqs=sorted({round(abs(np.angle(complex(*p)))*48000/(2*np.pi),2) for p in fitted["poles"]})
    assert np.allclose(freqs,[280,520,2450],atol=.05)
    assert not ({"notes","melody","rhythm","chords","events"} & set(json.dumps(fitted).lower().split()))


def test_runtime_profile_is_deterministic_and_sample_rate_adapts():
    p=_known_profile()
    a=EraAdmittanceState.from_profile(p,44100)
    b=EraAdmittanceState.from_profile(p,44100)
    x=np.zeros(1000); x[0]=1
    ya=np.array([a.tick(v) for v in x]); yb=np.array([b.tick(v) for v in x])
    assert np.array_equal(ya,yb)
    assert np.isfinite(ya).all() and np.max(np.abs(ya))>0


def test_invalid_unstable_profile_is_rejected():
    p=_known_profile(); p["poles"][0]=[1.01,0]
    try:
        validate_era_profile(p)
    except Exception:
        pass
    else:
        raise AssertionError("unstable profile accepted")


def _crossing_ir():
    ir=json.loads((ROOT/"tests/fixtures/high_level_ir.json").read_text())
    ir["transport"]["bpm"]=72
    ir["instruments"]["lead"]=materialize_preset("bowed.violin.modeled_admittance",role="lead")
    ir["tracks"]=[{"id":"lead","instrument":"lead","gain":.18,"pan":0.0,"source":{"type":"resolved"},"events":[
      {"start_beat":0,"duration_beats":1,"midi":55,"velocity":.61,"performance":{"articulation":"legato"}},
      {"start_beat":1,"duration_beats":1,"midi":62,"velocity":.63,"performance":{"articulation":"legato"}},
      {"start_beat":2,"duration_beats":1,"midi":69,"velocity":.62,"performance":{"articulation":"legato"}},
    ]}]
    ir["mix"]={"tail_seconds":.4,"drive":1.0,"ceiling":.98}
    return ir


def test_fitted_bridge_response_changes_closed_loop_when_embedded_in_patch():
    ir=realize_violin_performance(_crossing_ir(),"lead",config={"strict_comfort":False})
    base=ir["instruments"]["lead"]
    truth=_known_profile(48000)
    # Small scale keeps the fitted measurement as a weak bridge load.
    truth["output_scale"]=0.12
    fit_patch=json.loads(json.dumps(base))
    fit_patch["bowed_waveguide_graph"]["body"]["bridge_feedback"]["fitted_response"]=truth
    engine_for_patch(fit_patch).validate_authoring_patch("lead",fit_patch)
    sr=22050; beat_s=60/72; n=int((3*beat_s+.5)*sr)
    y0=engine_for_patch(base).render_track(ir["tracks"][0]["events"],n,sr,base,beat_s,gain=.18,pan=0)
    y1=engine_for_patch(fit_patch).render_track(ir["tracks"][0]["events"],n,sr,fit_patch,beat_s,gain=.18,pan=0)
    assert y0 is not None and y1 is not None and np.isfinite(y1).all()
    assert not np.array_equal(y0,y1)
    assert float(np.sqrt(np.mean((y1[:,0]-y0[:,0])**2))) > 1e-7


def test_wav_adapter_write_profile_and_validation_edges(tmp_path):
    from code_composer.audio.bridge_admittance_fit import (
        BridgeAdmittanceFitError, fit_era_wav, write_profile,
    )
    p=_known_profile(); y=impulse_response_from_profile(p,4096)
    stereo=np.column_stack([np.zeros_like(y), y])
    wav=tmp_path/'stereo_int16.wav'
    peak=max(1e-12,float(np.max(np.abs(stereo))))
    wavfile.write(wav,48000,np.clip(stereo/peak*20000,-32768,32767).astype(np.int16))
    fit=fit_era_wav(wav,order=6,channel=1,normalize_peak=True,source={'source_id':'adapter-test'})
    assert fit['source']['path']==wav.name and fit['source']['source_id']=='adapter-test'
    out=tmp_path/'profile.json'; write_profile(fit,out)
    assert json.loads(out.read_text())['format']==FMT
    try:
        fit_era_wav(wav,order=6,channel=7)
    except BridgeAdmittanceFitError:
        pass
    else:
        raise AssertionError('invalid channel accepted')


def test_fit_rejects_bad_protocol_inputs_and_runtime_rate():
    from code_composer.audio.bridge_admittance_fit import BridgeAdmittanceFitError
    bad_cases=[
        (np.zeros(8),48000,{}),
        (np.zeros(64),48000,{}),
        (np.r_[1.0,np.full(63,np.nan)],48000,{}),
        (np.r_[1.0,np.zeros(127)],1000,{}),
        (np.r_[1.0,np.zeros(127)],48000,{'order':1}),
        (np.r_[1.0,np.zeros(127)],48000,{'order':80}),
        (np.r_[1.0,np.zeros(127)],48000,{'order':4,'max_pole_radius':1.0}),
        (np.r_[1.0,np.zeros(31)],48000,{'order':12,'hankel_rows':4,'hankel_cols':4}),
    ]
    for y,sr,kw in bad_cases:
        try:
            fit_era_impulse_response(y,sr,**kw)
        except BridgeAdmittanceFitError:
            pass
        else:
            raise AssertionError((sr,kw))
    state_profile=_known_profile()
    try:
        EraAdmittanceState.from_profile(state_profile,1000)
    except BridgeAdmittanceFitError:
        pass
    else:
        raise AssertionError('bad runtime sample rate accepted')


def test_profile_validator_rejects_malformed_complex_and_scale():
    from code_composer.audio.bridge_admittance_fit import BridgeAdmittanceFitError
    cases=[]
    p=_known_profile(); p['poles']=[[0.5]]+p['poles'][1:]; cases.append(p)
    p=_known_profile(); p['residues']=p['residues'][:-1]; cases.append(p)
    p=_known_profile(); p['output_scale']=0; cases.append(p)
    p=_known_profile(); p['reference_sample_rate_hz']=1000; cases.append(p)
    for p in cases:
        try: validate_era_profile(p)
        except BridgeAdmittanceFitError: pass
        else: raise AssertionError('malformed profile accepted')
