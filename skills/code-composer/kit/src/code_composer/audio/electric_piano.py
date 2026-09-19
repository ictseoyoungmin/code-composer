import math
import numpy as np
from scipy.signal import lfilter, resample_poly

from ..core.theory import midi_to_hz


def _lowpass(x,sr,cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    a=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([a],[1.0,-(1.0-a)],x)


def _highpass(x,sr,cutoff):
    return x-_lowpass(x,sr,cutoff)


def _equal_power(sig,pan):
    pan=max(-1.0,min(1.0,float(pan)))
    a=(pan+1.0)*math.pi/4.0
    return sig*math.cos(a),sig*math.sin(a)


def _key_noise(n,sr,midi,velocity,cfg):
    gain=float(cfg.get('key_noise_gain',0.008))
    if gain<=0:
        return np.zeros(n)
    seed=int(cfg.get('seed',419))+int(midi)*3571+n%65521
    rng=np.random.default_rng(seed)
    noise=rng.standard_normal(n)
    noise=_lowpass(_highpass(noise,sr,180.0),sr,2200.0)
    rms=float(np.sqrt(np.mean(noise*noise))+1e-12)
    t=np.arange(n,dtype=np.float64)/sr
    env=np.exp(-t/0.010)
    return noise/rms*env*gain*(0.45+0.75*velocity)


def _tine(base,t,v,cfg,sr):
    decay=float(cfg.get('decay_s',2.8))
    release=float(cfg.get('release_s',0.55))
    bell=float(cfg.get('bell_gain',0.38))
    bark=float(cfg.get('bark_gain',0.16))
    bright=float(cfg.get('velocity_brightness',1.0))
    b=float(cfg.get('inharmonicity',0.0018))

    env=np.exp(-t/max(.05,decay))
    # Tine: strong fundamental + stretched bell partials. Harder strikes excite bell/bark.
    out=np.sin(2*np.pi*base*t+0.13)*env
    for k,w in ((2,.34),(3,.17),(5,.08)):
        f=base*k*math.sqrt(1.0+b*k*k)
        if f >= sr*0.45:
            continue
        out += np.sin(2*np.pi*f*t+0.21*k)*env**(1.0+.15*k)*w*(0.72+bright*v*.45)
    bell_env=np.exp(-t/max(.04,decay*.32))
    bell_hz=base*6.97
    if bell_hz < sr*0.45:
        out += np.sin(2*np.pi*bell_hz*t+0.4)*bell_env*bell*(0.25+v**1.7)
    # Velocity bark is harmonic saturation on the early fundamental, not broadband noise.
    bark_env=np.exp(-t/.075)
    out += np.tanh(np.sin(2*np.pi*base*t)*2.4)*bark_env*bark*(v**2.0)
    return out,release


def _reed(base,t,v,cfg,sr):
    decay=float(cfg.get('decay_s',2.0))
    release=float(cfg.get('release_s',0.42))
    bell=float(cfg.get('bell_gain',0.12))
    bark=float(cfg.get('bark_gain',0.34))
    bright=float(cfg.get('velocity_brightness',1.0))
    env=np.exp(-t/max(.05,decay))
    out=np.zeros_like(t)
    # Reed family: stronger odd partials and midrange bite.
    for k,w in ((1,1.0),(2,.18),(3,.42),(5,.20),(7,.10)):
        f=base*k
        if f >= sr*0.45:
            continue
        out += np.sin(2*np.pi*f*t+0.11*k)*env**(1+.08*k)*w
    bell_hz=base*4.05
    if bell_hz < sr*0.45:
        out += np.sin(2*np.pi*bell_hz*t+.7)*np.exp(-t/.34)*bell*(.3+v)
    out += np.tanh(out*2.6)*np.exp(-t/.11)*bark*(v**1.8)*(0.55+0.45*bright)
    return out*.74,release


def _digital_fm(base,t,v,cfg,sr):
    decay=float(cfg.get('decay_s',3.2))
    release=float(cfg.get('release_s',.8))
    bell=float(cfg.get('bell_gain',0.52))
    bark=float(cfg.get('bark_gain',0.08))
    bright=float(cfg.get('velocity_brightness',1.0))
    env=np.exp(-t/max(.05,decay))
    mod_env=np.exp(-t/max(.03,decay*.36))
    index=(1.0+3.0*v*bright)*mod_env
    mod=np.sin(2*np.pi*base*3.0*t+.2)
    carrier=np.sin(2*np.pi*base*t + index*mod)
    bell_sig=np.sin(2*np.pi*base*7.0*t + .35)*mod_env
    out=carrier*env + bell_sig*bell*(.25+.9*v)
    out += np.sin(2*np.pi*base*2*t)*env*.12
    out += np.tanh(carrier*2.2)*np.exp(-t/.09)*bark*v*v
    return out*.82,release


def _render_electric_piano_core(midi,duration_s,sr,patch,velocity=1.0,performance=None):
    graph=patch.get('electric_piano_graph',patch.get('graph',{}))
    perf=performance or {}
    v=max(.01,min(1.0,float(velocity)))
    tone=graph.get('tone',{})
    release=max(.02,float(tone.get('release_s',.55))*float(perf.get('release_scale',1.0)))
    total=max(.01,float(duration_s))+release
    n=max(1,int(total*sr))
    t=np.arange(n,dtype=np.float64)/sr
    base=midi_to_hz(midi)
    mechanism=tone.get('mechanism','tine')

    if mechanism=='reed':
        mono,_=_reed(base,t,v,tone,sr)
    elif mechanism=='digital_fm':
        mono,_=_digital_fm(base,t,v,tone,sr)
    else:
        mono,_=_tine(base,t,v,tone,sr)

    # Symbolic note-off changes the decay slope rather than introducing a hard gate.
    off=min(n,max(0,int(float(duration_s)*sr)))
    if off<n:
        rt=np.arange(n-off,dtype=np.float64)/sr
        mono[off:]*=np.exp(-rt/release)

    pickup=graph.get('pickup',{})
    mono=_highpass(mono,sr,float(pickup.get('highpass_hz',80.0)))
    mono=_lowpass(mono,sr,float(pickup.get('cutoff_hz',8200.0)))
    pdrive=float(pickup.get('drive',1.15))
    mono=np.tanh(mono*pdrive)/max(1e-9,math.tanh(max(.1,pdrive)))

    amp=graph.get('amp',{})
    adrive=float(amp.get('drive',1.08))
    mono=np.tanh(mono*adrive)/max(1e-9,math.tanh(max(.1,adrive)))
    mono=_lowpass(mono,sr,float(amp.get('cutoff_hz',7600.0)))

    mono += _key_noise(n,sr,midi,v,graph.get('mechanics',{}))

    modulation=graph.get('modulation',{})
    mtype=modulation.get('type','none')
    width=max(0.0,min(1.0,float(graph.get('stereo_width',.55))))
    base_pan=max(-width,min(width,(midi-60)/42.0*width))
    if mtype=='tremolo':
        rate=float(modulation.get('rate_hz',4.6))
        depth=max(0.0,min(1.0,float(modulation.get('depth',.18))))
        lmod=1.0-depth*.5+depth*.5*np.sin(2*np.pi*rate*t)
        rmod=1.0-depth*.5+depth*.5*np.sin(2*np.pi*rate*t+math.pi)
        l,r=_equal_power(mono,base_pan)
        left=l*lmod; right=r*rmod
    elif mtype=='chorus':
        rate=float(modulation.get('chorus_rate_hz',.55))
        cents=float(modulation.get('chorus_depth_cents',6.5))
        # Deterministic two-voice phase modulation gives a stage-piano chorus without delay randomness.
        phase_depth=(2**(cents/1200.0)-1.0)*base/max(.1,rate)
        phase=phase_depth*np.sin(2*np.pi*rate*t)
        wet=np.sin(2*np.pi*base*t+phase)*np.exp(-t/max(.05,float(tone.get('decay_s',2.7))))
        l,r=_equal_power(mono,base_pan*.5)
        wl,wr=_equal_power(wet*.20,-base_pan*.8)
        left=l+wl; right=r+wr
    else:
        left,right=_equal_power(mono,base_pan)

    amp_scale=.18+.82*(v**.78)
    gain=float(graph.get('output_gain',.64))
    stereo=np.stack([left,right],axis=1)*amp_scale*gain
    # short edge guard
    m=min(len(stereo)//2,max(1,int(.0005*sr)))
    ramp=np.linspace(0,1,m)
    stereo[:m]*=ramp[:,None]
    stereo[-m:]*=ramp[::-1,None]
    peak=float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak>1.0:
        stereo/=peak
    return stereo



def render_electric_piano_note(midi,duration_s,sr,patch,velocity=1.0,performance=None):
    """Render electric piano with deterministic internal oversampling.

    Nonlinear pickup/amp stages and FM/bark generation happen above the output
    sample rate, then are polyphase-downsampled. This prevents the high-register
    aliasing that made the first R5 dogfood sound brittle/broken.
    """
    sr=int(sr)
    if sr <= 24000:
        factor=4
    elif sr <= 48000:
        factor=2
    else:
        factor=1

    if factor==1:
        return _render_electric_piano_core(
            midi,duration_s,sr,patch,velocity=velocity,performance=performance
        )

    internal_sr=sr*factor
    hi=_render_electric_piano_core(
        midi,duration_s,internal_sr,patch,velocity=velocity,performance=performance
    )
    # FIR polyphase low-pass is deterministic and removes above-Nyquist products.
    out=resample_poly(hi,up=1,down=factor,axis=0,padtype='constant')

    graph=patch.get('electric_piano_graph',patch.get('graph',{}))
    release=max(.02,float(graph.get('tone',{}).get('release_s',.55))*
                float((performance or {}).get('release_scale',1.0)))
    target=max(1,int((max(.01,float(duration_s))+release)*sr))
    if len(out)>target:
        out=out[:target]
    elif len(out)<target:
        out=np.pad(out,((0,target-len(out)),(0,0)))

    peak=float(np.max(np.abs(out))) if len(out) else 0.0
    if peak>1.0:
        out/=peak
    return out

def electric_piano_tail_seconds(patch):
    graph=patch.get('electric_piano_graph',patch.get('graph',{}))
    tone=graph.get('tone',{})
    return max(.02,float(tone.get('release_s',.55)))


__all__=['render_electric_piano_note','electric_piano_tail_seconds']
