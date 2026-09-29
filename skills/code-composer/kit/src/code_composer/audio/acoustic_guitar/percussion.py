"""AG07 percussive acoustic-guitar actions.

No drum samples, IRs, or independent percussion synth are used. Every action
creates a deterministic contact/excitation signal and feeds it through the same
generic acoustic-guitar body/air radiation stage used by pitched notes.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter

from .body import radiate_acoustic_guitar_body


ACTIONS = (
    "body_tap",
    "top_slap",
    "bridge_hit",
    "string_slap",
    "muted_strum",
    "dead_strum",
    "nail_click",
)

LOCATIONS = (
    "lower_bout",
    "upper_bout",
    "soundboard",
    "bridge",
    "strings",
    "rim",
)


def _one_pole_lowpass(x, sr, cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    alpha=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([alpha],[1.0,-(1.0-alpha)],x)


def _one_pole_highpass(x, sr, cutoff):
    return x-_one_pole_lowpass(x,sr,cutoff)


def _normalize_rms(x):
    rms=float(np.sqrt(np.mean(x*x))+1e-12)
    return x/rms


def _contact_noise(n, sr, rng, hp, lp, decay_s):
    t=np.arange(n,dtype=np.float64)/float(sr)
    x=rng.standard_normal(n).astype(np.float64)
    x=_one_pole_highpass(x,sr,hp)
    x=_one_pole_lowpass(x,sr,lp)
    x=_normalize_rms(x)
    return x*np.exp(-t/max(0.001,float(decay_s)))


def _body_contact(action, location, strength, n, sr, rng):
    t=np.arange(n,dtype=np.float64)/float(sr)

    # Contact location changes coupling/excitation spectrum, not the body's
    # modal frequencies. The body resonator itself remains the accepted AG01 body.
    location_profile={
        "lower_bout": (45.0, 2600.0, 0.011, 1.18, 0.95, 0.84),
        "upper_bout": (85.0, 4200.0, 0.008, 0.92, 1.05, 0.96),
        "soundboard": (60.0, 5200.0, 0.007, 1.00, 1.00, 1.00),
        "bridge": (420.0, 7600.0, 0.0045, 0.72, 1.22, 1.18),
        "strings": (650.0, 8800.0, 0.0055, 0.62, 1.30, 1.10),
        "rim": (180.0, 6200.0, 0.0048, 0.78, 1.16, 1.06),
    }
    hp,lp,decay,low_scale,high_scale,coupling_gain=location_profile[location]
    noise=_contact_noise(n,sr,rng,hp,lp,decay)

    # A short broad mechanical impulse. It is deliberately non-pitched.
    impulse=np.zeros(n,dtype=np.float64)
    impulse[0]=1.0
    if n>1:
        impulse[1]=-0.42
    if n>2:
        impulse[2]=0.14

    low=_one_pole_lowpass(noise,sr,900.0)*low_scale
    high=_one_pole_highpass(noise,sr,1500.0)*high_scale

    profiles={
        "body_tap": (0.68,0.18,0.20),
        "top_slap": (0.30,0.62,0.42),
        "bridge_hit": (0.18,0.72,0.58),
        "nail_click": (0.06,0.78,0.72),
    }
    low_mix,high_mix,impulse_mix=profiles[action]
    drive=low*low_mix + high*high_mix + impulse*impulse_mix
    return drive*coupling_gain*max(0.0,min(1.0,strength))


def _string_contact(action, strength, n, sr, rng, parameters):
    t=np.arange(n,dtype=np.float64)/float(sr)
    direction=str(parameters.get("direction","down"))
    traversal_ms=max(6.0,min(180.0,float(parameters.get("traversal_ms",32.0))))
    string_count=max(1,min(6,int(parameters.get("string_count",6))))

    if action=="string_slap":
        x=_contact_noise(n,sr,rng,520.0,9200.0,0.012)
        # Two short contact components emulate string/fretboard collision without
        # introducing a stable musical pitch.
        delayed=np.zeros(n,dtype=np.float64)
        d=min(n-1,max(1,int(0.0022*sr)))
        delayed[d:]=x[:n-d]
        return (0.78*x + 0.28*delayed)*strength

    # muted/dead strums: several correlated contacts along one hand traversal.
    out=np.zeros(n,dtype=np.float64)
    order=range(string_count) if direction=="down" else range(string_count-1,-1,-1)
    denom=max(1,string_count-1)
    for ordinal,string_index in enumerate(order):
        x=ordinal/denom
        offset_s=(traversal_ms/1000.0)*x
        start=min(n-1,int(offset_s*sr))

        # Contact character follows physical string position. Low-string-side
        # contacts are heavier/darker; high-string-side contacts are lighter
        # and brighter. Reversing traversal therefore changes the audible
        # contact sequence instead of merely relabeling identical impulses.
        string_pos=string_index/denom
        hp=520.0 + 520.0*string_pos
        lp=6500.0 + 2100.0*string_pos
        contact_decay=(0.0075 + 0.0025*(1.0-string_pos))
        if action=="dead_strum":
            contact_decay*=0.72
        local=_contact_noise(n-start,sr,rng,hp,lp,contact_decay)

        # One coherent gesture: entry/exit lighter, middle contacts stronger,
        # with bounded low-to-high string-energy taper.
        gesture=0.78+0.22*math.sin(math.pi*x)
        string_weight=1.08-0.18*string_pos
        if action=="dead_strum":
            gesture*=0.88
        out[start:]+=local*gesture*string_weight
    out=_one_pole_highpass(out,sr,380.0)
    out=_one_pole_lowpass(out,sr,7200.0)
    return out*strength*0.34


def render_acoustic_guitar_action(
    action: str,
    duration_s: float,
    sr: int,
    patch: dict,
    *,
    parameters: dict,
    seed: int = 0,
):
    if action not in ACTIONS:
        raise ValueError(f"unsupported acoustic-guitar action: {action}")

    graph=patch.get("acoustic_guitar_graph",{})
    sr=int(sr)
    duration_s=max(0.01,float(duration_s))
    # Keep action body tails bounded but long enough to expose common resonator identity.
    tail_s=max(0.18,min(0.65,float(parameters.get("tail_s",0.38))))
    n=max(1,int((duration_s+tail_s)*sr))
    strength=max(0.0,min(1.0,float(parameters.get("strength",0.68))))
    location=str(parameters.get("location",{
        "body_tap":"lower_bout",
        "top_slap":"soundboard",
        "bridge_hit":"bridge",
        "string_slap":"strings",
        "muted_strum":"strings",
        "dead_strum":"strings",
        "nail_click":"rim",
    }[action]))
    if location not in LOCATIONS:
        raise ValueError(f"unsupported acoustic-guitar action location: {location}")

    stable_action=sum((i+1)*ord(ch) for i,ch in enumerate(action))
    stable_location=sum((i+1)*ord(ch) for i,ch in enumerate(location))
    rng=np.random.default_rng(
        (int(graph.get("seed",11901))+int(seed)*7919+stable_action*101+stable_location*17)
        & 0xFFFFFFFF
    )

    if action in {"body_tap","top_slap","bridge_hit","nail_click"}:
        contact=_body_contact(action,location,strength,n,sr,rng)
    else:
        contact=_string_contact(action,strength,n,sr,rng,parameters)

    stereo=radiate_acoustic_guitar_body(contact,sr,graph)

    # Body percussion must remain headroom-safe without per-event normalization.
    action_gain={
        "body_tap":0.80,
        "top_slap":0.66,
        "bridge_hit":0.58,
        "string_slap":0.60,
        "muted_strum":0.76,
        "dead_strum":0.70,
        "nail_click":0.42,
    }[action]
    stereo*=action_gain*max(0.0,float(graph.get("output_gain",0.82)))

    fade_n=min(n,max(1,int(0.018*sr)))
    stereo[-fade_n:]*=np.linspace(1.0,0.0,fade_n,endpoint=True)[:,None]
    return stereo


__all__=["ACTIONS","LOCATIONS","render_acoustic_guitar_action"]
