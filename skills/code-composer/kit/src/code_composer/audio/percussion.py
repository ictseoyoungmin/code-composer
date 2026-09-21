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



def _hi_hat_mechanics(patch):
    cfg=_graph(patch).get("hi_hat_mechanics",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _snare_mechanics(patch):
    cfg=_graph(patch).get("snare_mechanics",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _tom_mechanics(patch):
    cfg=_graph(patch).get("tom_mechanics",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _cymbal_extension(patch):
    cfg=_graph(patch).get("cymbal_extension",{})
    if not isinstance(cfg,dict) or not cfg.get("enabled",False):
        return None
    return cfg


def _impact_force_pulse(n, sr, velocity, *, soft_contact_s=.0018, hard_contact_s=.0009, shape=1.55):
    """Short deterministic stick/cymbal contact-force pulse.

    The pulse represents one mechanical contact event.  Harder authored strikes
    use a shorter contact window; amplitude scaling remains the responsibility
    of the caller so this helper changes excitation *shape*, not mix gain.
    """
    n=max(1,int(n))
    v=max(0.0,min(1.0,float(velocity)))
    soft=max(2.0/sr,float(soft_contact_s))
    hard=max(2.0/sr,min(soft,float(hard_contact_s)))
    contact_s=soft+(hard-soft)*(v**0.72)
    m=max(3,min(n,int(round(contact_s*sr))))
    x=(np.arange(m,dtype=np.float64)+0.5)/m
    pulse=np.sin(np.pi*x)**max(.5,float(shape))
    # A free strike rises slightly faster than it releases.  Preserve a smooth
    # zero-ish boundary while moving the center of force toward impact onset.
    pulse*=1.0-0.22*x
    pulse/=float(np.sum(pulse)+1e-12)
    out=np.zeros(n,dtype=np.float64)
    out[:m]=pulse
    return out


def _coherent_plate_bank(t, sr, rng, freqs, gains, decay_s, force, *, jitter=.006, attack_s=0.0):
    """Modal plate response to one coherent impact-force event.

    An impulsive force excites modal velocity at one shared time origin.  The
    modal signs/amplitudes may differ, but arbitrary independent start phases
    are not used here.  This is the S27-A alternative to the older random-phase
    plate bank and is opt-in only.
    """
    y=np.zeros(len(t),dtype=np.float64)
    total=0.0
    for i,(f0,g0) in enumerate(zip(freqs,gains)):
        f=float(f0)*_variation(rng,jitter)
        g=float(g0)*_variation(rng,.025)
        d=max(.02,float(decay_s)/(1.0+.055*i))
        # Audio output is a compact surface-velocity / radiation proxy rather
        # than membrane displacement.  A force impulse therefore produces a
        # coherent non-zero onset (cosine-like velocity response) while the
        # physical displacement itself would start from zero.
        mode=np.cos(2*np.pi*f*t)*np.exp(-t/d)
        # Only the short non-zero contact support is needed for convolution.
        # Keeping the full event-length zero tail here would make np.convolve
        # quadratic in the cymbal tail length.
        nz=np.flatnonzero(np.abs(force)>1e-18)
        fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
        excited=np.convolve(fp,mode,mode='full')[:len(t)]
        y+=g*excited
        total+=abs(g)
    y/=max(total,1e-12)
    if attack_s>0:
        y*=1.0-np.exp(-t/max(1e-5,float(attack_s)))
    return y


def _dense_cymbal_plate_bank(t, sr, rng, freqs, gains, decay_s, force, *,
                             jitter=.004, attack_s=0.0, cloud_size=5,
                             cloud_spread=.024, low_order_suppression=.72):
    """High-density, rapidly de-phasing cymbal plate field for S27-A2.

    `freqs`/`gains` define only a broad radiation envelope.  Unlike physical_v1
    (one stable partial per anchor), this renderer fills the intervals between
    anchors with many deterministic inharmonic modes.  A localized impact gives
    them one common mechanical time origin, while mode-shape signs, irregular
    spacing and frequency-dependent decay make the field de-phase within a few
    milliseconds instead of ringing as a pitched bell.
    """
    y=np.zeros(len(t),dtype=np.float64)
    nz=np.flatnonzero(np.abs(force)>1e-18)
    fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
    anchors=np.asarray(freqs,dtype=np.float64)
    amp=np.asarray(gains,dtype=np.float64)
    if len(anchors)==0:
        return y
    if len(anchors)==1:
        anchors=np.array([anchors[0]*.985,anchors[0]*1.015],dtype=np.float64)
        amp=np.array([amp[0],amp[0]],dtype=np.float64)

    count=max(12,int(len(anchors)*max(3,int(cloud_size))))
    # Stratified irregular distribution avoids both sparse anchor clusters and
    # a synthetic equally-spaced comb.  Cymbal modal density rises with order,
    # so the warp gives progressively more modes to the upper part of the band.
    u=(np.arange(count,dtype=np.float64)+rng.random(count))/count
    u=np.clip(u**.72,0.0,1.0)
    fmin=float(anchors[0]); fmax=float(anchors[-1])
    modal_f=fmin+(fmax-fmin)*u
    modal_f*=1.0+rng.uniform(-float(jitter),float(jitter),size=count)
    modal_f=np.clip(modal_f,max(40.0,fmin*.94),min(sr*.47,fmax*1.04))
    # Broad spectral envelope inherited from the authored anchors, with a small
    # floor so gaps between anchors radiate instead of exposing stable pitches.
    modal_g=np.interp(modal_f,anchors,amp,left=amp[0],right=amp[-1])
    modal_g*=rng.uniform(.72,1.18,size=count)
    x=(modal_f-fmin)/max(1e-9,fmax-fmin)
    # Bow/edge strikes excite higher spatial orders more strongly than a bell
    # strike.  Suppress only the low-order radiation, not the stick transient.
    modal_g*=float(low_order_suppression)+(1.0-float(low_order_suppression))*np.sqrt(np.clip(x,0,1))
    signs=np.where(rng.random(count)>=.5,1.0,-1.0)
    energy=0.0
    for i,(f,g,sign,xf) in enumerate(zip(modal_f,modal_g,signs,x)):
        # Higher modes die somewhat faster, but individual loss variation keeps
        # the decay cloud from collapsing into one audible pitch envelope.
        d=max(.016,float(decay_s)*(1.0-.42*xf))*rng.uniform(.78,1.13)
        # Tiny per-mode phase displacement represents radiation-path diversity;
        # it is bounded so all modes still belong to the same physical strike.
        phase=rng.uniform(-.18,.18)
        mode=sign*np.cos(2*np.pi*float(f)*t+phase)*np.exp(-t/d)
        excited=np.convolve(fp,mode,mode='full')[:len(t)]
        y+=float(g)*excited
        energy+=float(g)*float(g)
    y/=max(np.sqrt(energy),1e-12)
    if attack_s>0:
        y*=1.0-np.exp(-t/max(1e-5,float(attack_s)))
    return y

def _hat_collision_texture(n, sr, rng, velocity, state_cfg, mech, collision_profile=None):
    """Noise-like edge-collision field from two hi-hat plates.

    The historical path intentionally stays byte-identical when
    ``collision_profile`` is omitted.  S27-K R1 uses an opt-in micro-contact
    profile only for control-derived foot gestures: each re-contact is spread
    over a short raised pulse, while density rises and gain falls.  This keeps
    the physical irregular edge interaction without exposing isolated two-sample
    impulses as audible digital crackle in the late chick/splash tail.
    """
    n=max(1,int(n))
    duration=max(0.0,float(state_cfg.get("collision_duration_s",.05)))
    density=max(0.0,float(state_cfg.get("collision_density_hz",700.0)))
    gain=max(0.0,float(state_cfg.get("collision_gain",.25)))
    profile=collision_profile if isinstance(collision_profile,dict) and collision_profile.get("enabled",False) else None
    if profile is not None:
        density*=max(.1,float(profile.get("density_scale",1.0)))
        gain*=max(0.0,float(profile.get("gain_scale",1.0)))
    if duration<=0 or density<=0 or gain<=0:
        return np.zeros(n,dtype=np.float64)
    limit=min(n,max(1,int(duration*sr)))
    impulses=np.zeros(n,dtype=np.float64)
    # Contact density scales mildly with strike energy but never becomes a
    # periodic oscillator.  Exponential intervals mimic irregular edge re-contact.
    v=max(0.0,min(1.25,float(velocity)))
    mean_interval=sr/max(30.0,density*(.82+.34*min(1.0,v)))
    idx=max(1,int(.00045*sr))
    count=0
    if profile is None:
        # Locked S27-B/J behavior.  Do not refactor this branch: exact samples
        # are part of the pre-R1 regression baseline.
        while idx<limit and count<max(12,int(duration*density*2.5)):
            amp=np.exp(-idx/max(1.0,float(limit)*.62))*rng.uniform(.62,1.0)
            sign=-1.0 if rng.random()<.5 else 1.0
            impulses[idx]+=sign*amp
            if idx+1<n:
                impulses[idx+1]-=sign*amp*.58
            step=max(1,int(rng.exponential(mean_interval)))
            idx+=step
            count+=1
    else:
        pulse_ms=max(.10,float(profile.get("pulse_ms",.55)))
        pulse_n=max(4,int(round(pulse_ms*.001*sr)))
        # Raised micro-contact: zero slope at both ends and no single-sample
        # discontinuity.  Random polarity remains so the field is aperiodic.
        u=np.linspace(0.0,np.pi,pulse_n,dtype=np.float64)
        pulse=np.sin(u)**2
        pulse/=max(1e-12,float(np.max(pulse)))
        while idx<limit and count<max(16,int(duration*density*2.5)):
            amp=np.exp(-idx/max(1.0,float(limit)*.58))*rng.uniform(.54,.90)
            sign=-1.0 if rng.random()<.5 else 1.0
            end=min(n,idx+pulse_n)
            if end>idx:
                impulses[idx:end]+=sign*amp*pulse[:end-idx]
            step=max(1,int(rng.exponential(mean_interval)))
            idx+=step
            count+=1
    lo=float(mech.get("collision_low_hz",3600.0))
    hi=min(sr*.47,float(mech.get("collision_high_hz",11200.0)))
    x=_bandpass(impulses,sr,lo,hi)
    peak=float(np.max(np.abs(x))+1e-12)
    x=x/peak
    return x*gain*(.62+.38*min(1.0,v))



def _hat_collision_plate_excitation(n, sr, rng, velocity, state_cfg, mech):
    """Resonant metal re-contact field for the reopened two-plate hi-hat.

    Unlike ``_hat_collision_texture`` this path never sends a band-passed
    broadband impulse train directly to the output.  Irregular edge contacts
    form a short *mechanical force* signal which then excites a dense,
    high-order inharmonic plate bank.  The audible energy is therefore modal
    metal radiation rather than normalized friction/noise texture.
    """
    n=max(1,int(n))
    duration=max(0.0,float(state_cfg.get("collision_duration_s",.05)))
    density=max(0.0,float(state_cfg.get("collision_density_hz",700.0)))
    gain=max(0.0,float(state_cfg.get("collision_gain",.18)))
    if duration<=0 or density<=0 or gain<=0:
        return np.zeros(n,dtype=np.float64)

    limit=min(n,max(1,int(duration*sr)))
    v=max(0.0,min(1.25,float(velocity)))
    force=np.zeros(n,dtype=np.float64)
    # Contact events remain aperiodic, but each event is a finite mechanical
    # compression/release pulse rather than an audio-rate discontinuity.
    pulse_ms=max(.16,float(mech.get("collision_contact_ms",.46)))
    pulse_n=max(5,int(round(pulse_ms*.001*sr)))
    u=np.linspace(0.0,np.pi,pulse_n,dtype=np.float64)
    pulse=np.sin(u)**1.7
    pulse/=max(1e-12,float(np.max(pulse)))
    mean_interval=sr/max(30.0,density*(.84+.30*min(1.0,v)))
    idx=max(1,int(.00055*sr))
    count=0
    max_contacts=max(10,int(duration*density*2.2))
    while idx<limit and count<max_contacts:
        amp=np.exp(-idx/max(1.0,float(limit)*.64))*rng.uniform(.70,1.0)
        end=min(n,idx+pulse_n)
        if end>idx:
            force[idx:end]+=amp*pulse[:end-idx]
        idx+=max(1,int(rng.exponential(mean_interval)))
        count+=1

    freqs=mech.get("collision_mode_freqs",[4300.,5200.,6250.,7350.,8500.,9700.,10850.])
    gains=mech.get("collision_mode_gains",[.30,.46,.67,.86,1.0,.78,.50])
    decay=max(.006,float(state_cfg.get(
        "collision_resonance_decay_s",
        min(.040,max(.010,float(state_cfg.get("plate_decay_s",.12))*.14)),
    )))
    t=np.arange(n,dtype=np.float64)/sr
    metal=_dense_cymbal_plate_bank(
        t,sr,rng,list(freqs),list(gains),decay,force,
        jitter=float(mech.get("collision_mode_jitter",.015)),
        cloud_size=int(mech.get("collision_cloud_size",5)),
        cloud_spread=float(mech.get("collision_cloud_spread",.045)),
        low_order_suppression=float(mech.get("collision_low_order_suppression",.46)),
    )
    # Keep the layer spectrally inside the hi-hat radiation band without the
    # old peak-normalized noise path.  Its level is determined by mechanical
    # force, state gain and the modal radiation itself.
    lo=float(mech.get("collision_low_hz",3600.0))
    hi=min(sr*.47,float(mech.get("collision_high_hz",11200.0)))
    metal=_one_pole_highpass(metal,sr,lo*.82)
    metal=_one_pole_lowpass(metal,sr,hi)
    return metal*gain*(.66+.34*min(1.0,v))

def _two_cymbal_hat(duration_s, sr, velocity, seed, patch, mech, articulation, pedal_openness=None, collision_profile=None):
    """S27-B compact two-plate hi-hat model.

    Top and bottom plates are independent dense inharmonic fields.  Pedal state
    changes plate separation/contact loss, while an aperiodic inelastic-collision
    layer supplies the characteristic hi-hat rattle.  Legacy ``hat`` rendering is
    intentionally not routed here; this path is explicit and opt-in.
    """
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+2301)
    v=max(0.0,min(1.25,float(velocity)))
    states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
    aliases={
        "hat_tight_closed":"tight_closed",
        "hat_closed":"closed",
        "hat_half_open":"half_open",
        "hat_open":"open",
        "hat_pedal":"pedal_chick",
        "hat_foot_splash":"foot_splash",
    }
    state_name=aliases.get(str(articulation),str(articulation))
    state_cfg=states.get(state_name,{}) if isinstance(states.get(state_name,{}),dict) else {}
    pedal_only=state_name in ("pedal_chick","foot_splash")
    if not pedal_only and pedal_openness is not None and state_cfg:
        natural=float(state_cfg.get("openness",1.0))
        effective=min(natural,max(0.0,min(1.0,float(pedal_openness))))
        if effective < natural-1e-12:
            state_cfg=_interpolate_hi_hat_stick_state(states,effective)

    top_freqs=np.asarray(mech.get("top_mode_freqs",[3600.,4550.,5520.,6460.,7410.,8350.,9300.,10250.,11100.]),dtype=np.float64)
    top_gains=np.asarray(mech.get("top_mode_gains",[.42,.56,.70,.82,.92,1.0,.84,.64,.42]),dtype=np.float64)
    bottom_scale=float(mech.get("bottom_frequency_scale",.965))
    bottom_freqs=(top_freqs*bottom_scale).tolist()
    bottom_gains=(top_gains*np.asarray(mech.get("bottom_gain_shape",[.92,.96,1.0,1.02,1.0,.94,.86,.74,.62]),dtype=np.float64)).tolist()

    if pedal_only:
        force=_impact_force_pulse(
            n,sr,v,
            soft_contact_s=float(mech.get("pedal_contact_soft_s",.00145)),
            hard_contact_s=float(mech.get("pedal_contact_hard_s",.00062)),
            shape=float(mech.get("pedal_force_shape",1.35)),
        )
    else:
        force=_impact_force_pulse(
            n,sr,v,
            soft_contact_s=float(mech.get("stick_contact_soft_s",.00155)),
            hard_contact_s=float(mech.get("stick_contact_hard_s",.00062)),
            shape=float(mech.get("stick_force_shape",1.48)),
        )

    decay=max(.018,float(state_cfg.get("plate_decay_s",.12)))
    cloud_size=int(mech.get("plate_cloud_size",8))
    low_supp=float(mech.get("low_order_suppression",.12))
    top=_dense_cymbal_plate_bank(
        t,sr,rng,top_freqs.tolist(),top_gains.tolist(),decay,force,
        jitter=float(mech.get("mode_jitter",.009)),
        cloud_size=cloud_size,
        cloud_spread=float(mech.get("plate_cloud_spread",.034)),
        low_order_suppression=low_supp,
    )
    # The bottom plate receives energy through edge contact/stand coupling.  It
    # uses a distinct deterministic field instead of a pitch-shifted copy.
    transfer=float(state_cfg.get("bottom_transfer",.62))
    bottom_force=force*transfer
    bottom=_dense_cymbal_plate_bank(
        t,sr,rng,bottom_freqs,bottom_gains,decay*float(state_cfg.get("bottom_decay_scale",.90)),bottom_force,
        jitter=float(mech.get("mode_jitter",.009))*1.12,
        cloud_size=max(5,cloud_size-1),
        cloud_spread=float(mech.get("plate_cloud_spread",.034))*1.08,
        low_order_suppression=min(1.0,low_supp+0.04),
    )

    collision_model=str(mech.get("collision_model","broadband_texture_v1"))
    if collision_model=="modal_plate_excitation_v2" and collision_profile is None:
        collision=_hat_collision_plate_excitation(n,sr,rng,v,state_cfg,mech)
    else:
        collision=_hat_collision_texture(n,sr,rng,v,state_cfg,mech,collision_profile)
    contact=_stick_contact_radiation(
        force,sr,float(mech.get("contact_low_hz",4300.0)),min(sr*.47,float(mech.get("contact_high_hz",11200.0)))
    )

    # Tight pedal pressure dissipates plate motion quickly; looser/open states
    # preserve more independent plate radiation.  The collision texture already
    # carries the rattle duration, so no artificial reverb tail is added here.
    top_gain=float(state_cfg.get("top_gain",.50))
    bottom_gain=float(state_cfg.get("bottom_gain",.42))
    contact_gain=float(state_cfg.get("contact_gain",.18 if not pedal_only else .10))
    if pedal_only:
        # Foot chick/splash is driven by the two plates colliding rather than a
        # stick striking only the top plate.
        top_gain*=float(state_cfg.get("pedal_plate_scale",.72))
        bottom_gain*=float(state_cfg.get("pedal_plate_scale",.72))

    sig=top_gain*top+bottom_gain*bottom+contact_gain*contact+collision
    hp=float(mech.get("output_highpass_hz",2800.0))
    lp=min(sr*.47,float(mech.get("output_lowpass_hz",11400.0)))
    sig=_one_pole_highpass(sig,sr,hp)
    sig=_one_pole_lowpass(sig,sr,lp)
    sig=_softclip(sig,float(mech.get("drive",1.025)))
    sig=_declick(sig,sr,float(mech.get("declick_ms",.08)))
    out_gain=float(state_cfg.get("output_gain",mech.get("output_gain",.42)))
    # Velocity is still authored performance amplitude, but state/contact shape
    # above changes with velocity as well, so this is not volume-only dynamics.
    return sig*(max(.02,v)**float(mech.get("velocity_power",.90)))*out_gain



_HI_HAT_RING_OPENNESS = {
    "hat_half_open": 0.55,
    "hat_open": 1.0,
    "hat_foot_splash": 0.82,
}

_HI_HAT_CLOSURE_OPENNESS = {
    "hat_half_open": 0.55,
    "hat_closed": 0.12,
    "hat_tight_closed": 0.025,
    "hat_pedal": 0.0,
}


def resolve_hi_hat_pedal_openness(events, beat, control_name="hi_hat_pedal_openness"):
    """Resolve the persistent authored pedal state at one timeline beat.

    A completed curve leaves the pedal at its final openness until another
    explicit curve changes it.  Overlap is rejected by the IR validator; this
    resolver nevertheless stays deterministic if called before validation.
    """
    beat=float(beat)
    current=1.0
    controls=[
        ev for ev in events
        if ev.get("event_type")=="drum_control" and ev.get("control")==control_name
    ]
    for control in sorted(controls,key=lambda ev: float(ev.get("start_beat",0.0))):
        start=float(control.get("start_beat",0.0))
        if beat < start-1e-12:
            break
        points=control.get("points",[])
        if not isinstance(points,list) or not points:
            continue
        pts=sorted(points,key=lambda pt: float(pt.get("offset_beats",0.0)))
        duration=max(0.0,float(control.get("duration_beats",0.0)))
        end=start+duration
        if beat >= end-1e-12:
            current=float(pts[-1].get("openness",current))
            continue
        x=max(0.0,beat-start)
        xp=np.asarray([float(pt.get("offset_beats",0.0)) for pt in pts],dtype=np.float64)
        fp=np.asarray([float(pt.get("openness",current)) for pt in pts],dtype=np.float64)
        current=float(np.interp(x,xp,fp,left=fp[0],right=fp[-1]))
        break
    return max(0.0,min(1.0,current))



def _hi_hat_pedal_motion_gestures(event, beat_s, cfg):
    """Translate one *authored* pedal trajectory into physical contact gestures.

    S27-K does not invent a foot performance.  It only derives audible cymbal
    contact/release consequences from the explicit ``hi_hat_pedal_openness``
    curve already authored by the Composer Agent.  Slow motion may be silent;
    a fast crossing into contact produces a chick, while a fast release from a
    genuinely clamped state can produce a foot splash.
    """
    pedal_audio=cfg.get("pedal_audio",{}) if isinstance(cfg.get("pedal_audio",{}),dict) else {}
    if not pedal_audio.get("enabled",False):
        return []
    points=event.get("points",[])
    if not isinstance(points,list) or len(points)<2:
        return []
    pts=sorted(points,key=lambda pt:float(pt.get("offset_beats",0.0)))
    contact=max(0.0,min(1.0,float(pedal_audio.get("contact_threshold",.10))))
    release=max(contact,min(1.0,float(pedal_audio.get("release_threshold",.18))))
    splash_closed=max(0.0,min(contact,float(pedal_audio.get("splash_closed_openness",.08))))
    min_close=max(.01,float(pedal_audio.get("min_close_speed_per_s",3.5)))
    full_close=max(min_close+1e-9,float(pedal_audio.get("full_close_speed_per_s",16.0)))
    min_open=max(.01,float(pedal_audio.get("min_reopen_speed_per_s",3.5)))
    full_open=max(min_open+1e-9,float(pedal_audio.get("full_reopen_speed_per_s",14.0)))
    chick_min=max(.01,min(1.25,float(pedal_audio.get("chick_velocity_min",.36))))
    chick_max=max(chick_min,min(1.25,float(pedal_audio.get("chick_velocity_max",.94))))
    splash_min=max(.01,min(1.25,float(pedal_audio.get("splash_velocity_min",.42))))
    splash_max=max(splash_min,min(1.25,float(pedal_audio.get("splash_velocity_max",1.0))))
    out=[]
    for a,b in zip(pts[:-1],pts[1:]):
        x0=float(a.get("offset_beats",0.0)); x1=float(b.get("offset_beats",0.0))
        o0=max(0.0,min(1.0,float(a.get("openness",1.0))))
        o1=max(0.0,min(1.0,float(b.get("openness",o0))))
        dt=max(1e-9,(x1-x0)*float(beat_s))
        slope=(o1-o0)/dt
        if slope<0.0 and o0>contact+1e-12 and o1<=contact+1e-12:
            speed=-slope
            if speed>=min_close:
                u=(o0-contact)/max(1e-12,o0-o1)
                offset=(x0+(x1-x0)*max(0.0,min(1.0,u)))*float(beat_s)
                strength=max(0.0,min(1.0,(speed-min_close)/(full_close-min_close)))
                vel=chick_min+(chick_max-chick_min)*(strength**.72)
                out.append((offset,"hat_pedal",vel,speed))
        if slope>0.0 and o0<=splash_closed+1e-12 and o1>=release-1e-12:
            speed=slope
            if speed>=min_open:
                u=(release-o0)/max(1e-12,o1-o0)
                offset=(x0+(x1-x0)*max(0.0,min(1.0,u)))*float(beat_s)
                strength=max(0.0,min(1.0,(speed-min_open)/(full_open-min_open)))
                vel=splash_min+(splash_max-splash_min)*(strength**.72)
                out.append((offset,"hat_foot_splash",vel,speed))
    return out


def render_hi_hat_pedal_control(event, sr, beat_s, seed, patch):
    """Render S27-K contact audio caused by an explicit pedal control curve."""
    graph=patch.get("drum_graph",{}) if isinstance(patch,dict) else {}
    cfg=graph.get("hi_hat_state",{}) if isinstance(graph,dict) else {}
    pedal_audio=cfg.get("pedal_audio",{}) if isinstance(cfg.get("pedal_audio",{}),dict) else {}
    gestures=_hi_hat_pedal_motion_gestures(event,beat_s,cfg)
    if not gestures:
        return np.zeros((0,2),dtype=np.float64)
    mech=_hi_hat_mechanics(patch) or {}
    states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
    duration=max(0.0,float(event.get("duration_beats",0.0))*float(beat_s))
    max_tail=0.0
    for _,kind,_,_ in gestures:
        state_name="pedal_chick" if kind=="hat_pedal" else "foot_splash"
        st=states.get(state_name,{}) if isinstance(states.get(state_name,{}),dict) else {}
        max_tail=max(max_tail,float(st.get("tail_s",.5)))
    n=max(1,int(np.ceil((duration+max_tail+.01)*sr)))
    out=np.zeros((n,2),dtype=np.float64)
    profiles=pedal_audio.get("collision_profiles",{}) if isinstance(pedal_audio.get("collision_profiles",{}),dict) else {}
    for i,(offset,kind,vel,_speed) in enumerate(gestures):
        profile_name="chick" if kind=="hat_pedal" else "splash"
        profile=profiles.get(profile_name,{}) if isinstance(profiles.get(profile_name,{}),dict) else None
        st=render_drum_event(
            kind,.04,sr,vel,seed=int(seed)+i*104729,pan=0.0,patch=patch,
            hi_hat_collision_profile=profile,
        )
        # S27-K R2: control-derived foot gestures use the two plate/contact
        # response as the audible source.  The previous R1 broadband
        # micro-contact layer removed crackle but could read as felt/sandpaper
        # in a production mix.  Keep collision gain at zero in the preset and
        # calibrate only the physical plate/contact output here.
        if str(pedal_audio.get("model", "")) == "authored_motion_plate_contact_v3":
            gain_key="chick_output_gain" if kind=="hat_pedal" else "splash_output_gain"
            st*=max(0.0,float(pedal_audio.get(gain_key,1.0)))
        start=max(0,int(round(float(offset)*sr)))
        end=min(n,start+len(st))
        if end>start:
            out[start:end]+=st[:end-start]
    return out


def _interpolate_hi_hat_stick_state(states, openness):
    """Interpolate the accepted S27-B stick-state mechanics by pedal openness."""
    ordered=[]
    for name in ("tight_closed","closed","half_open","open"):
        cfg=states.get(name,{}) if isinstance(states,dict) else {}
        if isinstance(cfg,dict):
            ordered.append((float(cfg.get("openness",0.0)),cfg))
    ordered.sort(key=lambda item:item[0])
    if not ordered:
        return {}
    x=max(ordered[0][0],min(ordered[-1][0],float(openness)))
    if x<=ordered[0][0]+1e-12:
        return dict(ordered[0][1])
    if x>=ordered[-1][0]-1e-12:
        return dict(ordered[-1][1])
    lo=ordered[0]; hi=ordered[-1]
    for a,b in zip(ordered[:-1],ordered[1:]):
        if a[0]-1e-12 <= x <= b[0]+1e-12:
            lo,hi=a,b; break
    span=max(1e-12,hi[0]-lo[0]); u=(x-lo[0])/span
    out={}
    for key in set(lo[1])|set(hi[1]):
        av=lo[1].get(key); bv=hi[1].get(key)
        if isinstance(av,(int,float)) and not isinstance(av,bool) and isinstance(bv,(int,float)) and not isinstance(bv,bool):
            out[key]=float(av)+(float(bv)-float(av))*u
        else:
            out[key]=av if u<.5 else bv
    out["openness"]=x
    return out


def _continuous_hi_hat_openness(stereo, sr, kind, event_index, events, beat_s, cfg):
    """Apply explicitly-authored continuous pedal openness to one ringing hit.

    The control surface is a separate ``event_type: drum_control`` event with
    ``control: hi_hat_pedal_openness`` and piecewise-linear ``points``.  Openness
    is normalized 1=open to 0=closed.  The control can reduce residual energy but
    can never restore energy already dissipated, so re-opening is causal rather
    than a gain automation undo.
    """
    if str(kind) not in _HI_HAT_RING_OPENNESS:
        return stereo
    continuous = cfg.get("continuous", {}) if isinstance(cfg.get("continuous", {}), dict) else {}
    controls = [
        ev for ev in events
        if ev.get("event_type") == "drum_control"
        and ev.get("control") == continuous.get("control", "hi_hat_pedal_openness")
    ]
    if not controls or len(stereo) == 0:
        return stereo

    source = events[event_index] if 0 <= int(event_index) < len(events) else {}
    source_beat = float(source.get("start_beat", 0.0))
    n = len(stereo)
    natural_open = float(_HI_HAT_RING_OPENNESS[str(kind)])
    model=cfg.get("model","authored_continuous_openness_v2")
    control_name=continuous.get("control","hi_hat_pedal_openness")
    source_open=natural_open
    if model=="authored_persistent_openness_v3":
        source_open=min(natural_open,resolve_hi_hat_pedal_openness(events,source_beat,control_name))
    openness = np.full(n, source_open, dtype=np.float64)
    current = source_open
    cursor = 0
    touched = False

    for control in sorted(controls, key=lambda ev: float(ev.get("start_beat", 0.0))):
        points = control.get("points", [])
        if not isinstance(points, list) or len(points) < 2:
            continue
        start_beat = float(control.get("start_beat", 0.0))
        duration_beats = float(control.get("duration_beats", 0.0))
        ctrl_start = int(round((start_beat - source_beat) * float(beat_s) * sr))
        ctrl_end = int(round((start_beat + duration_beats - source_beat) * float(beat_s) * sr))
        if ctrl_end <= 0:
            # Persistent pre-strike state is already represented by source_open
            # in v3; v2 keeps its historical event-local behavior.
            if model!="authored_persistent_openness_v3":
                current = min(current, float(points[-1].get("openness", current)))
            continue
        if ctrl_start >= n:
            break
        start = max(0, ctrl_start)
        end = min(n, max(start + 1, ctrl_end))
        if cursor < start:
            openness[cursor:start] = current

        xp = np.asarray([
            (start_beat + float(pt.get("offset_beats", 0.0)) - source_beat) * float(beat_s) * sr
            for pt in points
        ], dtype=np.float64)
        fp = np.asarray([float(pt.get("openness", current)) for pt in points], dtype=np.float64)
        samples = np.arange(start, end, dtype=np.float64)
        vals = np.interp(samples, xp, fp, left=fp[0], right=fp[-1])
        # A pedal can open again and reduce *future* damping, but it cannot
        # recreate energy already removed by earlier contact.
        openness[start:end] = np.clip(vals, 0.0, natural_open)
        current = min(natural_open, max(0.0, float(fp[-1])))
        cursor = end
        touched = True

    if not touched:
        return stereo
    if cursor < n:
        openness[cursor:] = current

    # Preserve the accepted source bit-for-bit until the first sample where
    # pedal contact actually departs from the natural openness.
    reference_open=max(0.0,float(source_open))
    if reference_open <= 1e-9:
        return stereo
    contact = np.clip((reference_open - openness) / reference_open, 0.0, 1.0)
    active = np.flatnonzero(contact > 1e-12)
    if not len(active):
        return stereo
    first = int(active[0])

    power = max(.25, float(continuous.get("contact_power", 1.65)))
    contact = contact ** power
    body_tau = max(.005, float(continuous.get("body_closed_decay_ms", 72.0)) * .001)
    wash_tau = max(.002, float(continuous.get("wash_closed_decay_ms", 24.0)) * .001)
    residual = max(0.0, min(.25, float(continuous.get("residual", .003))))
    split_hz = float(continuous.get("split_hz", 5200.0))

    accum = np.cumsum(contact[first:]) / float(sr)
    body_env = residual + (1.0 - residual) * np.exp(-accum / body_tau)
    wash_env = residual + (1.0 - residual) * np.exp(-accum / wash_tau)

    out = stereo.copy()
    for ch in range(out.shape[1]):
        tail = stereo[first:, ch]
        body = _one_pole_lowpass(tail, sr, split_hz)
        wash = tail - body
        out[first:, ch] = body * body_env + wash * wash_env
    return out


def apply_hi_hat_state_transitions(stereo, sr, kind, event_index, events, beat_s, patch):
    """Damp an already-ringing explicit hi-hat event when a later closure occurs.

    S27-H is deliberately narrow: it does not synthesize pedal motion or infer a
    groove.  It only lets later *authored* hi-hat closure events dissipate energy
    that was emitted by an earlier open/half-open/splash event.  Patches without
    ``drum_graph.hi_hat_state`` return the input object untouched so all earlier
    presets remain byte-identical.
    """
    graph = patch.get("drum_graph", {}) if isinstance(patch, dict) else {}
    cfg = graph.get("hi_hat_state", {}) if isinstance(graph, dict) else {}
    if not isinstance(cfg, dict) or not cfg.get("enabled", False):
        return stereo
    if str(kind) not in _HI_HAT_RING_OPENNESS:
        return stereo

    model = cfg.get("model", "authored_closure_damping_v1")
    if model not in {"authored_closure_damping_v1", "authored_continuous_openness_v2", "authored_persistent_openness_v3"}:
        return stereo

    out = stereo
    if model == "authored_continuous_openness_v2":
        out = _continuous_hi_hat_openness(out, sr, kind, event_index, events, beat_s, cfg)

    state_cfg = cfg.get("closure", {}) if isinstance(cfg.get("closure", {}), dict) else {}
    current_open = float(_HI_HAT_RING_OPENNESS[str(kind)])
    source = events[event_index] if 0 <= int(event_index) < len(events) else {}
    source_beat = float(source.get("start_beat", 0.0))
    if model=="authored_persistent_openness_v3":
        continuous=cfg.get("continuous",{}) if isinstance(cfg.get("continuous",{}),dict) else {}
        current_open=min(current_open,resolve_hi_hat_pedal_openness(events,source_beat,continuous.get("control","hi_hat_pedal_openness")))
    duration_s = len(stereo) / max(1.0, float(sr))
    changed = out is not stereo

    defaults = {
        "hat_half_open": (42.0, 0.26),
        "hat_closed": (17.0, 0.028),
        "hat_tight_closed": (9.5, 0.008),
        "hat_pedal": (11.5, 0.004),
    }

    for j in range(int(event_index) + 1, len(events)):
        ev = events[j]
        if ev.get("event_type") != "drum":
            continue
        target_kind = str(ev.get("drum", ""))
        if target_kind not in _HI_HAT_CLOSURE_OPENNESS:
            continue
        target_open = float(_HI_HAT_CLOSURE_OPENNESS[target_kind])
        # Opening/re-opening never restores energy already lost by this earlier
        # ringing event.  Only a genuinely more-closed authored state damps it.
        if target_open >= current_open - 1e-12:
            continue
        dt_s = (float(ev.get("start_beat", 0.0)) - source_beat) * float(beat_s)
        if dt_s <= 0.0:
            continue
        start = int(round(dt_s * sr))
        if start >= len(stereo):
            break
        if not changed:
            out = stereo.copy()
            changed = True

        default_ms, default_residual = defaults[target_kind]
        item = state_cfg.get(target_kind, {}) if isinstance(state_cfg.get(target_kind, {}), dict) else {}
        decay_ms = max(0.5, float(item.get("decay_ms", default_ms)))
        residual = max(0.0, min(1.0, float(item.get("residual", default_residual))))
        length = len(out) - start
        if length > 0:
            tt = np.arange(length, dtype=np.float64) / float(sr)
            env = residual + (1.0 - residual) * np.exp(-tt / max(1e-6, decay_ms * 0.001))
            out[start:] *= env[:, None]
        current_open = target_open
        if current_open <= 1e-9:
            break

    return out

def _snare_membrane_bank(t, sr, rng, base_hz, ratios, gains, decay_s, force, strike_position):
    """Compact membrane response with strike-position dependent modal balance.

    The spatial weighting is intentionally low-order rather than a full circular
    membrane eigenfunction solver: center hits emphasize the first radiating
    modes, while off-center/rim-adjacent hits shift energy toward higher modes.
    """
    y=np.zeros(len(t),dtype=np.float64)
    nz=np.flatnonzero(np.abs(force)>1e-18)
    fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
    pos=max(0.0,min(1.0,float(strike_position)))
    count=max(1,len(ratios))
    energy=0.0
    for i,(ratio,gain) in enumerate(zip(ratios,gains)):
        order=i/max(1,count-1)
        # Central excitation favors the lowest radiating modes.  Toward the rim,
        # those modes are suppressed and spatially higher content becomes stronger.
        spatial=(1.0-pos)*(1.0-.38*order)+pos*(.24+1.12*order)
        spatial=max(.04,spatial)
        g=float(gain)*spatial*rng.uniform(.96,1.04)
        f=float(base_hz)*float(ratio)*rng.uniform(.996,1.004)
        d=max(.010,float(decay_s)*(1.0-.48*order))*rng.uniform(.92,1.07)
        phase=rng.uniform(-.05,.05)
        mode=np.cos(2*np.pi*f*t+phase)*np.exp(-t/d)
        y+=g*np.convolve(fp,mode,mode='full')[:len(t)]
        energy+=g*g
    return y/max(np.sqrt(energy),1e-12)


def _snare_rim_shell_response(t, sr, rng, force, cfg, *, cross_stick=False):
    freqs=cfg.get("rim_mode_freqs",[520.,760.,1040.,1480.,2240.,3380.])
    gains=cfg.get("rim_mode_gains",[1.0,.78,.60,.43,.28,.16])
    base_decay=float(cfg.get("rim_decay_s",.045 if not cross_stick else .055))
    nz=np.flatnonzero(np.abs(force)>1e-18)
    fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
    y=np.zeros(len(t),dtype=np.float64)
    energy=0.0
    for i,(f0,g0) in enumerate(zip(freqs,gains)):
        # Cross-stick is dominated by the lower woody/rim modes; a rimshot keeps
        # more upper metallic hoop definition.
        tilt=(1.0-.10*i) if cross_stick else (.72+.09*i)
        g=max(.02,float(g0)*tilt*rng.uniform(.96,1.04))
        f=float(f0)*rng.uniform(.994,1.006)
        d=max(.008,base_decay/(1.0+.18*i))
        mode=np.cos(2*np.pi*f*t+rng.uniform(-.04,.04))*np.exp(-t/d)
        y+=g*np.convolve(fp,mode,mode='full')[:len(t)]
        energy+=g*g
    y/=max(np.sqrt(energy),1e-12)
    # Short stick/hoop contact.  Cross-stick uses more low-mid wood and less air.
    if cross_stick:
        click=_stick_contact_radiation(force,sr,float(cfg.get("cross_stick_low_hz",650.0)),float(cfg.get("cross_stick_high_hz",4200.0)))
    else:
        click=_stick_contact_radiation(force,sr,float(cfg.get("rimshot_low_hz",1200.0)),float(cfg.get("rimshot_high_hz",7800.0)))
    return y,click


def _articulated_snare(duration_s, sr, velocity, seed, patch, mech, articulation):
    """S27-C coupled head/wire/rim articulation model.

    Legacy ``snare`` is deliberately not routed here.  The explicit articulation
    names select different physical contacts rather than EQ/decay presets:
    center/ghost excite the batter head, rimshot excites head+rim together, and
    cross-stick is primarily a rim/shell wooden knock with minimal head/wire drive.
    """
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+3203)
    v=max(0.0,min(1.25,float(velocity)))
    states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
    aliases={
        "snare_center":"center",
        "snare_ghost":"ghost",
        "snare_rimshot":"rimshot",
        "snare_cross_stick":"cross_stick",
    }
    name=aliases.get(str(articulation),str(articulation))
    st=states.get(name,{}) if isinstance(states.get(name,{}),dict) else {}
    cross=name=="cross_stick"
    rimshot=name=="rimshot"

    force=_impact_force_pulse(
        n,sr,v,
        soft_contact_s=float(st.get("stick_contact_soft_s",mech.get("stick_contact_soft_s",.0017))),
        hard_contact_s=float(st.get("stick_contact_hard_s",mech.get("stick_contact_hard_s",.00072))),
        shape=float(st.get("stick_force_shape",mech.get("stick_force_shape",1.46))),
    )
    base=float(mech.get("head_base_hz",185.0))
    ratios=mech.get("head_mode_ratios",[1.0,1.47,1.93,2.54,3.18,3.92])
    gains=mech.get("head_mode_gains",[1.0,.55,.34,.22,.14,.09])
    position=float(st.get("strike_position",.10))
    head_force=force*(float(st.get("head_excitation",1.0)))
    head=_snare_membrane_bank(
        t,sr,rng,base,ratios,gains,float(st.get("head_decay_s",mech.get("head_decay_s",.082))),
        head_force,position,
    ) if float(st.get("head_gain",.6))>0 else np.zeros(n,dtype=np.float64)

    # The thinner/resonant snare-side head is coupled through enclosed air/shell.
    # A short delay and slightly higher modal scale keep it related but distinct.
    delay=max(0,int(float(mech.get("bottom_head_delay_s",.0018))*sr))
    bottom_force=np.zeros(n,dtype=np.float64)
    if delay<n and not cross:
        bottom_force[delay:]=force[:n-delay]*float(st.get("bottom_transfer",mech.get("bottom_transfer",.42)))
    bottom=_snare_membrane_bank(
        t,sr,rng,base*float(mech.get("bottom_frequency_scale",1.18)),ratios,
        np.asarray(gains,dtype=np.float64)*np.asarray(mech.get("bottom_gain_shape",[.72,.82,.92,1.0,1.02,.98]),dtype=np.float64),
        float(st.get("bottom_decay_s",mech.get("bottom_decay_s",.070))),bottom_force,
        min(1.0,position+.08),
    ) if np.max(np.abs(bottom_force))>0 else np.zeros(n,dtype=np.float64)

    # Snare wires are driven by resonant-head motion, not an unrelated noise pad.
    wire=np.zeros(n,dtype=np.float64)
    wire_gain=float(st.get("wire_gain",.44))
    if wire_gain>0 and not cross:
        motion=np.abs(np.diff(bottom,prepend=0.0))
        motion=_one_pole_lowpass(motion,sr,float(mech.get("wire_envelope_hz",150.0)))
        motion/=float(np.max(motion)+1e-12)
        noise=rng.standard_normal(n).astype(np.float64)
        noise=_bandpass(noise,sr,float(mech.get("wire_low_hz",1100.0)),min(sr*.47,float(mech.get("wire_high_hz",10800.0))))
        noise/=float(np.sqrt(np.mean(noise*noise))+1e-12)
        tail=np.exp(-t/max(.008,float(st.get("wire_decay_s",mech.get("wire_decay_s",.105)))*(0.78+.30*min(1.0,v))))
        # Relative wire audibility stays meaningful for ghost notes even when the
        # absolute stroke is quiet, matching the characteristic soft snare buzz.
        wire=(.22+.78*motion)*tail*noise

    rim,wood=_snare_rim_shell_response(t,sr,rng,force,mech,cross_stick=cross)
    contact=_stick_contact_radiation(
        force,sr,float(mech.get("stick_contact_low_hz",900.0)),min(sr*.47,float(mech.get("stick_contact_high_hz",9000.0)))
    )

    sig=(float(st.get("head_gain",.62))*head
         +float(st.get("bottom_gain",.18))*bottom
         +wire_gain*wire
         +float(st.get("rim_gain",.05))*rim
         +float(st.get("wood_gain",.06))*wood
         +float(st.get("contact_gain",.10))*contact)
    sig=_one_pole_highpass(sig,sr,float(mech.get("output_highpass_hz",75.0)))
    sig=_one_pole_lowpass(sig,sr,min(sr*.47,float(mech.get("output_lowpass_hz",11500.0))))
    sig=_softclip(sig,float(mech.get("drive",1.035)))
    sig=_declick(sig,sr,float(mech.get("declick_ms",.08)))
    return sig*(max(.015,v)**float(st.get("velocity_power",mech.get("velocity_power",.94))))*float(st.get("output_gain",.58))



def _tom_membrane_bank(t, sr, rng, base_hz, ratios, gains, decay_s, force, strike_position):
    """Two-head tom membrane approximation with strike-position weighting.

    A centre hit strongly excites the low radiating modes; an edge hit suppresses
    the fundamental and shifts energy upward.  The renderer is deterministic and
    event-scale: it represents the causal head response without pretending to be
    a full finite-element membrane solver.
    """
    y=np.zeros(len(t),dtype=np.float64)
    nz=np.flatnonzero(np.abs(force)>1e-18)
    fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
    pos=max(0.0,min(1.0,float(strike_position)))
    count=max(1,len(ratios))
    energy=0.0
    for i,(ratio,gain) in enumerate(zip(ratios,gains)):
        order=i/max(1,count-1)
        # Tom centre strokes need a strong low-order body; moving outward quickly
        # suppresses the fundamental while exposing higher membrane structure.
        low_bias=((1.0-pos)**1.55)*(1.0-.46*order)
        edge_bias=(pos**1.08)*(.10+1.52*order)
        spatial=max(.035,low_bias+edge_bias)
        g=float(gain)*spatial*rng.uniform(.96,1.04)
        f=float(base_hz)*float(ratio)*rng.uniform(.996,1.004)
        d=max(.014,float(decay_s)*(1.0-.40*order))*rng.uniform(.93,1.07)
        mode=np.cos(2*np.pi*f*t+rng.uniform(-.05,.05))*np.exp(-t/d)
        y+=g*np.convolve(fp,mode,mode='full')[:len(t)]
        energy+=g*g
    return y/max(np.sqrt(energy),1e-12)


def _tom_shell_response(t, sr, rng, force, family_cfg):
    freqs=family_cfg.get("shell_mode_freqs",[280.,430.,650.,960.,1380.])
    gains=family_cfg.get("shell_mode_gains",[1.0,.72,.48,.30,.16])
    decay=float(family_cfg.get("shell_decay_s",.075))
    nz=np.flatnonzero(np.abs(force)>1e-18)
    fp=force[:int(nz[-1])+1] if len(nz) else force[:1]
    y=np.zeros(len(t),dtype=np.float64)
    energy=0.0
    for i,(f0,g0) in enumerate(zip(freqs,gains)):
        g=max(.01,float(g0)*rng.uniform(.96,1.04))
        f=float(f0)*rng.uniform(.994,1.006)
        d=max(.010,decay/(1.0+.15*i))
        mode=np.cos(2*np.pi*f*t+rng.uniform(-.05,.05))*np.exp(-t/d)
        y+=g*np.convolve(fp,mode,mode='full')[:len(t)]
        energy+=g*g
    return y/max(np.sqrt(energy),1e-12)


def _articulated_tom(duration_s, sr, velocity, seed, patch, mech, articulation):
    """S27-D high/mid/floor two-head tom family.

    Each size has its own head tuning, cavity/body coupling, shell response and
    decay.  Centre/edge are different excitation positions rather than pitch or
    EQ presets.  No legacy kick/snare/hat renderer is routed through this path.
    """
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+4109)
    v=max(0.0,min(1.25,float(velocity)))
    aliases={
        "tom_high":("high","center"), "tom_high_edge":("high","edge"),
        "tom_mid":("mid","center"), "tom_mid_edge":("mid","edge"),
        "tom_floor":("floor","center"), "tom_floor_edge":("floor","edge"),
    }
    family_name,state_name=aliases.get(str(articulation),("mid","center"))
    families=mech.get("families",{}) if isinstance(mech.get("families",{}),dict) else {}
    states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
    fam=families.get(family_name,{}) if isinstance(families.get(family_name,{}),dict) else {}
    st=states.get(state_name,{}) if isinstance(states.get(state_name,{}),dict) else {}

    force=_impact_force_pulse(
        n,sr,v,
        soft_contact_s=float(st.get("stick_contact_soft_s",mech.get("stick_contact_soft_s",.00185))),
        hard_contact_s=float(st.get("stick_contact_hard_s",mech.get("stick_contact_hard_s",.00078))),
        shape=float(st.get("stick_force_shape",mech.get("stick_force_shape",1.42))),
    )
    ratios=mech.get("head_mode_ratios",[1.0,1.59,2.14,2.30,2.65,3.16])
    gains=mech.get("head_mode_gains",[1.0,.48,.31,.22,.15,.09])
    position=float(st.get("strike_position",.08))
    base=float(fam.get("head_base_hz",132.0))
    head_decay=float(fam.get("head_decay_s",.25))*float(st.get("head_decay_scale",1.0))
    top=_tom_membrane_bank(t,sr,rng,base,ratios,gains,head_decay,force,position)

    # Enclosed air transfers the low-order head motion to the resonant head.
    delay=max(0,int(float(fam.get("bottom_head_delay_s",.0020))*sr))
    bottom_force=np.zeros(n,dtype=np.float64)
    if delay<n:
        bottom_force[delay:]=force[:n-delay]*float(fam.get("bottom_transfer",.38))*float(st.get("bottom_transfer_scale",1.0))
    bottom=_tom_membrane_bank(
        t,sr,rng,
        base*float(fam.get("bottom_frequency_scale",.985)),ratios,
        np.asarray(gains,dtype=np.float64)*np.asarray(mech.get("bottom_gain_shape",[.86,.94,1.0,1.02,.98,.90]),dtype=np.float64),
        float(fam.get("bottom_decay_s",head_decay*.92))*float(st.get("bottom_decay_scale",1.0)),
        bottom_force,min(1.0,position+.04),
    )

    # The air cavity is not rendered as an unrelated sine.  It is a low-frequency
    # projection of the coupled head motion, so its pitch/decay stay causally tied
    # to the two membranes and family size.
    cavity=top+float(fam.get("cavity_bottom_mix",.78))*bottom
    cavity=_one_pole_highpass(cavity,sr,max(30.0,base*.36))
    cavity=_one_pole_lowpass(cavity,sr,min(sr*.42,float(fam.get("cavity_lowpass_hz",base*3.4))))
    cavity*=np.exp(-t/max(.04,float(fam.get("cavity_decay_s",head_decay*1.12))))

    shell=_tom_shell_response(t,sr,rng,force,fam)
    contact=_stick_contact_radiation(
        force,sr,float(mech.get("stick_contact_low_hz",520.0)),min(sr*.47,float(mech.get("stick_contact_high_hz",6200.0)))
    )

    sig=(float(fam.get("top_gain",.66))*float(st.get("top_gain_scale",1.0))*top
         +float(fam.get("bottom_gain",.24))*float(st.get("bottom_gain_scale",1.0))*bottom
         +float(fam.get("cavity_gain",.12))*float(st.get("cavity_gain_scale",1.0))*cavity
         +float(fam.get("shell_gain",.11))*float(st.get("shell_gain_scale",1.0))*shell
         +float(fam.get("contact_gain",.075))*float(st.get("contact_gain_scale",1.0))*contact)
    sig=_one_pole_highpass(sig,sr,float(fam.get("output_highpass_hz",42.0)))
    sig=_one_pole_lowpass(sig,sr,min(sr*.47,float(fam.get("output_lowpass_hz",7600.0))))
    sig=_softclip(sig,float(mech.get("drive",1.035)))
    sig=_declick(sig,sr,float(mech.get("declick_ms",.08)))
    return sig*(max(.015,v)**float(st.get("velocity_power",mech.get("velocity_power",.92))))*float(fam.get("output_gain",.62))*float(st.get("output_gain_scale",1.0))


def _stick_contact_radiation(force, sr, low_hz, high_hz):
    """Radiated short stick/contact component derived from the force pulse."""
    c=_bandpass(np.asarray(force,dtype=np.float64),sr,float(low_hz),float(high_hz))
    # A small force-slope term adds wooden-tip definition without replacing the
    # impact by a broadband noise burst.
    slope=np.diff(force,prepend=0.0)
    slope=_bandpass(slope,sr,max(500.0,float(low_hz)*1.15),min(sr*.47,float(high_hz)*1.12))
    c=c+0.32*slope
    peak=float(np.max(np.abs(c))+1e-12)
    return c/peak


def _plate_bank(t, sr, rng, freqs, gains, decay_s, *, jitter=.006, attack_s=0.0):
    """Compact deterministic inharmonic plate-mode bank.

    This is intentionally independent of the later S20-S24 cymbal engine.  The
    S19 drum core is the preservation anchor; only ride/crash are added here.
    """
    y=np.zeros(len(t),dtype=np.float64)
    total=0.0
    for i,(f0,g0) in enumerate(zip(freqs,gains)):
        f=float(f0)*_variation(rng,jitter)
        g=float(g0)*_variation(rng,.035)
        d=max(.02,float(decay_s)/(1.0+.055*i))
        y+=g*np.sin(2*np.pi*f*t+rng.uniform(-np.pi,np.pi))*np.exp(-t/d)
        total+=abs(g)
    y/=max(total,1e-12)
    if attack_s>0:
        y*=1.0-np.exp(-t/max(1e-5,float(attack_s)))
    return y


def _ride_cymbal(duration_s, sr, velocity, seed, patch, ext):
    cfg=_cfg(patch,"ride")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+1601)
    v=max(0.0,min(1.25,float(velocity)))
    strike_model=str(ext.get("strike_model",""))
    physical=strike_model in ("physical_v1","physical_v2")

    freqs=cfg.get("mode_freqs",[610.,845.,1120.,1510.,1980.,2580.,3270.,4010.,4920.,5960.,7140.,8420.,9720.])
    gains=cfg.get("mode_gains",[1.0,.92,.84,.74,.66,.58,.50,.43,.36,.30,.25,.20,.15])
    if physical:
        force=_impact_force_pulse(
            n,sr,v,
            soft_contact_s=float(cfg.get("stick_contact_soft_s",.0018)),
            hard_contact_s=float(cfg.get("stick_contact_hard_s",.00085)),
            shape=float(cfg.get("stick_force_shape",1.55)),
        )
        if strike_model=="physical_v2":
            plate=_dense_cymbal_plate_bank(
                t,sr,rng,freqs,gains,float(cfg.get("decay_s",1.55)),force,
                jitter=float(cfg.get("mode_jitter",.006)),
                cloud_size=int(cfg.get("plate_cloud_size",5)),
                cloud_spread=float(cfg.get("plate_cloud_spread",.024)),
                low_order_suppression=float(cfg.get("low_order_suppression",.68)),
            )
        else:
            plate=_coherent_plate_bank(t,sr,rng,freqs,gains,float(cfg.get("decay_s",1.55)),force,jitter=float(cfg.get("mode_jitter",.006)))
        contact=_stick_contact_radiation(
            force,sr,float(cfg.get("contact_low_hz",1900.0)),min(sr*.47,float(cfg.get("contact_high_hz",7200.0)))
        )
    else:
        plate=_plate_bank(t,sr,rng,freqs,gains,float(cfg.get("decay_s",1.55)),jitter=float(cfg.get("mode_jitter",.006)))
        contact=rng.standard_normal(n).astype(np.float64)
        contact=_bandpass(contact,sr,float(cfg.get("contact_low_hz",1900.0)),min(sr*.47,float(cfg.get("contact_high_hz",5600.0))))
        contact/=float(np.sqrt(np.mean(contact*contact))+1e-12)
        contact*=np.exp(-t/max(1e-4,float(cfg.get("contact_decay_s",.010))))

    # Weak upper wash sustains behind the ping without overtaking it.
    wash=rng.standard_normal(n).astype(np.float64)
    wash=_bandpass(wash,sr,float(cfg.get("wash_low_hz",3500.0)),min(sr*.47,float(cfg.get("wash_high_hz",9800.0))))
    wash/=float(np.sqrt(np.mean(wash*wash))+1e-12)
    wash*=np.exp(-t/max(.05,float(cfg.get("wash_decay_s",.72))))
    wash*=1.0-np.exp(-t/max(1e-5,float(cfg.get("wash_attack_s",.018))))

    vn=min(1.0,v)
    plate_dyn=float(cfg.get("plate_velocity_floor",.88))+float(cfg.get("plate_velocity_scale",.18))*(vn**float(cfg.get("plate_velocity_power",.70)))
    contact_dyn=float(cfg.get("contact_velocity_floor",.62))+float(cfg.get("contact_velocity_scale",.78))*(vn**float(cfg.get("contact_velocity_power",1.80)))
    wash_dyn=float(cfg.get("wash_velocity_floor",.80))+float(cfg.get("wash_velocity_scale",.24))*(vn**float(cfg.get("wash_velocity_power",1.10)))

    sig=(float(cfg.get("plate_gain",.72))*plate_dyn*plate
         +float(cfg.get("contact_gain",.115))*contact_dyn*contact
         +float(cfg.get("wash_gain",.075))*wash_dyn*wash)
    sig=_one_pole_highpass(sig,sr,float(cfg.get("highpass_hz",520.0)))
    sig=_one_pole_lowpass(sig,sr,min(sr*.47,float(cfg.get("lowpass_hz",10800.0))))
    sig=_softclip(sig,float(cfg.get("drive",1.025)))
    sig=_declick(sig,sr,float(cfg.get("strike_declick_ms",.08) if physical else cfg.get("declick_ms",.45)))
    return sig*v*float(cfg.get("output_gain",.42))

def _crash_cymbal(duration_s, sr, velocity, seed, patch, ext):
    cfg=_cfg(patch,"crash")
    n=max(1,int(duration_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    rng=_rng(seed+1701)
    v=max(0.0,min(1.25,float(velocity)))
    strike_model=str(ext.get("strike_model",""))
    physical=strike_model in ("physical_v1","physical_v2")

    if physical:
        force=_impact_force_pulse(
            n,sr,v,
            soft_contact_s=float(cfg.get("stick_contact_soft_s",.0024)),
            hard_contact_s=float(cfg.get("stick_contact_hard_s",.00115)),
            shape=float(cfg.get("stick_force_shape",1.38)),
        )
        if strike_model=="physical_v2":
            bank=lambda freqs,gains,decay,attack=0.0: _dense_cymbal_plate_bank(
                t,sr,rng,freqs,gains,decay,force,
                jitter=float(cfg.get("mode_jitter",.008)),attack_s=attack,
                cloud_size=int(cfg.get("plate_cloud_size",5)),
                cloud_spread=float(cfg.get("plate_cloud_spread",.030)),
                low_order_suppression=float(cfg.get("low_order_suppression",.58)),
            )
        else:
            bank=lambda freqs,gains,decay,attack=0.0: _coherent_plate_bank(
                t,sr,rng,freqs,gains,decay,force,jitter=float(cfg.get("mode_jitter",.008)),attack_s=attack
            )
    else:
        force=None
        bank=lambda freqs,gains,decay,attack=0.0: _plate_bank(
            t,sr,rng,freqs,gains,decay,jitter=float(cfg.get("mode_jitter",.008)),attack_s=attack
        )

    low=bank(
        cfg.get("low_mode_freqs",[360.,505.,690.,910.,1180.,1470.]),
        cfg.get("low_mode_gains",[1.0,.88,.73,.58,.45,.34]),
        float(cfg.get("low_decay_s",1.90)),
    )
    mid=bank(
        cfg.get("mid_mode_freqs",[1260.,1570.,1910.,2310.,2780.,3290.,3840.]),
        cfg.get("mid_mode_gains",[.92,.86,.78,.68,.58,.48,.38]),
        float(cfg.get("mid_decay_s",1.55)),
        float(cfg.get("mid_bloom_s",.018))*(1.08-.18*min(1.0,v)),
    )
    high=bank(
        cfg.get("high_mode_freqs",[3450.,3970.,4560.,5220.,5940.,6710.,7530.,8420.,9360.,10200.]),
        cfg.get("high_mode_gains",[.82,.78,.72,.66,.59,.52,.45,.38,.31,.24]),
        float(cfg.get("high_decay_s",1.18)),
        float(cfg.get("high_bloom_s",.052))*(1.12-.28*min(1.0,v)),
    )

    shimmer=rng.standard_normal(n).astype(np.float64)
    shimmer=_bandpass(shimmer,sr,float(cfg.get("shimmer_low_hz",3200.0)),min(sr*.47,float(cfg.get("shimmer_high_hz",10500.0))))
    shimmer/=float(np.sqrt(np.mean(shimmer*shimmer))+1e-12)
    shimmer*=np.exp(-t/max(.05,float(cfg.get("shimmer_decay_s",.95))))
    shimmer*=1.0-np.exp(-t/max(1e-5,float(cfg.get("shimmer_bloom_s",.035))))

    if physical:
        contact=_stick_contact_radiation(
            force,sr,float(cfg.get("contact_low_hz",700.0)),min(sr*.47,float(cfg.get("contact_high_hz",7600.0)))
        )
    else:
        contact=rng.standard_normal(n).astype(np.float64)
        contact=_bandpass(contact,sr,float(cfg.get("contact_low_hz",900.0)),min(sr*.47,float(cfg.get("contact_high_hz",7200.0))))
        contact/=float(np.sqrt(np.mean(contact*contact))+1e-12)
        contact*=np.exp(-t/max(1e-4,float(cfg.get("contact_decay_s",.012))))

    vn=min(1.0,v)
    body_dyn=float(cfg.get("body_velocity_floor",.90))+float(cfg.get("body_velocity_scale",.14))*(vn**float(cfg.get("body_velocity_power",.80)))
    bloom_dyn=float(cfg.get("bloom_velocity_floor",.64))+float(cfg.get("bloom_velocity_scale",.62))*(vn**float(cfg.get("bloom_velocity_power",1.55)))
    contact_dyn=float(cfg.get("contact_velocity_floor",.46))+float(cfg.get("contact_velocity_scale",1.02))*(vn**float(cfg.get("contact_velocity_power",2.10)))
    shimmer_dyn=float(cfg.get("shimmer_velocity_floor",.70))+float(cfg.get("shimmer_velocity_scale",.42))*(vn**float(cfg.get("shimmer_velocity_power",1.45)))

    sig=(float(cfg.get("low_gain",.54))*body_dyn*low
         +float(cfg.get("mid_gain",.48))*bloom_dyn*mid
         +float(cfg.get("high_gain",.38))*bloom_dyn*high
         +float(cfg.get("shimmer_gain",.105))*shimmer_dyn*shimmer
         +float(cfg.get("contact_gain",.075))*contact_dyn*contact)
    sig=_one_pole_highpass(sig,sr,float(cfg.get("highpass_hz",260.0)))
    sig=_one_pole_lowpass(sig,sr,min(sr*.47,float(cfg.get("lowpass_hz",11000.0))))
    sig=_softclip(sig,float(cfg.get("drive",1.02)))
    sig=_declick(sig,sr,float(cfg.get("strike_declick_ms",.08) if physical else cfg.get("declick_ms",.5)))
    return sig*v*float(cfg.get("output_gain",.34))

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


def render_drum_event(kind, duration_s, sr, velocity, seed=0, pan=0.0, patch=None, hi_hat_pedal_openness=None, hi_hat_collision_profile=None):
    realism=_realism(patch)
    if kind=="kick":
        minimum=float(realism.get("kick_tail_s",0.36)) if realism else 0.28
        sig=kick(max(duration_s,minimum),sr,velocity,patch=patch,seed=seed)
        pan=0.0
    elif kind in ("snare_center","snare_ghost","snare_rimshot","snare_cross_stick"):
        mech=_snare_mechanics(patch)
        if mech is None:
            sig=np.zeros(max(1,int(duration_s*sr)))
        else:
            states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
            aliases={"snare_center":"center","snare_ghost":"ghost","snare_rimshot":"rimshot","snare_cross_stick":"cross_stick"}
            state=states.get(aliases[kind],{}) if isinstance(states.get(aliases[kind],{}),dict) else {}
            minimum=float(state.get("tail_s",mech.get("tail_s",.24)))
            sig=_articulated_snare(max(duration_s,minimum),sr,velocity,seed,patch,mech,kind)
            pan=0.04 if pan==0 else pan
    elif kind=="snare":
        minimum=float(realism.get("snare_tail_s",0.34)) if realism else 0.20
        sig=snare(max(duration_s,minimum),sr,velocity,seed,patch=patch)
        pan=0.04 if pan==0 else pan
    elif kind=="hat":
        minimum=float(realism.get("hat_tail_s",0.13)) if realism else 0.07
        sig=hat(max(duration_s,minimum),sr,velocity,seed,patch=patch)
        pan=0.18 if pan==0 else pan
    elif kind in ("hat_tight_closed","hat_closed","hat_half_open","hat_open","hat_pedal","hat_foot_splash"):
        mech=_hi_hat_mechanics(patch)
        if mech is None:
            sig=np.zeros(max(1,int(duration_s*sr)))
        else:
            states=mech.get("states",{}) if isinstance(mech.get("states",{}),dict) else {}
            aliases={"hat_tight_closed":"tight_closed","hat_closed":"closed","hat_half_open":"half_open","hat_open":"open","hat_pedal":"pedal_chick","hat_foot_splash":"foot_splash"}
            state=states.get(aliases[kind],{}) if isinstance(states.get(aliases[kind],{}),dict) else {}
            minimum=float(state.get("tail_s",mech.get("tail_s",.60)))
            sig=_two_cymbal_hat(max(duration_s,minimum),sr,velocity,seed,patch,mech,kind,hi_hat_pedal_openness,hi_hat_collision_profile)
            pan=0.18 if pan==0 else pan
    elif kind in ("tom_high","tom_high_edge","tom_mid","tom_mid_edge","tom_floor","tom_floor_edge"):
        mech=_tom_mechanics(patch)
        if mech is None:
            sig=np.zeros(max(1,int(duration_s*sr)))
        else:
            aliases={
                "tom_high":("high","center"), "tom_high_edge":("high","edge"),
                "tom_mid":("mid","center"), "tom_mid_edge":("mid","edge"),
                "tom_floor":("floor","center"), "tom_floor_edge":("floor","edge"),
            }
            family_name,_state_name=aliases[kind]
            families=mech.get("families",{}) if isinstance(mech.get("families",{}),dict) else {}
            fam=families.get(family_name,{}) if isinstance(families.get(family_name,{}),dict) else {}
            minimum=float(fam.get("tail_s",mech.get("tail_s",.62)))
            sig=_articulated_tom(max(duration_s,minimum),sr,velocity,seed,patch,mech,kind)
            if pan==0:
                pan={"high":-.14,"mid":.02,"floor":.18}.get(family_name,0.0)
    elif kind=="ride":
        ext=_cymbal_extension(patch)
        if ext is None:
            sig=np.zeros(max(1,int(duration_s*sr)))
        else:
            minimum=float(ext.get("ride_tail_s",1.80))
            sig=_ride_cymbal(max(duration_s,minimum),sr,velocity,seed,patch,ext)
            pan=0.26 if pan==0 else pan
    elif kind=="crash":
        ext=_cymbal_extension(patch)
        if ext is None:
            sig=np.zeros(max(1,int(duration_s*sr)))
        else:
            minimum=float(ext.get("crash_tail_s",2.20))
            sig=_crash_cymbal(max(duration_s,minimum),sr,velocity,seed,patch,ext)
            pan=-0.24 if pan==0 else pan
    else:
        sig=np.zeros(max(1,int(duration_s*sr)))
    return equal_power_pan(sig,pan)
