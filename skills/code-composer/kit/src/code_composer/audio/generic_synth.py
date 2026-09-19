import math
import numpy as np
from scipy.signal import lfilter
from ..core.theory import midi_to_hz


def _waveform(kind: str, phase: np.ndarray) -> np.ndarray:
    x = phase / (2*np.pi)
    frac = x - np.floor(x)
    if kind == "sine":
        return np.sin(phase)
    if kind == "saw":
        return 2.0 * frac - 1.0
    if kind == "square":
        return np.where(frac < 0.5, 1.0, -1.0)
    if kind == "triangle":
        return 1.0 - 4.0 * np.abs(frac - 0.5)
    return np.sin(phase)


def _smoothstep01(x):
    x = np.clip(x, 0.0, 1.0)
    return x*x*(3.0-2.0*x)


def _adsr(n, sr, cfg):
    a=float(cfg.get("attack",0.01))
    d=float(cfg.get("decay",0.08))
    s=float(cfg.get("sustain",0.65))
    r=float(cfg.get("release",0.18))

    na=min(int(a*sr),n)
    nd=min(int(d*sr),max(0,n-na))
    nr=min(int(r*sr),max(0,n-na-nd))
    ns=max(0,n-na-nd-nr)

    env=np.zeros(n,dtype=np.float64)
    i=0
    if na:
        env[i:i+na]=_smoothstep01(np.linspace(0,1,na,endpoint=False)); i+=na
    if nd:
        u=_smoothstep01(np.linspace(0,1,nd,endpoint=False))
        env[i:i+nd]=1.0+(s-1.0)*u; i+=nd
    if ns:
        env[i:i+ns]=s; i+=ns
    if nr:
        u=_smoothstep01(np.linspace(0,1,nr))
        env[i:i+nr]=s*(1.0-u)
    return env


def _one_pole_lowpass(x, sr, cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    alpha=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([alpha], [1.0, -(1.0-alpha)], x)


def _one_pole_highpass(x, sr, cutoff):
    return x-_one_pole_lowpass(x,sr,cutoff)


def _apply_filter(sig, sr, cfg, env=None):
    if not cfg or cfg.get("type","none")=="none":
        return sig
    ftype=cfg.get("type","lowpass")
    cutoff=float(cfg.get("cutoff",18000.0))
    env_amount=float(cfg.get("env_amount",0.0))
    if ftype=="lowpass":
        base=_one_pole_lowpass(sig,sr,cutoff)
        if env is not None and abs(env_amount)>1e-9:
            mod_cutoff=max(40.0,cutoff*(1.0+env_amount))
            mod=_one_pole_lowpass(sig,sr,mod_cutoff)
            return base*(1-env)+mod*env
        return base
    if ftype=="highpass":
        return _one_pole_highpass(sig,sr,cutoff)
    if ftype=="bandpass":
        low=float(cfg.get("low_cutoff",cfg.get("low",300.0)))
        high=float(cfg.get("high_cutoff",cfg.get("high",7000.0)))
        return _one_pole_lowpass(_one_pole_highpass(sig,sr,low),sr,high)
    return sig


def _waveshape(sig, cfg):
    if not cfg or cfg.get("type","none")=="none":
        return sig
    kind=cfg.get("type","tanh")
    drive=float(cfg.get("drive",1.0))
    if kind=="tanh":
        return np.tanh(sig*drive)
    if kind=="softclip":
        x=sig*drive
        return x/(1.0+np.abs(x))
    return sig


def _normalize(sig):
    peak=np.max(np.abs(sig)) if len(sig) else 0.0
    if peak>1.0:
        sig=sig/peak
    return sig


def _pitch_envelope(n, sr, cfg):
    """Deterministic small pitch approach, useful for breath/pluck articulation."""
    if not cfg:
        return np.ones(n,dtype=np.float64)
    start=float(cfg.get("start_cents",0.0))
    end=float(cfg.get("end_cents",0.0))
    time_s=max(1e-5,float(cfg.get("time_s",0.04)))
    m=min(n,max(1,int(time_s*sr)))
    cents=np.full(n,end,dtype=np.float64)
    u=_smoothstep01(np.linspace(0,1,m,endpoint=True))
    cents[:m]=start+(end-start)*u
    return 2.0**(cents/1200.0)


def _declick_envelope(n, sr, cfg):
    ms=float(cfg.get("ms",0.0)) if cfg else 0.0
    if ms<=0:
        return np.ones(n,dtype=np.float64)
    m=min(n//2,max(1,int(ms*0.001*sr)))
    env=np.ones(n,dtype=np.float64)
    ramp=_smoothstep01(np.linspace(0,1,m,endpoint=True))
    env[:m]*=ramp
    env[-m:]*=ramp[::-1]
    return env


def _breath_layer(n, sr, cfg, midi, velocity):
    if not cfg or float(cfg.get("gain",0.0))<=0:
        return np.zeros(n,dtype=np.float64)
    seed=int(cfg.get("seed",41)) + int(midi)*1009 + int(n)%65521
    rng=np.random.default_rng(seed)
    noise=rng.standard_normal(n).astype(np.float64)
    low=float(cfg.get("low_cutoff",1400.0))
    high=float(cfg.get("high_cutoff",6500.0))
    noise=_one_pole_highpass(noise,sr,low)
    noise=_one_pole_lowpass(noise,sr,high)
    rms=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise=noise/rms

    attack=max(1,int(float(cfg.get("attack",0.035))*sr))
    release=max(1,int(float(cfg.get("release",0.06))*sr))
    env=np.ones(n,dtype=np.float64)
    ma=min(n,attack)
    mr=min(n,release)
    env[:ma]*=_smoothstep01(np.linspace(0,1,ma,endpoint=True))
    env[-mr:]*=_smoothstep01(np.linspace(1,0,mr,endpoint=True))
    # Keep breath subordinate and less velocity-sensitive than the pitched tone.
    gain=float(cfg.get("gain",0.012)) * max(0.2,float(velocity))**0.55
    return noise*env*gain


def _attack_partial(base_hz, n, sr, cfg):
    if not cfg or float(cfg.get("gain",0.0))<=0:
        return np.zeros(n,dtype=np.float64)
    harmonic=max(1.0,float(cfg.get("harmonic",2.0)))
    gain=float(cfg.get("gain",0.025))
    decay=max(1e-4,float(cfg.get("decay_s",0.045)))
    attack=max(1e-5,float(cfg.get("attack_s",0.004)))
    t=np.arange(n,dtype=np.float64)/sr
    amp=(1.0-np.exp(-t/attack))*np.exp(-t/decay)
    phase=2*np.pi*base_hz*harmonic*t
    return np.sin(phase)*amp*gain


def render_generic_note(midi: int, duration_s: float, sr: int, patch: dict, velocity: float = 1.0, performance: dict | None = None):
    """
    Render a serializable instrument graph to deterministic stereo samples.

    v1.5 optional performance/timbre blocks:
      - pitch_envelope: small deterministic pitch approach
      - breath: band-limited low-level air layer
      - attack_partial: tonal, decaying articulation (not broadband click noise)
      - declick: smooth whole-note onset/release guard

    No instrument behavior is inferred from a hard-coded preset name.
    """
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    base_hz=midi_to_hz(midi)

    graph=patch.get("graph",patch)
    performance=performance or {}
    oscillators=graph.get("oscillators") or [{"waveform":"sine","gain":1.0}]
    unison=graph.get("unison",{})
    voices=max(1,int(unison.get("voices",1)))
    detune_cents=float(unison.get("detune_cents",0.0))
    stereo_width=max(0.0,min(1.0,float(unison.get("stereo_width",0.0))))

    lfo=graph.get("lfo",{})
    lfo_rate=float(lfo.get("rate_hz",0.0))
    pitch_lfo_cents=float(lfo.get("pitch_cents",0.0))
    amp_lfo_depth=max(0.0,min(1.0,float(lfo.get("amp_depth",0.0))))
    lfo_wave=np.sin(2*np.pi*lfo_rate*t) if lfo_rate>0 else np.zeros(n)
    amp_mod=1.0-amp_lfo_depth*0.5+amp_lfo_depth*0.5*lfo_wave
    pitch_cfg=dict(graph.get("pitch_envelope",{}))
    if "pitch_start_cents" in performance:
        pitch_cfg["start_cents"]=performance["pitch_start_cents"]
        pitch_cfg["end_cents"]=performance.get("pitch_end_cents",0.0)
        pitch_cfg["time_s"]=performance.get("pitch_time_s",0.08)
    pitch_env_ratio=_pitch_envelope(n,sr,pitch_cfg)

    left=np.zeros(n,dtype=np.float64)
    right=np.zeros(n,dtype=np.float64)

    for osc in oscillators:
        waveform=osc.get("waveform","sine")
        gain=float(osc.get("gain",1.0))
        octave=int(osc.get("octave",0))
        semitone=float(osc.get("semitone",0.0))
        osc_detune=float(osc.get("detune_cents",0.0))
        phase_offset=float(osc.get("phase",0.0))

        for voice in range(voices):
            if voices==1:
                spread=0.0
                pan=0.0
            else:
                spread=(voice/(voices-1))*2.0-1.0
                pan=spread*stereo_width

            total_cents=osc_detune+spread*detune_cents
            pitch_ratio=2.0**((12*octave+semitone)/12.0)
            cents_ratio=2.0**(total_cents/1200.0)
            inst_ratio=2.0**((pitch_lfo_cents*lfo_wave)/1200.0)
            freq=base_hz*pitch_ratio*cents_ratio*inst_ratio*pitch_env_ratio
            phase=phase_offset+2*np.pi*np.cumsum(freq)/sr
            voice_sig=_waveform(waveform,phase)*gain/max(1,voices)

            angle=(pan+1.0)*math.pi/4.0
            left+=voice_sig*math.cos(angle)
            right+=voice_sig*math.sin(angle)

    # A tonal transient gives pluck definition without the popcorn/static behavior
    # of a broadband impulse/noise click.
    partial=_attack_partial(base_hz,n,sr,graph.get("attack_partial",{}))
    if np.any(partial):
        left+=partial*math.sqrt(0.5)
        right+=partial*math.sqrt(0.5)

    env_cfg=dict(graph.get("envelope",{}))
    if performance:
        env_cfg["attack"]=float(env_cfg.get("attack",0.01))*float(performance.get("attack_scale",1.0))
        env_cfg["release"]=float(env_cfg.get("release",0.18))*float(performance.get("release_scale",1.0))
    env=_adsr(n,sr,env_cfg)
    left*=env*amp_mod*velocity
    right*=env*amp_mod*velocity

    # Breath is added after tonal ADSR but has its own slower envelope. It is deliberately
    # band-limited and low-gain so it reads as air rather than static.
    breath=_breath_layer(n,sr,graph.get("breath",{}),midi,velocity)
    if np.any(breath):
        left+=breath*math.sqrt(0.5)
        right+=breath*math.sqrt(0.5)

    filt=graph.get("filter",{})
    left=_apply_filter(left,sr,filt,env)
    right=_apply_filter(right,sr,filt,env)

    ws=graph.get("waveshaper",{})
    left=_waveshape(left,ws)
    right=_waveshape(right,ws)

    guard=_declick_envelope(n,sr,graph.get("declick",{}))
    left*=guard
    right*=guard

    gain=float(graph.get("output_gain",1.0))
    left*=gain
    right*=gain

    stereo=np.stack([left,right],axis=1)
    return _normalize(stereo)


__all__ = ["render_generic_note"]
