"""Deterministic plucked electric-bass synthesis.

This is an independently implemented lightweight physical/parametric model.  It is
not a sample player and does not embed external measurements.  A struck string is
represented as a harmonic bank whose initial amplitudes depend on pluck and pickup
position, while upper partials decay faster than the fundamental.  A small,
band-limited finger transient supplies excitation texture without becoming a
separate pitched oscillator.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter

from ..core.theory import midi_to_hz


def _smoothstep01(x):
    x=np.clip(x,0.0,1.0)
    return x*x*(3.0-2.0*x)


def _one_pole_lowpass(x, sr, cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    alpha=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([alpha],[1.0,-(1.0-alpha)],x)


def _one_pole_highpass(x, sr, cutoff):
    return x-_one_pole_lowpass(x,sr,cutoff)


def _pitch_ratio(n, sr, performance):
    p=performance or {}
    if "pitch_start_cents" not in p and "pitch_end_cents" not in p:
        return np.ones(n,dtype=np.float64)
    start=float(p.get("pitch_start_cents",0.0))
    end=float(p.get("pitch_end_cents",0.0))
    time_s=max(1e-4,float(p.get("pitch_time_s",0.08)))
    m=min(n,max(1,int(time_s*sr)))
    cents=np.full(n,end,dtype=np.float64)
    u=_smoothstep01(np.linspace(0.0,1.0,m,endpoint=True))
    cents[:m]=start+(end-start)*u
    return 2.0**(cents/1200.0)


def _release_guard(n, sr, release_s):
    env=np.ones(n,dtype=np.float64)
    m=min(n,max(1,int(max(1e-4,float(release_s))*sr)))
    env[-m:]*=1.0-_smoothstep01(np.linspace(0.0,1.0,m,endpoint=True))
    return env


def _finger_noise(n, sr, cfg, midi, velocity, attack_scale):
    gain=float(cfg.get("finger_noise_gain",0.012))
    if gain<=0:
        return np.zeros(n,dtype=np.float64)
    seed=int(cfg.get("seed",1701))+int(midi)*1009+n*17
    rng=np.random.default_rng(seed & 0xFFFFFFFF)
    noise=rng.standard_normal(n).astype(np.float64)
    noise=_one_pole_highpass(noise,sr,float(cfg.get("finger_noise_low_hz",550.0)))
    noise=_one_pole_lowpass(noise,sr,float(cfg.get("finger_noise_high_hz",4200.0)))
    rms=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise/=rms
    t=np.arange(n,dtype=np.float64)/sr
    decay=max(0.003,float(cfg.get("finger_noise_decay_s",0.026))*max(.55,float(attack_scale)))
    attack=max(0.0003,float(cfg.get("finger_noise_attack_s",0.0015))*max(.55,float(attack_scale)))
    env=(1.0-np.exp(-t/attack))*np.exp(-t/decay)
    return noise*env*gain*max(.2,float(velocity))**.7


def render_plucked_bass_note(midi: int, duration_s: float, sr: int, patch: dict,
                             velocity: float = 1.0, performance: dict | None = None):
    graph=patch.get("plucked_bass_graph",patch.get("graph",{}))
    if not isinstance(graph,dict):
        graph={}
    n=max(1,int(float(duration_s)*int(sr)))
    t=np.arange(n,dtype=np.float64)/sr
    base=midi_to_hz(int(midi))
    perf=performance or {}
    pitch_ratio=_pitch_ratio(n,sr,perf)

    max_partials=max(1,int(graph.get("max_partials",18)))
    nyq=sr*.48
    pluck_pos=float(graph.get("pluck_position",0.18))
    pickup_pos=float(graph.get("pickup_position",0.22))
    rolloff=float(graph.get("partial_rolloff",1.08))
    inharm=max(0.0,float(graph.get("inharmonicity",0.000055)))
    base_decay=max(.05,float(graph.get("base_decay_s",1.55)))
    damping=max(0.0,float(graph.get("frequency_damping",0.20)))
    damping_power=max(.2,float(graph.get("damping_power",1.15)))
    keytrack=float(graph.get("decay_keytrack",0.010))
    decay_key_scale=2.0**(-keytrack*(int(midi)-40))

    sig=np.zeros(n,dtype=np.float64)
    norm=0.0
    for h in range(1,max_partials+1):
        # Slight stiffness-induced inharmonicity.  Keep it bounded so the note remains
        # recognisably bass-like rather than bell-like.
        harmonic_ratio=h*math.sqrt(1.0+inharm*h*h)
        freq=base*harmonic_ratio
        if freq>=nyq:
            break

        # Ideal plucked-string displacement and pickup sampling both have spatial
        # nulls.  Their product gives natural note-dependent spectral notches without
        # injecting unrelated fixed resonances.
        pluck=math.sin(math.pi*h*pluck_pos)
        pickup=math.sin(math.pi*h*pickup_pos)
        amp=(pluck*pickup)/(h**rolloff)
        norm+=abs(amp)

        # Higher modes lose energy faster.  This is the audible distinction missing
        # from the previous persistent sine/triangle generic bass.
        hf=(h-1)/max(1,max_partials-1)
        decay=base_decay*decay_key_scale/(1.0+damping*(h-1)**damping_power)
        decay=max(.025,decay)
        natural=np.exp(-t/decay)
        phase=2.0*np.pi*np.cumsum(freq*pitch_ratio)/sr
        sig+=amp*np.sin(phase)*natural

    if norm>1e-12:
        sig/=norm

    attack_scale=float(perf.get("attack_scale",1.0))
    release_scale=float(perf.get("release_scale",1.0))
    attack_s=max(.0004,float(graph.get("attack_s",0.006))*max(.4,attack_scale))
    attack=1.0-np.exp(-t/attack_s)
    release_s=max(.004,float(graph.get("release_s",0.075))*max(.25,release_scale))
    sig*=attack*_release_guard(n,sr,release_s)

    sig+=_finger_noise(n,sr,graph,int(midi),float(velocity),attack_scale)

    # Pickup/tone circuit: remove rumble and keep finger-style upper mids bounded.
    sig=_one_pole_highpass(sig,sr,float(graph.get("highpass_hz",24.0)))
    sig=_one_pole_lowpass(sig,sr,float(graph.get("pickup_lowpass_hz",4200.0)))
    drive=max(.05,float(graph.get("drive",1.12)))
    sig=np.tanh(sig*drive)/math.tanh(drive)

    sig*=float(velocity)*float(graph.get("output_gain",0.78))
    # Electric bass is mostly central; a tiny decorrelated high-passed side component
    # avoids a perfectly mathematical mono line without turning it into chorus.
    width=max(0.0,min(.25,float(graph.get("stereo_width",0.035))))
    side=_one_pole_highpass(sig,sr,float(graph.get("side_highpass_hz",650.0)))
    left=sig-side*width
    right=sig+side*width
    peak=max(float(np.max(np.abs(left))) if len(left) else 0.0,
             float(np.max(np.abs(right))) if len(right) else 0.0)
    if peak>1.0:
        left/=peak; right/=peak
    return np.stack([left,right],axis=1)


__all__=["render_plucked_bass_note"]
