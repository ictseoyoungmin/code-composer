import math
import numpy as np
from scipy.signal import lfilter
from .synth import equal_power_pan


def _rng(seed):
    return np.random.default_rng(seed & 0xFFFFFFFF)


def _one_pole_lowpass(x, sr, cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    alpha=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([alpha],[1.0,-(1.0-alpha)],x)


def _one_pole_highpass(x, sr, cutoff):
    return x-_one_pole_lowpass(x,sr,cutoff)


def _bandpass(x, sr, low, high):
    return _one_pole_lowpass(_one_pole_highpass(x,sr,low),sr,high)


def _softclip(x, drive=1.0):
    drive=max(1e-6,float(drive))
    return np.tanh(x*drive)/np.tanh(drive)


def _declick(x, sr, ms=1.2):
    if len(x)==0:
        return x
    m=min(len(x)//2,max(1,int(float(ms)*0.001*sr)))
    if m<=0:
        return x
    ramp=np.sin(np.linspace(0,np.pi/2,m))**2
    y=x.copy()
    y[:m]*=ramp
    y[-m:]*=ramp[::-1]
    return y


def _graph(patch):
    graph=(patch or {}).get("drum_graph",(patch or {}).get("graph",{}))
    return graph if isinstance(graph,dict) else {}


def _cfg(patch, kind):
    graph=_graph(patch)
    return graph.get(kind,{}) if isinstance(graph.get(kind,{}),dict) else {}


def _realism(patch):
    cfg=_graph(patch).get("realism_hardening",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _legacy_kick(duration_s, sr, velocity=1.0, patch=None):
    cfg=_cfg(patch,"kick")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr

    start_hz=float(cfg.get("pitch_start_hz",165.0))
    end_hz=float(cfg.get("pitch_end_hz",48.0))
    pitch_decay=max(1e-4,float(cfg.get("pitch_decay_s",0.045)))
    body_decay=max(1e-4,float(cfg.get("body_decay_s",0.095)))
    sub_decay=max(body_decay,float(cfg.get("sub_decay_s",0.140)))

    f=end_hz+(start_hz-end_hz)*np.exp(-t/pitch_decay)
    phase=2*np.pi*np.cumsum(f)/sr
    body=np.sin(phase)*np.exp(-t/body_decay)

    # A slower sub component gives weight without extending the click transient.
    sub_phase=2*np.pi*np.cumsum(np.maximum(end_hz*0.92,f*0.55))/sr
    sub=np.sin(sub_phase)*np.exp(-t/sub_decay)

    # Tonal beater, deliberately not broadband noise.
    click_hz=float(cfg.get("click_hz",2200.0))
    click_decay=max(1e-4,float(cfg.get("click_decay_s",0.010)))
    click_attack=max(1e-5,float(cfg.get("click_attack_s",0.0012)))
    click_env=(1.0-np.exp(-t/click_attack))*np.exp(-t/click_decay)
    click=np.sin(2*np.pi*click_hz*t)*click_env

    sig=(float(cfg.get("body_gain",0.92))*body
         +float(cfg.get("sub_gain",0.12))*sub
         +float(cfg.get("click_gain",0.055))*click)
    sig=_one_pole_lowpass(sig,sr,float(cfg.get("lowpass_hz",5200.0)))
    sig=_softclip(sig,float(cfg.get("drive",1.10)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.8)))
    return sig*float(velocity)*float(cfg.get("output_gain",0.92))


def _legacy_snare(duration_s, sr, velocity=1.0, seed=0, patch=None):
    cfg=_cfg(patch,"snare")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed)

    body_f1=float(cfg.get("body_hz",185.0))
    body_f2=float(cfg.get("body2_hz",335.0))
    body=(np.sin(2*np.pi*body_f1*t)
          +float(cfg.get("body2_gain",0.30))*np.sin(2*np.pi*body_f2*t+0.17))
    body*=np.exp(-t/max(1e-4,float(cfg.get("body_decay_s",0.085))))

    noise=rng.standard_normal(n).astype(np.float64)
    noise=_bandpass(noise,sr,float(cfg.get("noise_low_hz",1200.0)),float(cfg.get("noise_high_hz",9000.0)))
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise*=np.exp(-t/max(1e-4,float(cfg.get("noise_decay_s",0.060))))

    # Narrow tonal crack gives definition without an unbounded white-noise impulse.
    crack_hz=float(cfg.get("crack_hz",2700.0))
    crack=np.sin(2*np.pi*crack_hz*t+0.31)*np.exp(-t/max(1e-4,float(cfg.get("crack_decay_s",0.015))))

    sig=(float(cfg.get("body_gain",0.34))*body
         +float(cfg.get("noise_gain",0.48))*noise
         +float(cfg.get("crack_gain",0.055))*crack)
    sig=_one_pole_lowpass(sig,sr,float(cfg.get("lowpass_hz",10500.0)))
    sig=_softclip(sig,float(cfg.get("drive",1.08)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.65)))
    return sig*float(velocity)*float(cfg.get("output_gain",0.56))


def _legacy_hat(duration_s, sr, velocity=1.0, seed=0, patch=None):
    cfg=_cfg(patch,"hat")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed)

    # Inharmonic metallic cluster instead of only two fixed sinusoids.
    freqs=cfg.get("metal_freqs",[5600.0,7100.0,8450.0,10150.0,12300.0])
    gains=cfg.get("metal_gains",[1.0,0.72,0.48,0.32,0.20])
    metal=np.zeros(n,dtype=np.float64)
    for i,f in enumerate(freqs):
        g=float(gains[i]) if i<len(gains) else 0.2
        metal+=g*np.sin(2*np.pi*float(f)*t+i*0.73)
    metal/=max(1e-12,float(np.sum(np.abs(gains))))

    noise=rng.standard_normal(n).astype(np.float64)
    noise=_one_pole_highpass(noise,sr,float(cfg.get("noise_highpass_hz",5200.0)))
    noise=_one_pole_lowpass(noise,sr,float(cfg.get("noise_lowpass_hz",15000.0)))
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)

    decay=max(1e-4,float(cfg.get("decay_s",0.030)))
    env=np.exp(-t/decay)
    sig=(float(cfg.get("metal_gain",0.33))*metal
         +float(cfg.get("noise_gain",0.15))*noise)*env
    sig=_one_pole_highpass(sig,sr,float(cfg.get("output_highpass_hz",4300.0)))
    sig=_softclip(sig,float(cfg.get("drive",1.04)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.45)))
    return sig*float(velocity)*float(cfg.get("output_gain",0.36))


def _mode_sum(t, base_hz, ratios, gains, decays, *, phase_offsets=None, freq_scale=None):
    y=np.zeros(len(t),dtype=np.float64)
    if phase_offsets is None:
        phase_offsets=[0.0]*len(ratios)
    if freq_scale is None:
        freq_scale=np.ones(len(t),dtype=np.float64)
    for i,(ratio,gain,decay) in enumerate(zip(ratios,gains,decays)):
        f=base_hz*float(ratio)*freq_scale
        phase=2*np.pi*np.cumsum(f)/max(1.0,1.0/(t[1]-t[0]) if len(t)>1 else 1.0)
        # The caller normally supplies t = arange(n)/sr. Reconstructing sr this
        # way keeps this helper deterministic without another parameter.
        y+=float(gain)*np.sin(phase+float(phase_offsets[i]))*np.exp(-t/max(1e-5,float(decay)))
    return y


def _modal_signal(t, sr, base_hz, ratios, gains, decays, *, phase_offsets=None, freq_scale=None):
    y=np.zeros(len(t),dtype=np.float64)
    if phase_offsets is None:
        phase_offsets=[0.0]*len(ratios)
    if freq_scale is None:
        freq_scale=np.ones(len(t),dtype=np.float64)
    for i,(ratio,gain,decay) in enumerate(zip(ratios,gains,decays)):
        f=base_hz*float(ratio)*freq_scale
        phase=2*np.pi*np.cumsum(f)/sr
        y+=float(gain)*np.sin(phase+float(phase_offsets[i]))*np.exp(-t/max(1e-5,float(decay)))
    return y


def _variation(rng, amount):
    amount=max(0.0,float(amount))
    return 1.0+rng.uniform(-amount,amount)


def _modeled_kick(duration_s, sr, velocity, seed, patch, realism):
    cfg=_cfg(patch,"kick")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+101)
    v=max(0.0,min(1.25,float(velocity)))
    strike=float(realism.get("strike_variation",0.05))
    bright=float(realism.get("velocity_brightness",0.45))

    base=float(cfg.get("pitch_end_hz",48.0))*_variation(rng,strike*0.10)
    ratios=realism.get("kick_mode_ratios",[1.0,1.594,2.136,2.296,2.653])
    gains=np.asarray(realism.get("kick_mode_gains",[1.0,0.36,0.20,0.13,0.08]),dtype=np.float64)
    impact_shape=np.linspace(1.0,1.0+bright*(v-0.55),len(gains))
    gains=np.maximum(0.0,gains*impact_shape)
    gains*=np.asarray([_variation(rng,strike) for _ in gains])

    base_decay=float(cfg.get("body_decay_s",0.095))*1.45
    decays=[base_decay/(1.0+0.22*i) for i in range(len(ratios))]
    shift_cents=float(realism.get("kick_tension_shift_cents",65.0))*min(1.0,v)**1.7
    shift_ratio=2.0**(shift_cents/1200.0)-1.0
    tension_decay=max(1e-4,float(realism.get("kick_tension_decay_s",0.035)))
    freq_scale=1.0+shift_ratio*np.exp(-t/tension_decay)
    phases=rng.uniform(-0.15,0.15,len(ratios))
    body=_modal_signal(t,sr,base,ratios,gains,decays,phase_offsets=phases,freq_scale=freq_scale)

    # Cavity/sub energy is broad and short enough to avoid a separate pitched tail.
    sub_f=max(28.0,base*0.73)
    sub=np.sin(2*np.pi*sub_f*t+rng.uniform(-0.1,0.1))*np.exp(-t/max(.03,float(cfg.get("sub_decay_s",.14))))

    noise=rng.standard_normal(n).astype(np.float64)
    center=float(cfg.get("click_hz",2200.0))*(0.88+0.18*min(1.0,v))
    noise=_bandpass(noise,sr,max(180.0,center*0.38),min(sr*.46,center*2.2))
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
    attack=max(1e-5,float(cfg.get("click_attack_s",0.0012)))
    decay=max(1e-4,float(cfg.get("click_decay_s",0.010)))*(0.78+0.35*v)
    impact_env=(1.0-np.exp(-t/attack))*np.exp(-t/decay)
    beater=noise*impact_env

    sig=(float(cfg.get("body_gain",0.92))*0.72*body
         +float(cfg.get("sub_gain",0.12))*0.68*sub
         +float(realism.get("kick_beater_noise_gain",0.055))*beater)
    sig=_one_pole_lowpass(sig,sr,float(cfg.get("lowpass_hz",5200.0))*(0.86+0.20*min(1.0,v)))
    sig=_softclip(sig,float(cfg.get("drive",1.10)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.8)))
    return sig*v*float(cfg.get("output_gain",0.92))*0.92


def _modeled_snare(duration_s, sr, velocity, seed, patch, realism):
    cfg=_cfg(patch,"snare")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+211)
    v=max(0.0,min(1.25,float(velocity)))
    strike=float(realism.get("strike_variation",0.05))
    bright=float(realism.get("velocity_brightness",0.45))

    base=float(cfg.get("body_hz",185.0))*_variation(rng,strike*0.12)
    ratios=realism.get("snare_mode_ratios",[1.0,1.47,1.93,2.54])
    gains=np.asarray(realism.get("snare_mode_gains",[1.0,0.54,0.32,0.17]),dtype=np.float64)
    gains*=np.asarray([_variation(rng,strike) for _ in gains])
    gains*=np.linspace(1.0,1.0+bright*(v-0.50),len(gains))
    decay0=max(.02,float(cfg.get("body_decay_s",0.085)))*1.18
    decays=[decay0/(1.0+0.27*i) for i in range(len(ratios))]
    body=_modal_signal(t,sr,base,ratios,gains,decays,phase_offsets=rng.uniform(-.3,.3,len(ratios)))

    # Initial batter-head broadband strike.
    strike_noise=rng.standard_normal(n).astype(np.float64)
    lo=float(cfg.get("noise_low_hz",1200.0))*(0.86+0.18*v)
    hi=min(sr*.47,float(cfg.get("noise_high_hz",9000.0))*(0.88+0.20*v))
    strike_noise=_bandpass(strike_noise,sr,lo,hi)
    strike_noise/=float(np.sqrt(np.mean(strike_noise*strike_noise))+1e-12)
    strike_decay=max(.008,float(cfg.get("noise_decay_s",0.060)))*(0.70+0.34*v)
    strike_layer=strike_noise*np.exp(-t/strike_decay)

    # Deterministic stochastic snare-wire collision envelope. The low-passed
    # absolute noise avoids a periodic LFO while producing repeated contact bursts.
    mod=np.abs(rng.standard_normal(n).astype(np.float64))
    mod=_one_pole_lowpass(mod,sr,float(realism.get("snare_wire_rattle_hz",72.0)))
    mod-=float(np.min(mod))
    mod/=float(np.max(mod)+1e-12)
    delay=max(0,int(float(realism.get("snare_wire_delay_s",0.0025))*sr))
    wire_env=np.zeros(n,dtype=np.float64)
    if delay<n:
        tail_t=t[:n-delay]
        wire_env[delay:]=(0.30+0.70*mod[:n-delay])*np.exp(
            -tail_t/max(.01,float(realism.get("snare_wire_decay_s",0.18))*(0.78+0.36*v))
        )
    wire=rng.standard_normal(n).astype(np.float64)
    wire=_bandpass(wire,sr,max(900.0,lo*.72),min(sr*.47,hi*1.12))
    wire/=float(np.sqrt(np.mean(wire*wire))+1e-12)
    wire*=wire_env

    # Very short stick/crack impulse, noise-led instead of a persistent fixed tone.
    crack=rng.standard_normal(n).astype(np.float64)
    crack_center=float(cfg.get("crack_hz",2700.0))
    crack=_bandpass(crack,sr,max(250.0,crack_center*.55),min(sr*.47,crack_center*1.65))
    crack/=float(np.sqrt(np.mean(crack*crack))+1e-12)
    crack*=np.exp(-t/max(1e-4,float(cfg.get("crack_decay_s",0.015))))

    sig=(float(cfg.get("body_gain",0.34))*0.82*body
         +float(cfg.get("noise_gain",0.48))*0.64*strike_layer
         +float(realism.get("snare_wire_gain",0.38))*wire
         +float(cfg.get("crack_gain",0.055))*0.72*crack)
    sig=_one_pole_lowpass(sig,sr,float(cfg.get("lowpass_hz",10500.0))*(0.90+0.12*min(1.0,v)))
    sig=_softclip(sig,float(cfg.get("drive",1.08)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.65)))
    return sig*v*float(cfg.get("output_gain",0.56))*0.72


def _modeled_hat(duration_s, sr, velocity, seed, patch, realism):
    cfg=_cfg(patch,"hat")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+307)
    v=max(0.0,min(1.25,float(velocity)))
    strike=float(realism.get("strike_variation",0.05))
    bright=float(realism.get("velocity_brightness",0.45))
    jitter=float(realism.get("hat_mode_jitter",0.006))

    freqs=cfg.get("metal_freqs",[5600.0,7100.0,8450.0,10150.0,12300.0])
    gains=cfg.get("metal_gains",[1.0,0.72,0.48,0.32,0.20])
    base_decay=max(.004,float(cfg.get("decay_s",0.030)))
    vel_decay=1.0+float(realism.get("hat_decay_velocity_scale",0.55))*max(0.0,min(1.0,v)-0.45)
    metal=np.zeros(n,dtype=np.float64)
    total=0.0
    for i,f0 in enumerate(freqs):
        g=float(gains[i]) if i<len(gains) else 0.2
        g*=_variation(rng,strike)
        g*=1.0+bright*max(0.0,v-0.5)*(i/max(1,len(freqs)-1))
        f=float(f0)*_variation(rng,jitter)
        decay=base_decay*vel_decay*(0.72+0.18*i)
        metal+=g*np.sin(2*np.pi*f*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/decay)
        total+=abs(g)
    metal/=max(1e-12,total)

    noise=rng.standard_normal(n).astype(np.float64)
    hp=float(cfg.get("noise_highpass_hz",5200.0))*(0.96+0.05*min(1.0,v))
    lp=min(sr*.47,float(cfg.get("noise_lowpass_hz",15000.0))*(0.94+0.08*min(1.0,v)))
    noise=_one_pole_highpass(noise,sr,hp)
    noise=_one_pole_lowpass(noise,sr,lp)
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise_decay=base_decay*vel_decay*0.66
    noise*=np.exp(-t/noise_decay)

    sig=(float(cfg.get("metal_gain",0.33))*metal
         +float(cfg.get("noise_gain",0.15))*noise)
    sig=_one_pole_highpass(sig,sr,float(cfg.get("output_highpass_hz",4300.0)))
    sig=_softclip(sig,float(cfg.get("drive",1.04)))
    sig=_declick(sig,sr,float(cfg.get("declick_ms",0.45)))
    return sig*v*float(cfg.get("output_gain",0.36))*0.90



PERCUSSION_ARTICULATIONS = {
    "kick": ("default",),
    "snare": ("center", "ghost", "rimshot", "cross_stick"),
    "hat": ("closed", "half_open", "open", "pedal", "choke"),
    "ride": ("bow", "bell", "choke"),
    "crash": ("crash", "choke"),
    "tom_high": ("center", "edge"),
    "tom_mid": ("center", "edge"),
    "tom_floor": ("center", "edge"),
}

_DEFAULT_ARTICULATION = {
    "kick": "default",
    "snare": "center",
    "hat": "closed",
    "ride": "bow",
    "crash": "crash",
    "tom_high": "center",
    "tom_mid": "center",
    "tom_floor": "center",
}

_ARTICULATION_ALIASES = {
    "cross-stick": "cross_stick",
    "crossstick": "cross_stick",
    "half-open": "half_open",
    "halfopen": "half_open",
}


def supported_articulations():
    return {k: tuple(v) for k, v in PERCUSSION_ARTICULATIONS.items()}


def _articulation_foundation(patch):
    cfg=_graph(patch).get("articulation_foundation",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _acoustic_core(patch):
    cfg=_graph(patch).get("acoustic_core_hardening",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _voicing_polish(patch):
    cfg=_graph(patch).get("voicing_polish",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _cymbal_presence(patch):
    cfg=_graph(patch).get("cymbal_presence_hardening",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _coupled_membrane_bank(t, sr, base_hz, ratios, gains, decay_s, rng, *,
                           pair_split=.026, resonant_gain=.30, shell_gain=.08,
                           cavity_hz=None, cavity_gain=.08, velocity=1.0,
                           edge=False):
    """Reduced-order two-head + cavity + shell approximation.

    Each low membrane mode is split into a weakly coupled in/out-of-phase pair.
    This follows the physical observation that two drum heads coupled by the
    enclosed air do not retain one isolated resonance.  It is intentionally a
    compact modal approximation rather than a fitted or FDTD drum model.
    """
    y=np.zeros(len(t),dtype=np.float64)
    v=max(0.0,min(1.25,float(velocity)))
    total=0.0
    for i,(ratio,g0) in enumerate(zip(ratios,gains)):
        f0=float(base_hz)*float(ratio)*_variation(rng,.006+.002*i)
        # Coupling is strongest in the low modes and falls with mode order.
        split=float(pair_split)/(1.0+.28*i)
        f_lo=f0*(1.0-split)
        f_hi=f0*(1.0+split*.82)
        g=float(g0)*(1.0+(.10+.08*i)*max(0.0,v-.5))
        if edge:
            g*=.86+.08*i
        d=max(.015,float(decay_s)/(1.0+.20*i))
        p=rng.uniform(-np.pi,np.pi)
        # Lower pair: air-loaded/in-phase side, slightly longer lived.
        y+=g*np.sin(2*np.pi*f_lo*t+p)*np.exp(-t/(d*1.08))
        # Upper pair: compressed-cavity/out-of-phase side.
        y+=g*float(resonant_gain)*np.sin(2*np.pi*f_hi*t+p+1.31)*np.exp(-t/(d*.86))
        total+=abs(g)*(1.0+float(resonant_gain))
    y/=max(total,1e-12)

    # Shell modes are weak but break the "pure membrane sine bank" character.
    shell_base=max(120.0,float(base_hz)*2.65)
    shell=np.zeros(len(t),dtype=np.float64)
    for i,r in enumerate((1.0,1.37,1.91,2.63)):
        f=shell_base*r*_variation(rng,.012)
        d=max(.025,float(decay_s)*(.46-.055*min(i,3)))
        shell+=(1.0/(1.0+.65*i))*np.sin(2*np.pi*f*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/d)
    shell/=2.25

    if cavity_hz is None:
        cavity_hz=max(42.0,float(base_hz)*.68)
    cavity=(np.sin(2*np.pi*float(cavity_hz)*t+rng.uniform(-.3,.3))
            +.32*np.sin(2*np.pi*float(cavity_hz)*1.73*t+rng.uniform(-.5,.5)))
    cavity*=np.exp(-t/max(.035,float(decay_s)*1.18))
    return y+float(shell_gain)*shell+float(cavity_gain)*cavity


def _dense_plate_field(t, sr, rng, *, low_hz, high_hz, mode_count, decay_s,
                       pair_spread=.0055, brightness=0.5, focus_hz=None,
                       velocity=1.0):
    """Dense deterministic inharmonic plate field for cymbal-like sources.

    A compact bank of paired, slightly split modes creates the dense beating
    missing from a handful of fixed sinusoids.  Frequencies are generated from
    a deterministic non-harmonic distribution and remain below Nyquist.
    """
    n=max(8,int(mode_count))
    hi=min(float(high_hz),sr*.47)
    lo=min(max(80.0,float(low_hz)),hi*.92)
    v=max(0.0,min(1.25,float(velocity)))
    y=np.zeros(len(t),dtype=np.float64)
    total=0.0
    ratio=hi/lo
    for i in range(n):
        u=(i+.43)/n
        # Curved log distribution: dense, not a harmonic ladder.
        warped=u**(.78+0.10*math.sin((i+1)*1.71))
        f=lo*(ratio**warped)*_variation(rng,.009)
        spread=float(pair_spread)*(0.55+.85*u)*_variation(rng,.12)
        g=math.exp(-1.22*u)*(0.72+0.28*math.sin((i+1)*2.17)**2)
        if focus_hz:
            oct_dist=abs(math.log(max(f,1.0)/float(focus_hz),2.0))
            g*=.62+.78*math.exp(-1.4*oct_dist)
        g*=1.0+float(brightness)*max(0.0,v-.45)*u
        d=float(decay_s)*(1.08-.50*u)*_variation(rng,.12)
        p=rng.uniform(-np.pi,np.pi)
        # Closely spaced pairs create natural-looking beating without an LFO.
        y+=g*np.sin(2*np.pi*f*(1.0-spread)*t+p)*np.exp(-t/max(.012,d*1.04))
        y+=g*(.54+.18*u)*np.sin(2*np.pi*f*(1.0+spread*.83)*t+p+1.07)*np.exp(-t/max(.010,d*.92))
        total+=abs(g)*(1.54+.18*u)
    return y/max(total,1e-12)


def _core_drum_head(kind, duration_s, sr, velocity, seed, patch, art, core):
    cfg=_cfg(patch,kind)
    acfg=_articulation_foundation(patch) or {}
    polish=_voicing_polish(patch) or {}
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    offsets={"kick":1101,"snare":1201,"tom_high":1301,"tom_mid":1321,"tom_floor":1341}
    rng=_rng(seed+offsets[kind])
    v=max(0.0,min(1.25,float(velocity)))
    edge=art=="edge"

    if kind=="kick":
        base=float(cfg.get("pitch_end_hz",48.0))
        ratios=_realism(patch).get("kick_mode_ratios",[1.0,1.594,2.136,2.296,2.653])
        gains=_realism(patch).get("kick_mode_gains",[1.0,.36,.20,.13,.08])
        decay=float(cfg.get("body_decay_s",.105))*1.65
        cavity_hz=float(core.get("kick_cavity_hz",63.0))
        body=_coupled_membrane_bank(
            t,sr,base,ratios,gains,decay,rng,
            pair_split=float(core.get("kick_head_pair_split",.038)),
            resonant_gain=float(core.get("kick_resonant_head_gain",.34)),
            shell_gain=float(core.get("kick_shell_gain",.055)),
            cavity_hz=cavity_hz,cavity_gain=float(core.get("kick_cavity_gain",.16)),
            velocity=v,
        )
        # Felt/beater contact: short broadband force with velocity-dependent bandwidth.
        hit=_normalized_noise(rng,n)
        hit=_bandpass(hit,sr,450.0,min(sr*.47,2600.0+3200.0*min(1.0,v)))
        hit/=float(np.sqrt(np.mean(hit*hit))+1e-12)
        hit*=np.exp(-t/(.0065+.0025*v))
        if polish:
            hit=_one_pole_lowpass(hit,sr,float(polish.get("kick_contact_lowpass_hz",3900.0)))
        hit_scale=float(polish.get("kick_contact_gain_scale",1.0)) if polish else 1.0
        body_scale=float(polish.get("kick_body_gain_scale",1.0)) if polish else 1.0
        sig=.88*body*body_scale+float(core.get("kick_contact_gain",.075))*hit*hit_scale
        sig=_one_pole_lowpass(sig,sr,5200.0+1000.0*min(1.0,v))
        sig=_softclip(sig,1.045)
        sig=_declick(sig,sr,.7)
        return sig*v*float(cfg.get("output_gain",1.0166))*1.18

    if kind=="snare":
        base=float(cfg.get("body_hz",185.0))
        ratios=_realism(patch).get("snare_mode_ratios",[1.0,1.47,1.93,2.54])
        gains=_realism(patch).get("snare_mode_gains",[1.0,.54,.32,.17])
        decay=float(cfg.get("body_decay_s",.085))*1.36
        body=_coupled_membrane_bank(
            t,sr,base,ratios,gains,decay,rng,
            pair_split=float(core.get("snare_head_pair_split",.030)),
            resonant_gain=float(core.get("snare_resonant_head_gain",.42)),
            shell_gain=float(core.get("snare_shell_gain",.11)),
            cavity_hz=float(core.get("snare_cavity_hz",116.0)),
            cavity_gain=float(core.get("snare_cavity_gain",.075)),velocity=v,
        )
        # Resonant-head proxy drives the wires, so rattle follows drum energy instead
        # of being an unrelated independent noise tail.
        resonant=np.abs(body)
        driver=_one_pole_lowpass(resonant,sr,float(core.get("snare_wire_driver_hz",115.0)))
        driver/=float(np.max(driver)+1e-12)
        wire=_normalized_noise(rng,n)
        wire=_bandpass(wire,sr,1500.0,min(sr*.47,11500.0))
        wire/=float(np.sqrt(np.mean(wire*wire))+1e-12)
        delay=max(0,int(float(core.get("snare_wire_delay_s",.0018))*sr))
        env=np.zeros(n,dtype=np.float64)
        if delay<n:
            env[delay:]=driver[:n-delay]*np.exp(-t[:n-delay]/float(core.get("snare_wire_decay_s",.24)))
        wire*=env
        if polish:
            wire=_one_pole_lowpass(wire,sr,float(polish.get("snare_wire_lowpass_hz",9200.0)))
        impact=_normalized_noise(rng,n)
        impact=_bandpass(impact,sr,700.0,min(sr*.47,9800.0))
        impact/=float(np.sqrt(np.mean(impact*impact))+1e-12)
        impact*=np.exp(-t/(.010+.004*v))
        if polish:
            impact=_one_pole_lowpass(impact,sr,float(polish.get("snare_impact_lowpass_hz",8600.0)))
        body_scale=float(polish.get("snare_body_gain_scale",1.0)) if polish else 1.0
        wire_scale=float(polish.get("snare_wire_gain_scale",1.0)) if polish else 1.0
        impact_scale=float(polish.get("snare_impact_gain_scale",1.0)) if polish else 1.0
        sig=.66*body*body_scale+float(core.get("snare_wire_coupling_gain",.44))*wire*wire_scale+.15*impact*impact_scale
        sig=_one_pole_lowpass(sig,sr,min(sr*.46,11800.0))
        sig=_softclip(sig,1.035)
        sig=_declick(sig,sr,.6)
        return sig*v*float(cfg.get("output_gain",.6188))*1.32

    defaults={"tom_high":180.0,"tom_mid":132.0,"tom_floor":88.0}
    base=float(cfg.get("base_hz",defaults[kind]))
    ratios=cfg.get("mode_ratios",[1.0,1.59,2.14,2.30,2.65])
    gains=cfg.get("edge_mode_gains" if edge else "center_mode_gains",
                  [.72,.58,.46,.28,.16] if edge else [1.0,.38,.20,.13,.08])
    decay=float(cfg.get("decay_s",.48 if kind!="tom_floor" else .62))*(.84 if edge else 1.0)
    cavity_defaults={"tom_high":205.0,"tom_mid":148.0,"tom_floor":92.0}
    body=_coupled_membrane_bank(
        t,sr,base,ratios,gains,decay,rng,
        pair_split=float(core.get("tom_head_pair_split",.028)),
        resonant_gain=float(core.get("tom_resonant_head_gain",.36)),
        shell_gain=float(core.get("tom_shell_gain",.095)),
        cavity_hz=float(core.get(f"{kind}_cavity_hz",cavity_defaults[kind])),
        cavity_gain=float(core.get("tom_cavity_gain",.095)),velocity=v,edge=edge,
    )
    impact=_normalized_noise(rng,n)
    impact=_bandpass(impact,sr,650.0 if edge else 260.0,min(sr*.47,7800.0 if edge else 5900.0))
    impact/=float(np.sqrt(np.mean(impact*impact))+1e-12)
    impact*=np.exp(-t/(.015 if edge else .021))
    if polish:
        impact=_one_pole_lowpass(impact,sr,float(polish.get("tom_impact_lowpass_hz",6200.0)))
    impact_scale=float(polish.get("tom_impact_gain_scale",1.0)) if polish else 1.0
    body_scale=float(polish.get("tom_body_gain_scale",1.0)) if polish else 1.0
    sig=(.82 if edge else .91)*body*body_scale+(.12 if edge else .085)*impact*impact_scale
    sig=_one_pole_lowpass(sig,sr,min(sr*.46,float(cfg.get("lowpass_hz",7600.0))))
    sig=_softclip(sig,1.035)
    sig=_declick(sig,sr,.55)
    return sig*v*float(cfg.get("output_gain",.46))*float(acfg.get("tom_edge_gain",.82) if edge else 1.0)*1.13


def _core_cymbal(kind, duration_s, sr, velocity, seed, patch, art, core):
    cfg=_cfg(patch,kind if kind in {"ride","crash"} else "hat")
    acfg=_articulation_foundation(patch) or {}
    polish=_voicing_polish(patch) or {}
    presence=_cymbal_presence(patch) or {}
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+{"hat":1501,"ride":1601,"crash":1701}[kind])
    v=max(0.0,min(1.25,float(velocity)))

    # Keep S20 contact articulations: S21 is the free-vibration acoustic core.
    if art=="choke":
        if kind=="hat":
            return _hat_articulation(duration_s,sr,velocity,seed,patch,_realism(patch),art)
        return _cymbal_articulation(kind,duration_s,sr,velocity,seed,patch,art)
    if kind=="hat" and art=="pedal":
        return _hat_articulation(duration_s,sr,velocity,seed,patch,_realism(patch),art)

    mode_count=int(core.get("cymbal_mode_count",34))
    spread=float(core.get("cymbal_pair_spread",.0058))
    if kind=="hat":
        if art=="closed":
            low,high,decay,focus,out=3200.0,11200.0,.070,6800.0,.44
        elif art=="half_open":
            low,high,decay,focus,out=2300.0,11300.0,.38,5900.0,.40
        else:
            low,high,decay,focus,out=1700.0,11400.0,.92,5200.0,.38
        modes=max(20,mode_count-8)
        hp=2100.0 if art=="open" else 3000.0
    elif kind=="ride":
        if art=="bell":
            low,high,decay,focus,out=1800.0,11200.0,.86,5200.0,.39
            modes=max(22,mode_count-4); hp=1250.0
        else:
            low,high,decay,focus,out=780.0,11000.0,1.45,3200.0,.34
            modes=mode_count; hp=720.0
    else:
        low,high,decay,focus,out=420.0,11400.0,1.85,2700.0,.36
        modes=mode_count+6; hp=380.0

    plate=_dense_plate_field(
        t,sr,rng,low_hz=low,high_hz=high,mode_count=modes,decay_s=decay,
        pair_spread=spread,brightness=float(core.get("cymbal_velocity_brightness",.62)),
        focus_hz=focus,velocity=v,
    )
    # Broadband excitation is subordinate to the plate field.  S24 optionally
    # colors and amplitude-modulates the wash from modal energy so it reads as
    # metal turbulence rather than an independent white/static-noise layer.
    noise=_normalized_noise(rng,n)
    if presence:
        low1=max(float(presence.get("wash_low_hz",1800.0)),hp*.82)
        mid=float(presence.get("wash_mid_hz",4800.0))
        high=min(sr*.47,float(presence.get("wash_high_hz",9800.0)))
        b1=_bandpass(noise,sr,low1,min(mid,high*.92))
        b2=_bandpass(noise,sr,max(low1*1.25,mid*.82),high)
        noise=float(presence.get("wash_low_band_mix",.68))*b1+float(presence.get("wash_high_band_mix",.32))*b2
    else:
        noise=_one_pole_highpass(noise,sr,hp)
        noise=_one_pole_lowpass(noise,sr,min(sr*.47,11600.0))
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
    if presence:
        modal_env=_one_pole_lowpass(np.abs(plate),sr,float(presence.get("wash_envelope_hz",170.0)))
        modal_env/=float(np.max(modal_env)+1e-12)
        corr=float(presence.get("wash_modal_correlation",.82))
        noise*=((1.0-corr)+corr*modal_env)
        wash_attack=max(1e-5,float(presence.get("wash_attack_ms",5.5))*.001)
        noise*=1.0-np.exp(-t/wash_attack)
    noise*=np.exp(-t/(decay*float(core.get("cymbal_noise_decay_ratio",.54))))
    contact=_normalized_noise(rng,n)
    contact=_bandpass(contact,sr,max(650.0,hp*.8),min(sr*.47,10500.0))
    contact/=float(np.sqrt(np.mean(contact*contact))+1e-12)
    contact*=np.exp(-t/(.006 if kind!="crash" else .010))
    if polish:
        contact=_one_pole_lowpass(contact,sr,float(polish.get("cymbal_contact_lowpass_hz",9600.0)))
    modal_scale=float(polish.get("cymbal_modal_gain_scale",1.0)) if polish else 1.0
    noise_scale=float(polish.get("cymbal_noise_gain_scale",1.0)) if polish else 1.0
    contact_scale=float(polish.get("cymbal_contact_gain_scale",1.0)) if polish else 1.0
    if presence:
        modal_scale*=float(presence.get("modal_body_gain_scale",1.28))
        noise_scale*=float(presence.get("wash_gain_scale",.55))
        contact_scale*=float(presence.get("contact_gain_scale",1.22))
    sig=plate*float(core.get("cymbal_modal_gain",.78))*modal_scale+noise*float(core.get("cymbal_noise_gain",.16))*noise_scale+contact*.055*contact_scale
    if presence:
        # Short-lived mid/upper-metal reinforcement makes the strike read as a
        # cymbal body before the wash develops. It is derived from the modal
        # plate signal, not from a new stochastic source.
        p_lo=float(presence.get("presence_low_hz",1800.0))
        p_hi=min(sr*.46,float(presence.get("presence_high_hz",7600.0)))
        metal=_bandpass(plate,sr,p_lo,p_hi)
        metal*=np.exp(-t/max(.01,float(presence.get("presence_decay_s",.115))))
        sig+=metal*float(presence.get("presence_gain",.42))
    if polish:
        hf_cut=float(polish.get("cymbal_hf_damping_hz",9000.0))
        hf=_one_pole_highpass(sig,sr,hf_cut)
        hf_decay=max(.02,decay*float(polish.get("cymbal_hf_decay_ratio",.34)))
        sig=(sig-hf)+hf*np.exp(-t/hf_decay)
        attack=max(1e-5,float(polish.get("cymbal_attack_glue_ms",.7))*.001)
        sig*=float(polish.get("cymbal_initial_gain",.82))+(1.0-float(polish.get("cymbal_initial_gain",.82)))*(1.0-np.exp(-t/attack))
    sig=_one_pole_highpass(sig,sr,hp*.78)
    sig=_softclip(sig,1.018)
    sig=_declick(sig,sr,.38)
    # Preserve articulation-level loudness relationships from S20.
    if kind=="hat":
        gain={"closed":float(cfg.get("output_gain",.3978))*1.12,
              "half_open":float(acfg.get("hat_half_open_gain",.36))*1.05,
              "open":float(acfg.get("hat_open_gain",.34))*1.06}[art]
    elif kind=="ride":
        gain=float(cfg.get("bell_output_gain",.34) if art=="bell" else cfg.get("bow_output_gain",.30))*1.18
    else:
        gain=float(cfg.get("output_gain",.30))*1.15
    if presence:
        kind_gain={
            "hat": float(presence.get("hat_output_gain_scale",1.12)),
            "ride": float(presence.get("ride_output_gain_scale",1.20)),
            "crash": float(presence.get("crash_output_gain_scale",1.28)),
        }[kind]
        gain*=kind_gain
    return sig*v*gain*out/.40


def _core_snare_noncenter(duration_s, sr, velocity, seed, patch, realism, art, core):
    # Start from S20 articulation identity, then couple in a little shell/head body
    # so rim/wood articulations do not sound like isolated toy tone clusters.
    base=_snare_articulation(duration_s,sr,velocity,seed,patch,realism,art)
    if art=="ghost":
        body=_core_drum_head("snare",duration_s,sr,min(float(velocity),.55),seed+31,patch,"center",core)
        return .58*base+.34*body
    if art=="rimshot":
        body=_core_drum_head("snare",duration_s,sr,min(float(velocity),1.0),seed+41,patch,"center",core)
        return .72*base+.23*body
    # cross-stick gets shell/cavity coloration but no wire-heavy center hit.
    cfg=_cfg(patch,"snare")
    n=max(1,int(duration_s*sr)); t=np.arange(n,dtype=np.float64)/sr; rng=_rng(seed+1451)
    shell=np.zeros(n,dtype=np.float64)
    for f,g,d in ((620,.8,.075),(980,.55,.060),(1560,.32,.043),(2480,.18,.030)):
        shell+=g*np.sin(2*np.pi*f*_variation(rng,.012)*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/d)
    shell/=1.85
    return .78*base+.13*shell*float(velocity)*float(cfg.get("output_gain",.6188))

def _normalize_articulation(kind, articulation):
    if kind not in PERCUSSION_ARTICULATIONS:
        return None
    if articulation in (None, "", "default"):
        return _DEFAULT_ARTICULATION[kind]
    art=_ARTICULATION_ALIASES.get(str(articulation),str(articulation))
    if art not in PERCUSSION_ARTICULATIONS[kind]:
        raise ValueError(f"unsupported percussion articulation for {kind}: {articulation!r}")
    return art


def _normalized_noise(rng, n):
    x=rng.standard_normal(n).astype(np.float64)
    return x/float(np.sqrt(np.mean(x*x))+1e-12)


def _snare_articulation(duration_s, sr, velocity, seed, patch, realism, art):
    if art == "center":
        return _modeled_snare(duration_s,sr,velocity,seed,patch,realism)
    cfg=_cfg(patch,"snare")
    acfg=_articulation_foundation(patch) or {}
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+421)
    v=max(0.0,min(1.25,float(velocity)))

    if art == "ghost":
        # Ghost strokes retain head/wire identity but cap the excitation and crack.
        gv=min(v,0.58)
        base=float(cfg.get("body_hz",185.0))*_variation(rng,0.012)
        body=_modal_signal(
            t,sr,base,[1.0,1.47,1.93],[1.0,0.34,0.16],[0.075,0.055,0.040],
            phase_offsets=rng.uniform(-.2,.2,3),
        )
        noise=_normalized_noise(rng,n)
        noise=_bandpass(noise,sr,900.0,min(sr*.47,7200.0))
        noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
        noise*=np.exp(-t/.045)
        wire=_normalized_noise(rng,n)
        wire=_bandpass(wire,sr,1500.0,min(sr*.47,9200.0))
        wire/=float(np.sqrt(np.mean(wire*wire))+1e-12)
        wire*=np.exp(-t/.105)
        sig=.31*body+.22*noise+.16*wire
        sig=_one_pole_lowpass(sig,sr,min(sr*.46,9000.0))
        sig=_softclip(sig,1.03)
        sig=_declick(sig,sr,.65)
        return sig*gv*float(acfg.get("snare_ghost_gain",0.62))*float(cfg.get("output_gain",0.56))

    if art == "rimshot":
        # Coupled head + rim strike: short shell/rim modes above a reduced head response.
        head=_modeled_snare(duration_s,sr,min(1.0,v),seed+7,patch,realism)
        freqs=[760.0,1430.0,2760.0,4890.0]
        decays=[.080,.055,.036,.022]
        gains=[1.0,.72,.42,.24]
        rim=np.zeros(n,dtype=np.float64)
        for i,(f,d,g) in enumerate(zip(freqs,decays,gains)):
            f*= _variation(rng,.012)
            rim+=g*np.sin(2*np.pi*f*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/d)
        rim/=sum(gains)
        click=_normalized_noise(rng,n)
        click=_bandpass(click,sr,1800.0,min(sr*.47,11000.0))
        click/=float(np.sqrt(np.mean(click*click))+1e-12)
        click*=np.exp(-t/.012)
        sig=.32*head+.62*rim+.18*click
        sig=_softclip(sig,1.12)
        sig=_declick(sig,sr,.5)
        return sig*v*float(acfg.get("snare_rimshot_gain",0.90))

    # cross_stick: wood/rim contact with only a small shell contribution.
    freqs=[930.0,1810.0,3290.0,5150.0]
    gains=[1.0,.68,.38,.18]
    decays=[.070,.050,.032,.020]
    wood=np.zeros(n,dtype=np.float64)
    for f,g,d in zip(freqs,gains,decays):
        wood+=g*np.sin(2*np.pi*f*_variation(rng,.01)*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/d)
    wood/=sum(gains)
    body=np.sin(2*np.pi*float(cfg.get("body_hz",185.0))*t)*np.exp(-t/.045)
    tick=_normalized_noise(rng,n)
    tick=_bandpass(tick,sr,1200.0,min(sr*.47,8500.0))
    tick/=float(np.sqrt(np.mean(tick*tick))+1e-12)
    tick*=np.exp(-t/.008)
    sig=.70*wood+.11*body+.12*tick
    sig=_softclip(sig,1.04)
    sig=_declick(sig,sr,.45)
    return sig*v*float(acfg.get("snare_cross_stick_gain",0.72))


def _hat_articulation(duration_s, sr, velocity, seed, patch, realism, art):
    if art == "closed":
        return _modeled_hat(duration_s,sr,velocity,seed,patch,realism)
    cfg=_cfg(patch,"hat")
    acfg=_articulation_foundation(patch) or {}
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+509)
    v=max(0.0,min(1.25,float(velocity)))

    if art in {"half_open","open"}:
        openness=.52 if art=="half_open" else 1.0
        freqs=cfg.get("metal_freqs",[5600.0,7100.0,8450.0,10150.0,11200.0])
        gains=cfg.get("metal_gains",[1.0,.72,.48,.32,.20])
        # Open hats expose lower plate modes and a much longer noisy wash.
        extra=[3100.0,4050.0] if openness>.8 else [3900.0]
        all_freqs=extra+list(freqs)
        all_gains=([.46,.34] if openness>.8 else [.34])+list(gains)
        base_decay=float(acfg.get("hat_half_open_decay_s",.22) if art=="half_open" else acfg.get("hat_open_decay_s",.62))
        metal=np.zeros(n,dtype=np.float64)
        total=0.0
        for i,(f0,g0) in enumerate(zip(all_freqs,all_gains)):
            g=float(g0)*_variation(rng,.05)
            decay=base_decay*(.72+.08*i)*(1.0+.22*max(0.0,v-.5))
            metal+=g*np.sin(2*np.pi*float(f0)*_variation(rng,.007)*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/decay)
            total+=abs(g)
        metal/=max(total,1e-12)
        noise=_normalized_noise(rng,n)
        hp=3000.0 if art=="open" else 3900.0
        noise=_one_pole_highpass(noise,sr,hp)
        noise=_one_pole_lowpass(noise,sr,min(sr*.47,11600.0))
        noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
        noise*=np.exp(-t/(base_decay*(.74 if art=="open" else .60)))
        sig=(.39+.08*openness)*metal+(.17+.08*openness)*noise
        sig=_one_pole_highpass(sig,sr,2500.0 if art=="open" else 3400.0)
        sig=_softclip(sig,1.025)
        sig=_declick(sig,sr,.4)
        gain=float(acfg.get("hat_open_gain",0.34) if art=="open" else acfg.get("hat_half_open_gain",0.36))
        return sig*v*gain

    if art == "pedal":
        # Foot chick: two plates collide and damp almost immediately.
        noise=_normalized_noise(rng,n)
        noise=_bandpass(noise,sr,2500.0,min(sr*.47,10500.0))
        noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
        noise*=np.exp(-t/.026)
        metal=(np.sin(2*np.pi*4100*t)+.55*np.sin(2*np.pi*7350*t+.4))*np.exp(-t/.038)
        sig=.34*noise+.20*metal
        sig=_declick(_softclip(sig,1.02),sr,.35)
        return sig*v*float(acfg.get("hat_pedal_gain",0.27))

    # Choke is an explicit hand-contact articulation only in S20. It does not yet
    # terminate a previously rendered cymbal; stateful muting is S22.
    contact=_normalized_noise(rng,n)
    contact=_bandpass(contact,sr,900.0,min(sr*.47,8200.0))
    contact/=float(np.sqrt(np.mean(contact*contact))+1e-12)
    contact*=np.exp(-t/.018)
    ring=(np.sin(2*np.pi*3300*t)+.35*np.sin(2*np.pi*6100*t+.7))*np.exp(-t/.030)
    sig=.27*contact+.12*ring
    sig=_declick(_softclip(sig,1.01),sr,.3)
    return sig*v*float(acfg.get("hat_choke_gain",0.22))


def _cymbal_articulation(kind, duration_s, sr, velocity, seed, patch, art):
    cfg=_cfg(patch,kind)
    acfg=_articulation_foundation(patch) or {}
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+(601 if kind=="ride" else 701))
    v=max(0.0,min(1.25,float(velocity)))

    if art == "choke":
        contact=_normalized_noise(rng,n)
        contact=_bandpass(contact,sr,700.0,min(sr*.47,9000.0))
        contact/=float(np.sqrt(np.mean(contact*contact))+1e-12)
        contact*=np.exp(-t/.022)
        ring=np.sin(2*np.pi*(2300.0 if kind=="ride" else 1800.0)*t)*np.exp(-t/.040)
        sig=.24*contact+.10*ring
        return _declick(_softclip(sig,1.015),sr,.35)*v*float(acfg.get("cymbal_choke_gain",.24))

    if kind == "ride":
        bell = art == "bell"
        freqs=cfg.get("bell_freqs" if bell else "bow_freqs",
                      [3180.0,4780.0,6620.0,8460.0,10700.0] if bell else [1350.0,2260.0,3560.0,5230.0,7480.0,10100.0])
        gains=cfg.get("bell_gains" if bell else "bow_gains",
                      [1.0,.78,.54,.32,.18] if bell else [1.0,.78,.56,.36,.22,.12])
        base_decay=float(cfg.get("bell_decay_s",.72) if bell else cfg.get("bow_decay_s",1.15))
        noise_gain=float(cfg.get("bell_noise_gain",.075) if bell else cfg.get("bow_noise_gain",.13))
        tonal_gain=float(cfg.get("bell_tonal_gain",.64) if bell else cfg.get("bow_tonal_gain",.40))
        out_gain=float(cfg.get("bell_output_gain",.34) if bell else cfg.get("bow_output_gain",.30))
        hp=1200.0 if bell else 900.0
    else:
        freqs=cfg.get("freqs",[780.0,1260.0,2110.0,3380.0,5120.0,7460.0,10150.0])
        gains=cfg.get("gains",[1.0,.84,.66,.49,.34,.22,.12])
        base_decay=float(cfg.get("decay_s",1.35))
        noise_gain=float(cfg.get("noise_gain",.21))
        tonal_gain=float(cfg.get("tonal_gain",.34))
        out_gain=float(cfg.get("output_gain",.30))
        hp=650.0

    metal=np.zeros(n,dtype=np.float64)
    total=0.0
    for i,(f0,g0) in enumerate(zip(freqs,gains)):
        g=float(g0)*_variation(rng,.045)
        decay=base_decay*(.70+.085*i)*(1.0+.18*max(0.0,v-.5))
        metal+=g*np.sin(2*np.pi*float(f0)*_variation(rng,.006)*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/decay)
        total+=abs(g)
    metal/=max(total,1e-12)
    noise=_normalized_noise(rng,n)
    noise=_one_pole_highpass(noise,sr,hp)
    noise=_one_pole_lowpass(noise,sr,min(sr*.47,11500.0))
    noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise*=np.exp(-t/(base_decay*.62))
    sig=tonal_gain*metal+noise_gain*noise
    sig=_one_pole_highpass(sig,sr,hp*.82)
    sig=_softclip(sig,1.02)
    sig=_declick(sig,sr,.4)
    return sig*v*out_gain


def _tom_articulation(kind, duration_s, sr, velocity, seed, patch, art):
    cfg=_cfg(patch,kind)
    acfg=_articulation_foundation(patch) or {}
    defaults={"tom_high":180.0,"tom_mid":132.0,"tom_floor":88.0}
    base=float(cfg.get("base_hz",defaults[kind]))
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+811+{"tom_high":0,"tom_mid":17,"tom_floor":29}[kind])
    v=max(0.0,min(1.25,float(velocity)))
    edge=art=="edge"
    ratios=cfg.get("mode_ratios",[1.0,1.59,2.14,2.30,2.65])
    gains=np.asarray(cfg.get("edge_mode_gains" if edge else "center_mode_gains",
                             [.72,.58,.46,.28,.16] if edge else [1.0,.38,.20,.13,.08]),dtype=np.float64)
    gains*=np.asarray([_variation(rng,.04) for _ in gains])
    decay0=float(cfg.get("decay_s",.48 if kind!="tom_floor" else .62))*(.82 if edge else 1.0)
    decays=[decay0/(1.0+.18*i) for i in range(len(ratios))]
    shift_cents=float(cfg.get("tension_shift_cents",38.0))*min(1.0,v)**1.5
    shift_ratio=2.0**(shift_cents/1200.0)-1.0
    freq_scale=1.0+shift_ratio*np.exp(-t/max(.008,float(cfg.get("tension_decay_s",.055))))
    body=_modal_signal(t,sr,base,ratios,gains,decays,phase_offsets=rng.uniform(-.22,.22,len(ratios)),freq_scale=freq_scale)
    impact=_normalized_noise(rng,n)
    lo=700.0 if edge else 350.0
    hi=min(sr*.47,7500.0 if edge else 5200.0)
    impact=_bandpass(impact,sr,lo,hi)
    impact/=float(np.sqrt(np.mean(impact*impact))+1e-12)
    impact*=np.exp(-t/(.018 if edge else .024))
    sig=(.72 if edge else .83)*body+(.12 if edge else .08)*impact
    sig=_one_pole_lowpass(sig,sr,min(sr*.46,float(cfg.get("lowpass_hz",7600.0))))
    sig=_softclip(sig,float(cfg.get("drive",1.05)))
    sig=_declick(sig,sr,.55)
    return sig*v*float(cfg.get("output_gain",.46))*float(acfg.get("tom_edge_gain",.82) if edge else 1.0)

def kick(duration_s, sr, velocity=1.0, patch=None, seed=0):
    realism=_realism(patch)
    if realism is None:
        return _legacy_kick(duration_s,sr,velocity,patch)
    return _modeled_kick(duration_s,sr,velocity,seed,patch,realism)


def snare(duration_s, sr, velocity=1.0, seed=0, patch=None):
    realism=_realism(patch)
    if realism is None:
        return _legacy_snare(duration_s,sr,velocity,seed,patch)
    return _modeled_snare(duration_s,sr,velocity,seed,patch,realism)


def hat(duration_s, sr, velocity=1.0, seed=0, patch=None):
    realism=_realism(patch)
    if realism is None:
        return _legacy_hat(duration_s,sr,velocity,seed,patch)
    return _modeled_hat(duration_s,sr,velocity,seed,patch,realism)


def _render_drum_event_base(kind, duration_s, sr, velocity, seed=0, pan=0.0, patch=None, articulation=None):
    realism=_realism(patch)
    foundation=_articulation_foundation(patch)
    core=_acoustic_core(patch)
    art=_normalize_articulation(kind,articulation) if foundation is not None else None

    if core is not None and realism is not None and foundation is not None:
        if kind=="kick":
            minimum=float(realism.get("kick_tail_s",.36))
            sig=_core_drum_head(kind,max(duration_s,minimum),sr,velocity,seed,patch,"default",core)
            pan=0.0
            return equal_power_pan(sig,pan)
        if kind=="snare":
            tails={"center":float(realism.get("snare_tail_s",.34)),"ghost":float(foundation.get("snare_ghost_tail_s",.24)),
                   "rimshot":float(foundation.get("snare_rimshot_tail_s",.24)),"cross_stick":float(foundation.get("snare_cross_stick_tail_s",.16))}
            dur=max(duration_s,tails[art])
            sig=(_core_drum_head(kind,dur,sr,velocity,seed,patch,art,core) if art=="center"
                 else _core_snare_noncenter(dur,sr,velocity,seed,patch,realism,art,core))
            pan=0.04 if pan==0 else pan
            return equal_power_pan(sig,pan)
        if kind=="hat":
            tails={"closed":float(realism.get("hat_tail_s",.13)),"half_open":float(foundation.get("hat_half_open_tail_s",.52)),
                   "open":float(foundation.get("hat_open_tail_s",1.15)),"pedal":float(foundation.get("hat_pedal_tail_s",.13)),
                   "choke":float(foundation.get("hat_choke_tail_s",.09))}
            sig=_core_cymbal(kind,max(duration_s,tails[art]),sr,velocity,seed,patch,art,core)
            pan=0.18 if pan==0 else pan
            return equal_power_pan(sig,pan)
        if kind in {"ride","crash"}:
            tail_key=("ride_bell_tail_s" if art=="bell" else "ride_bow_tail_s") if kind=="ride" else "crash_tail_s"
            minimum=float(foundation.get("cymbal_choke_tail_s",.12) if art=="choke" else foundation.get(tail_key,1.8 if kind=="ride" else 2.2))
            sig=_core_cymbal(kind,max(duration_s,minimum),sr,velocity,seed,patch,art,core)
            default_pan=0.26 if kind=="ride" else -0.24
            pan=default_pan if pan==0 else pan
            return equal_power_pan(sig,pan)
        if kind in {"tom_high","tom_mid","tom_floor"}:
            minimum=float(foundation.get("tom_tail_s",.74))
            sig=_core_drum_head(kind,max(duration_s,minimum),sr,velocity,seed,patch,art,core)
            default_pan={"tom_high":.18,"tom_mid":.04,"tom_floor":-.16}[kind]
            pan=default_pan if pan==0 else pan
            return equal_power_pan(sig,pan)

    if kind=="kick":
        minimum=float(realism.get("kick_tail_s",0.36)) if realism else 0.28
        sig=kick(max(duration_s,minimum),sr,velocity,patch=patch,seed=seed)
        pan=0.0
    elif kind=="snare":
        if foundation is None:
            minimum=float(realism.get("snare_tail_s",0.34)) if realism else 0.20
            sig=snare(max(duration_s,minimum),sr,velocity,seed,patch=patch)
        else:
            tails={"center":float(realism.get("snare_tail_s",.34)),"ghost":float(foundation.get("snare_ghost_tail_s",.24)),
                   "rimshot":float(foundation.get("snare_rimshot_tail_s",.24)),"cross_stick":float(foundation.get("snare_cross_stick_tail_s",.16))}
            sig=_snare_articulation(max(duration_s,tails[art]),sr,velocity,seed,patch,realism,art)
        pan=0.04 if pan==0 else pan
    elif kind=="hat":
        if foundation is None:
            minimum=float(realism.get("hat_tail_s",0.13)) if realism else 0.07
            sig=hat(max(duration_s,minimum),sr,velocity,seed,patch=patch)
        else:
            tails={"closed":float(realism.get("hat_tail_s",.13)),"half_open":float(foundation.get("hat_half_open_tail_s",.52)),
                   "open":float(foundation.get("hat_open_tail_s",1.15)),"pedal":float(foundation.get("hat_pedal_tail_s",.13)),
                   "choke":float(foundation.get("hat_choke_tail_s",.09))}
            sig=_hat_articulation(max(duration_s,tails[art]),sr,velocity,seed,patch,realism,art)
        pan=0.18 if pan==0 else pan
    elif foundation is not None and kind in {"ride","crash"}:
        tail_key=("ride_bell_tail_s" if art=="bell" else "ride_bow_tail_s") if kind=="ride" else "crash_tail_s"
        if art=="choke":
            minimum=float(foundation.get("cymbal_choke_tail_s",.12))
        else:
            minimum=float(foundation.get(tail_key,1.8 if kind=="ride" else 2.2))
        sig=_cymbal_articulation(kind,max(duration_s,minimum),sr,velocity,seed,patch,art)
        default_pan=0.26 if kind=="ride" else -0.24
        pan=default_pan if pan==0 else pan
    elif foundation is not None and kind in {"tom_high","tom_mid","tom_floor"}:
        minimum=float(foundation.get("tom_tail_s",.74))
        sig=_tom_articulation(kind,max(duration_s,minimum),sr,velocity,seed,patch,art)
        default_pan={"tom_high":.18,"tom_mid":.04,"tom_floor":-.16}[kind]
        pan=default_pan if pan==0 else pan
    else:
        sig=np.zeros(max(1,int(duration_s*sr)))
    return equal_power_pan(sig,pan)

def _performance_timbre_cfg(patch):
    graph=(patch or {}).get("drum_graph", {}) if isinstance(patch,dict) else {}
    cfg=graph.get("performance_timbre", {}) if isinstance(graph,dict) else {}
    return cfg if isinstance(cfg,dict) and cfg.get("enabled",False) else None


def _bounded_optional_control(value, name):
    if value is None:
        return None
    try:
        x=float(value)
    except Exception as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"{name} outside [0,1]")
    return x


def _timbre_filter_mono(x, sr, kind, force, position, cfg):
    x=np.asarray(x,dtype=np.float64)
    if len(x)==0:
        return x.copy()
    y=x.copy()
    rms0=float(np.sqrt(np.mean(x*x))+1e-12)
    t=np.arange(len(x),dtype=np.float64)/float(sr)

    if force is not None:
        neutral=float(cfg.get("force_neutral",.5))
        denom=max(neutral,1.0-neutral,1e-9)
        d=max(-1.0,min(1.0,(float(force)-neutral)/denom))
        if kind in {"hat","ride","crash"}:
            split=min(sr*.43,4600.0)
        elif kind=="kick":
            split=min(sr*.43,1600.0)
        else:
            split=min(sr*.43,2300.0)
        low=_one_pole_lowpass(y,sr,split)
        high=y-low
        amount=float(cfg.get("force_brightness",.72))
        if d>=0:
            y=y+high*(amount*d)
        else:
            y=y+high*(amount*.82*d)
        attack=float(cfg.get("force_attack",.18))
        if attack>0 and abs(d)>1e-12:
            y*=1.0+attack*d*np.exp(-t/.010)

    if position is not None:
        pos=max(0.0,min(1.0,float(position)))
        pd=(pos-.5)*2.0
        if kind in {"snare","tom_high","tom_mid","tom_floor"}:
            split=min(sr*.43,1150.0 if kind!="snare" else 1750.0)
            low=_one_pole_lowpass(y,sr,split)
            high=y-low
            y=y+high*(float(cfg.get("membrane_edge_brightness",.46))*pd)
        elif kind=="kick":
            split=min(sr*.43,1050.0)
            low=_one_pole_lowpass(y,sr,split)
            high=y-low
            y=y+high*(float(cfg.get("kick_edge_brightness",.16))*pd)
        elif kind in {"hat","ride","crash"}:
            dark=float(cfg.get("cymbal_edge_darkening",.24))*pos
            softened=_one_pole_lowpass(y,sr,min(sr*.44,9000.0-2200.0*pos))
            y=(1.0-dark)*y+dark*softened
            tail=float(cfg.get("cymbal_edge_tail_boost",.30))*pos
            if tail>0:
                rise=1.0+tail*(1.0-np.exp(-t/.18))
                y*=rise

    if bool(cfg.get("rms_preserve",True)):
        rms1=float(np.sqrt(np.mean(y*y))+1e-12)
        y*=rms0/rms1
    return y


def _apply_performance_timbre(stereo, sr, kind, strike_force, strike_position, patch):
    cfg=_performance_timbre_cfg(patch)
    force=_bounded_optional_control(strike_force,"strike_force")
    position=_bounded_optional_control(strike_position,"strike_position")
    if cfg is None or (force is None and position is None):
        return stereo
    y=np.asarray(stereo,dtype=np.float64).copy()
    if y.ndim==1:
        return _timbre_filter_mono(y,sr,kind,force,position,cfg)
    for ch in range(y.shape[1]):
        y[:,ch]=_timbre_filter_mono(y[:,ch],sr,kind,force,position,cfg)
    return y


def render_drum_event(kind, duration_s, sr, velocity, seed=0, pan=0.0, patch=None, articulation=None, strike_force=None, strike_position=None):
    """Render one authored drum event.

    S23 strike controls are optional timbre controls.  When both are omitted the
    exact pre-S23/S22 path is used.  They never create timing, hits or loudness
    automation; event velocity remains the musical intensity authority.
    """
    stereo=_render_drum_event_base(kind,duration_s,sr,velocity,seed=seed,pan=pan,patch=patch,articulation=articulation)
    return _apply_performance_timbre(stereo,sr,kind,strike_force,strike_position,patch)

