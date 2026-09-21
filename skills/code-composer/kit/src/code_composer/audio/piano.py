import math
import numpy as np
from scipy.signal import lfilter
from ..core.theory import midi_to_hz
from .piano_design import resolve_piano_design
from .electric_piano import render_electric_piano_note, electric_piano_tail_seconds


def _smoothstep01(x):
    x=np.clip(x,0.0,1.0)
    return x*x*(3.0-2.0*x)


def _one_pole_lowpass(x,sr,cutoff):
    cutoff=max(20.0,min(float(cutoff),sr*0.45))
    alpha=1.0-math.exp(-2.0*math.pi*cutoff/sr)
    return lfilter([alpha],[1.0,-(1.0-alpha)],x)


def _one_pole_highpass(x,sr,cutoff):
    return x-_one_pole_lowpass(x,sr,cutoff)


def _equal_power(sig,pan):
    pan=max(-1.0,min(1.0,float(pan)))
    angle=(pan+1.0)*math.pi/4.0
    return sig*math.cos(angle),sig*math.sin(angle)


def _string_count(midi,cfg):
    low_split=int(cfg.get('low_split_midi',43))
    high_split=int(cfg.get('high_split_midi',61))
    if midi < low_split:
        return int(cfg.get('low_strings',1))
    if midi < high_split:
        return int(cfg.get('mid_strings',2))
    return int(cfg.get('high_strings',3))


def _note_pan(midi,width):
    # Acoustic keyboard perspective: bass left, treble right.
    return max(-width,min(width,(float(midi)-60.0)/36.0*width))


def _hammer_layer(base_hz,n,sr,midi,velocity,cfg,strike_seed=None,strike_cfg=None):
    gain=float(cfg.get('gain',0.11))
    noise_gain=float(cfg.get('noise_gain',0.055))
    decay=max(0.001,float(cfg.get('decay_s',0.018)))
    tonal_gain=float(cfg.get('tonal_gain',0.035))
    seed=int(cfg.get('seed',193)) + int(midi)*7919 + n%65521
    rng=np.random.default_rng(seed)
    strike_cfg=strike_cfg if isinstance(strike_cfg,dict) else {}
    identity_active=bool(strike_seed is not None and any(float(strike_cfg.get(k,0.0))>0 for k in (
        'phase_jitter_rad','unison_phase_jitter_rad','partial_phase_jitter_rad',
        'hammer_noise_mix','hammer_gain_variation','hammer_decay_variation'
    )))
    strike_rng=np.random.default_rng(int(strike_seed)&0xFFFFFFFF) if identity_active else None
    gain_scale=1.0
    tonal_phase_offset=0.0
    if strike_rng is not None:
        decay_var=max(0.0,min(.30,float(strike_cfg.get('hammer_decay_variation',0.0))))
        gain_var=max(0.0,min(.20,float(strike_cfg.get('hammer_gain_variation',0.0))))
        decay*=1.0 + float(strike_rng.uniform(-decay_var,decay_var))
        gain_scale*=1.0 + float(strike_rng.uniform(-gain_var,gain_var))
        tonal_phase_offset=float(strike_rng.uniform(-1.0,1.0))*float(strike_cfg.get('phase_jitter_rad',0.0))*.35
    t=np.arange(n,dtype=np.float64)/sr
    env=np.exp(-t/decay)
    ma=min(n,max(1,int(float(cfg.get('attack_s',0.0005))*sr)))
    env[:ma]*=_smoothstep01(np.linspace(0,1,ma,endpoint=True))

    # Harder playing opens the hammer spectrum rather than only making it louder.
    v=max(0.0,min(1.0,float(velocity)))
    low=float(cfg.get('low_cutoff_hz',700.0))
    soft_high=float(cfg.get('soft_high_cutoff_hz',3200.0))
    hard_high=float(cfg.get('hard_high_cutoff_hz',11500.0))
    register=max(0.0,min(1.0,(midi-24)/72.0))
    high=soft_high+(hard_high-soft_high)*(v**1.45)
    high*=0.9+0.2*register
    high=min(high,sr*0.44)
    noise=rng.standard_normal(n).astype(np.float64)
    if strike_rng is not None:
        mix=max(0.0,min(1.0,float(strike_cfg.get('hammer_noise_mix',0.0))))
        if mix>0:
            strike_noise=strike_rng.standard_normal(n).astype(np.float64)
            noise=noise*(1.0-mix)+strike_noise*mix
    noise=_one_pole_highpass(noise,sr,low)
    noise=_one_pole_lowpass(noise,sr,high)
    nrms=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise=noise/nrms

    harmonic=float(cfg.get('tonal_harmonic',7.0))
    tonal_hz=min(base_hz*harmonic,sr*0.43)
    tonal=np.sin(2*np.pi*tonal_hz*t + 0.17*midi + tonal_phase_offset)
    amp=(gain*(0.48+0.72*v))*env*gain_scale
    return noise*amp*noise_gain + tonal*env*tonal_gain*(0.35+0.8*v)


def _resonance_layer(base_hz,n,sr,midi,velocity,pedal,cfg,noteoff_env=None):
    """Low-level string/body reinforcement without inventing a release melody.

    In the no-pedal state the dampers must dominate after key release.  Historical
    versions used a long independent oscillator bank (including 1.5*f0), which could
    outlive the struck strings and become audible as a new pitched tail.  Keep the
    dry resonance harmonic and subordinate, and let sustain-pedal state opt into the
    longer sympathetic component.
    """
    base_gain=float(cfg.get('gain',0.025))
    pedal_gain=float(cfg.get('pedal_gain',0.075)) if pedal else 0.0
    no_pedal_scale=max(0.0,min(1.0,float(cfg.get('no_pedal_gain_scale',0.22))))
    gain=(base_gain if pedal else base_gain*no_pedal_scale)+pedal_gain
    if gain<=0:
        return np.zeros(n,dtype=np.float64)
    decay=max(0.05,float(cfg.get('decay_s',2.4 if pedal else 1.2)))
    if not pedal:
        decay*=max(0.05,min(1.0,float(cfg.get('no_pedal_decay_scale',0.30))))
    t=np.arange(n,dtype=np.float64)/sr
    env=np.exp(-t/decay)
    if noteoff_env is not None:
        env*=np.asarray(noteoff_env,dtype=np.float64)[:n]

    ratios=list(cfg.get('ratios',[1.0,2.0,3.0,4.0]))
    weights=list(cfg.get('weights',[1.0,0.36,0.20,0.10]))
    if not pedal:
        # A no-pedal resonance layer is not a sympathetic-string synthesizer.  Reject
        # non-harmonic ratio tones (notably the old 1.5*f0 component) so the release
        # cannot reveal a note that was never struck.
        harmonic=[]
        for ratio,w in zip(ratios,weights):
            r=float(ratio); nearest=round(r)
            if nearest>=1 and abs(r-nearest)<=0.035:
                harmonic.append((float(nearest),float(w)))
        if harmonic:
            ratios=[r for r,_ in harmonic]; weights=[w for _,w in harmonic]
        else:
            ratios=[1.0,2.0,3.0]; weights=[1.0,0.28,0.12]

    out=np.zeros(n,dtype=np.float64)
    for i,(ratio,w) in enumerate(zip(ratios,weights)):
        freq=base_hz*float(ratio)
        if freq>=sr*0.45: continue
        phase=0.31*(midi+i*13)
        out += np.sin(2*np.pi*freq*t+phase)*float(w)
    norm=max(1.0,sum(abs(float(w)) for w in weights))
    return out/norm*env*gain*(0.4+0.6*max(0.0,min(1.0,velocity)))



def _mechanical_layer(n,sr,midi,velocity,duration_s,cfg):
    """Deterministic key/damper mechanics, intentionally subordinate to the strings."""
    key_gain=float(cfg.get('key_noise_gain',0.0))
    damper_gain=float(cfg.get('damper_noise_gain',0.0))
    if key_gain<=0 and damper_gain<=0:
        return np.zeros(n,dtype=np.float64)
    seed=int(cfg.get('seed',271))+int(midi)*4513+n%65521
    rng=np.random.default_rng(seed)
    noise=rng.standard_normal(n).astype(np.float64)
    noise=_one_pole_highpass(noise,sr,90.0)
    noise=_one_pole_lowpass(noise,sr,1900.0)
    rms=float(np.sqrt(np.mean(noise*noise))+1e-12)
    noise/=rms
    t=np.arange(n,dtype=np.float64)/sr
    out=noise*np.exp(-t/.010)*key_gain*(.35+.75*velocity)
    off=min(n-1,max(0,int(float(duration_s)*sr)))
    if damper_gain>0 and off<n-1:
        m=min(n-off,max(1,int(.045*sr)))
        rt=np.arange(m,dtype=np.float64)/sr
        out[off:off+m]+=noise[off:off+m]*np.exp(-rt/.016)*damper_gain*(.35+.45*velocity)
    return out


def _bridge_transfer(x,sr,cfg):
    coupling=max(0.0,min(1.0,float(cfg.get('coupling',0.0))))
    if coupling<=0:
        return x
    low=float(cfg.get('low_cutoff_hz',55.0))
    high=float(cfg.get('high_cutoff_hz',12500.0))
    wet=_one_pole_lowpass(_one_pole_highpass(x,sr,low),sr,high)
    return x*(1.0-coupling*.34)+wet*(coupling*.62)


def _modal_soundboard(x,sr,cfg,decay_scale_multiplier=1.0):
    """Track-wide damped modal body excited by the summed piano signal."""
    gain=float(cfg.get('modal_gain',0.0))
    if gain<=0 or len(x)==0:
        return np.zeros_like(x)
    modes=cfg.get('modes_hz',[])
    weights=cfg.get('mode_weights',[])
    decays=cfg.get('mode_decays',[])
    if not modes or len(weights)!=len(modes) or len(decays)!=len(modes):
        return np.zeros_like(x)
    mono=.5*(x[:,0]+x[:,1])
    out=np.zeros_like(x)
    decay_scale=max(.02,float(cfg.get('modal_decay_scale',1.0))*float(decay_scale_multiplier))
    norm=max(1.0,sum(abs(float(w)) for w in weights))
    # Stable second-order resonators. The input is lightly high-passed so DC/low rumble
    # does not dominate the wooden body response.
    excitation=_one_pole_highpass(mono,sr,35.0)
    for idx,(freq,w,decay) in enumerate(zip(modes,weights,decays)):
        f=float(freq)
        if f<=20 or f>=sr*.44:
            continue
        tau=max(.03,float(decay)*decay_scale)
        r=math.exp(-1.0/(tau*sr))
        theta=2.0*math.pi*f/sr
        # Normalize feed by (1-r) so modes remain bounded as decay grows.
        b=[max(1e-7,1.0-r)]
        a=[1.0,-2.0*r*math.cos(theta),r*r]
        mode=lfilter(b,a,excitation)*float(w)/norm
        pan=((idx/max(1,len(modes)-1))*2.0-1.0)*.32
        ml,mr=_equal_power(mode,pan)
        out[:,0]+=ml; out[:,1]+=mr
    return out*gain



def _sustain_pedal_controls(events):
    return sorted(
        [
            ev for ev in (events or [])
            if ev.get('event_type') == 'piano_control'
            and ev.get('control') == 'sustain_pedal'
        ],
        key=lambda ev: (float(ev.get('start_beat', 0.0)), float(ev.get('duration_beats', 0.0))),
    )


def _interp_pedal_points(control, beat):
    start=float(control.get('start_beat',0.0))
    duration=max(1e-12,float(control.get('duration_beats',0.0)))
    local=max(0.0,min(duration,float(beat)-start))
    points=control.get('points') or []
    if not points:
        return 0.0
    if local <= float(points[0]['offset_beats']):
        return float(points[0]['position'])
    for a,b in zip(points,points[1:]):
        xa=float(a['offset_beats']); xb=float(b['offset_beats'])
        if local <= xb + 1e-12:
            ya=float(a['position']); yb=float(b['position'])
            if xb <= xa + 1e-12:
                return yb
            u=(local-xa)/(xb-xa)
            return ya+(yb-ya)*u
    return float(points[-1]['position'])


def resolve_sustain_pedal_position(events, beat):
    """Resolve authored sustain-pedal state at ``beat`` with persistent final state.

    Explicit piano-control curves are the authority whenever present.  Between curves,
    the final position of the previous curve remains active, matching a physical pedal
    that stays where the performer left it until another authored motion changes it.
    """
    controls=_sustain_pedal_controls(events)
    if not controls:
        return 0.0
    state=0.0
    t=float(beat)
    for control in controls:
        start=float(control.get('start_beat',0.0))
        duration=float(control.get('duration_beats',0.0))
        end=start+duration
        if t < start - 1e-12:
            return max(0.0,min(1.0,state))
        if t <= end + 1e-12:
            return max(0.0,min(1.0,_interp_pedal_points(control,t)))
        points=control.get('points') or []
        if points:
            state=float(points[-1]['position'])
    return max(0.0,min(1.0,state))


def _next_sustain_pedal_release_beat(events, beat, threshold=0.5):
    """Return the first future down->up threshold crossing after ``beat``."""
    t=float(beat)
    threshold=float(threshold)
    if resolve_sustain_pedal_position(events,t) < threshold:
        return None
    controls=_sustain_pedal_controls(events)
    state=resolve_sustain_pedal_position(events,t)
    for control in controls:
        start=float(control.get('start_beat',0.0))
        end=start+float(control.get('duration_beats',0.0))
        if end <= t + 1e-12:
            continue
        points=control.get('points') or []
        if not points:
            continue
        first=float(points[0]['position'])
        if start > t + 1e-12 and state >= threshold and first < threshold:
            return start
        abs_points=[(start+float(p['offset_beats']),float(p['position'])) for p in points]
        for (ta,ya),(tb,yb) in zip(abs_points,abs_points[1:]):
            if tb <= t + 1e-12:
                continue
            seg_start=max(t,ta)
            if seg_start > ta + 1e-12:
                u=(seg_start-ta)/max(1e-12,tb-ta)
                ya=ya+(yb-ya)*u
                ta=seg_start
            if ya >= threshold and yb < threshold:
                if abs(yb-ya) <= 1e-12:
                    return tb
                u=(threshold-ya)/(yb-ya)
                return ta+(tb-ta)*u
        state=float(points[-1]['position'])
        t=max(t,end)
    return None


def _max_sustain_pedal_position(events, start_beat, end_beat):
    start=float(start_beat); end=max(start,float(end_beat))
    values=[resolve_sustain_pedal_position(events,start),resolve_sustain_pedal_position(events,end)]
    for control in _sustain_pedal_controls(events):
        cstart=float(control.get('start_beat',0.0))
        for point in control.get('points') or []:
            at=cstart+float(point['offset_beats'])
            if start-1e-12 <= at <= end+1e-12:
                values.append(float(point['position']))
    return max(values or [0.0])


def _explicit_sustain_pedal_envelope(events,n,sr,beat_s):
    controls=_sustain_pedal_controls(events)
    if not controls or n<=0:
        return None
    out=np.zeros(int(n),dtype=np.float64)
    cursor=0
    state=0.0
    samples_per_beat=float(sr)*float(beat_s)
    for control in controls:
        start=max(0,min(n,int(round(float(control.get('start_beat',0.0))*samples_per_beat))))
        if start>cursor:
            out[cursor:start]=state
        points=control.get('points') or []
        if not points:
            cursor=max(cursor,start)
            continue
        abs_samples=[]
        for point in points:
            idx=max(0,min(n-1,int(round((float(control.get('start_beat',0.0))+float(point['offset_beats']))*samples_per_beat))))
            abs_samples.append((idx,float(point['position'])))
        for (ia,ya),(ib,yb) in zip(abs_samples,abs_samples[1:]):
            if ib<=ia:
                continue
            lo=max(cursor,ia); hi=min(n,ib+1)
            if hi<=lo:
                continue
            denom=max(1,ib-ia)
            u=(np.arange(lo,hi,dtype=np.float64)-ia)/denom
            out[lo:hi]=ya+(yb-ya)*u
        cursor=max(cursor,min(n,abs_samples[-1][0]+1))
        state=float(points[-1]['position'])
    if cursor<n:
        out[cursor:]=state
    return np.clip(out,0.0,1.0)


def _causal_pedal_smooth(x,sr,time_s=0.012):
    x=np.asarray(x,dtype=np.float64)
    if len(x)==0 or time_s<=0:
        return x
    alpha=1.0-math.exp(-1.0/max(1.0,float(time_s)*float(sr)))
    y=np.empty_like(x)
    state=float(x[0])
    for i,value in enumerate(x):
        state += alpha*(float(value)-state)
        y[i]=state
    return y


def render_piano_track_with_controls(events,n,sr,patch,beat_s):
    """Render acoustic piano with explicit persistent sustain-pedal control state.

    Legacy note-local ``performance.pedal`` behavior is untouched when a track has no
    ``piano_control`` events.  Once explicit sustain control is present, that timeline
    becomes authoritative: a released key remains undamped only until the next authored
    pedal-up crossing, then the normal S14 damper release takes over.  A later repedal
    does not resurrect energy that has already been damped.
    """
    controls=_sustain_pedal_controls(events)
    if not controls:
        return None
    if patch.get('piano_engine')=='electric' or 'electric_piano_graph' in patch:
        return None
    graph=patch.get('piano_graph',patch.get('graph',{}))
    normal_release=max(.02,float(graph.get('damper',{}).get('release_s',.20)))
    threshold=.5
    buf=np.zeros((n,2),dtype=np.float64)
    total_beats=float(n)/(float(sr)*float(beat_s))
    for ev in events or []:
        if ev.get('event_type')=='piano_control':
            continue
        if 'midi' not in ev:
            continue
        start_beat=float(ev.get('start_beat',0.0))
        key_duration=max(1e-9,float(ev.get('duration_beats',0.0)))
        key_off=start_beat+key_duration
        effective_off=key_off
        if resolve_sustain_pedal_position(events,key_off) >= threshold:
            release_beat=_next_sustain_pedal_release_beat(events,key_off,threshold)
            if release_beat is None:
                # No authored release: keep the strings undamped through the rendered
                # track, leaving room for the ordinary damper release at the tail.
                release_margin=normal_release/max(1e-12,float(beat_s))
                effective_off=max(key_off,max(start_beat,total_beats-release_margin))
            else:
                effective_off=max(key_off,float(release_beat))
        duration_s=max(1e-9,(effective_off-start_beat)*float(beat_s))
        perf=dict(ev.get('performance') or {})
        perf['pedal']=bool(_max_sustain_pedal_position(events,start_beat,effective_off)>=threshold)
        perf['pedal_controlled']=True
        stereo=render_piano_note(
            int(ev['midi']),duration_s,int(sr),patch,
            velocity=float(ev.get('velocity',.8)),performance=perf,
        )
        event_pan=float(ev.get('pan',0.0))
        if abs(event_pan)>1e-9:
            mono=.5*(stereo[:,0]+stereo[:,1])
            l,r=_equal_power(mono,event_pan)
            stereo=np.stack([l,r],axis=1)
        start=max(0,int(start_beat*float(beat_s)*int(sr)))
        end=min(len(buf),start+len(stereo))
        if end>start:
            buf[start:end]+=stereo[:end-start]
    return buf

def render_piano_note(midi:int,duration_s:float,sr:int,patch:dict,velocity:float=1.0,performance:dict|None=None):
    """Deterministic sample-free piano approximation.

    Models coupled strings with stretched partials, velocity-dependent hammer spectrum,
    register-dependent decay and keyboard stereo position, plus a low-level soundboard /
    sympathetic-resonance approximation. It is intentionally isolated from the generic
    oscillator synth path.
    """
    if isinstance(patch,dict) and 'piano_design' in patch:
        patch=resolve_piano_design(patch)
    if patch.get('piano_engine')=='electric' or 'electric_piano_graph' in patch:
        return render_electric_piano_note(
            midi,duration_s,sr,patch,velocity=velocity,performance=performance
        )
    graph=patch.get('piano_graph',patch.get('graph',{}))
    perf=performance or {}
    v=max(0.01,min(1.0,float(velocity)))
    pedal=bool(perf.get('pedal',graph.get('pedal',False)))
    pedal_controlled=bool(perf.get('pedal_controlled',False))

    damper=graph.get('damper',{})
    if pedal_controlled:
        # Explicit pedal state owns note sustain duration at track level.  Once that
        # state reaches pedal-up, use the ordinary damper release instead of attaching
        # another long per-note pedal tail.
        release_s=float(damper.get('release_s',0.20))
    else:
        release_s=float(damper.get('pedal_release_s',1.65) if pedal else damper.get('release_s',0.20))
    release_s=max(0.02,min(5.0,release_s*float(perf.get('release_scale',1.0))))
    total_s=max(0.01,float(duration_s))+release_s
    n=max(1,int(total_s*sr))
    t=np.arange(n,dtype=np.float64)/sr
    base_hz=midi_to_hz(midi)

    strings=graph.get('strings',{})
    partials=max(3,min(28,int(strings.get('max_partials',16))))
    if midi>=76: partials=max(5,int(partials*0.68))
    elif midi<=40: partials=min(28,int(partials*1.20))
    string_count=max(1,min(3,_string_count(midi,strings)))
    detune=float(strings.get('detune_cents',0.65))
    stereo_width=max(0.0,min(1.0,float(strings.get('stereo_width',0.72))))
    base_decay=max(0.15,float(strings.get('base_decay_s',3.2)))
    decay_keytrack=float(strings.get('decay_keytrack',0.55))
    partial_decay_power=max(0.0,float(strings.get('partial_decay_power',0.58)))
    rolloff=float(strings.get('spectral_rolloff',1.36))
    velocity_brightness=float(strings.get('velocity_brightness',0.72))
    rolloff=max(0.58,min(2.4,rolloff-velocity_brightness*(v-0.5)))
    inharm=float(strings.get('inharmonicity',0.00016))
    inharm*=1.0+0.7*abs((midi-60)/48.0)
    key_factor=2.0**(-(midi-60)/48.0*decay_keytrack)

    strike_cfg=graph.get('strike_identity',{}) if isinstance(graph.get('strike_identity',{}),dict) else {}
    strike_seed=perf.get('piano_strike_seed')
    strike_active=bool(strike_seed is not None and any(float(strike_cfg.get(k,0.0))>0 for k in (
        'phase_jitter_rad','unison_phase_jitter_rad','partial_phase_jitter_rad',
        'hammer_noise_mix','hammer_gain_variation','hammer_decay_variation'
    )))
    strike_rng=np.random.default_rng(int(strike_seed)&0xFFFFFFFF) if strike_active else None
    strike_global_phase=(float(strike_rng.uniform(-1.0,1.0))*float(strike_cfg.get('phase_jitter_rad',0.0)) if strike_rng is not None else 0.0)
    partial_phase_offsets=(
        strike_rng.uniform(-1.0,1.0,partials+1)*float(strike_cfg.get('partial_phase_jitter_rad',0.0))
        if strike_rng is not None else np.zeros(partials+1,dtype=np.float64)
    )
    unison_phase_offsets=(
        strike_rng.uniform(-1.0,1.0,string_count)*float(strike_cfg.get('unison_phase_jitter_rad',0.0))
        if strike_rng is not None else np.zeros(string_count,dtype=np.float64)
    )

    note_pan=_note_pan(midi,stereo_width)
    left=np.zeros(n,dtype=np.float64)
    right=np.zeros(n,dtype=np.float64)

    # Soft piano strings do not have a static sustain plateau: every partial decays.
    attack_s=max(0.0004,float(strings.get('attack_s',0.0018)))
    attack_env=1.0-np.exp(-t/attack_s)
    noteoff=np.ones(n,dtype=np.float64)
    off=int(max(0.0,float(duration_s))*sr)
    if off<n:
        rt=t[off:]-t[off]
        noteoff[off:]=np.exp(-rt/release_s)

    if string_count==1:
        spreads=[0.0]
    elif string_count==2:
        spreads=[-1.0,1.0]
    else:
        spreads=[-1.0,0.0,1.0]

    decoh=strings.get('unison_decoherence',{}) if isinstance(strings.get('unison_decoherence',{}),dict) else {}
    decoh_start=int(decoh.get('start_midi',61))
    decoh_active=string_count>=3 and midi>=decoh_start and any(float(decoh.get(name,0.0))>0.0 for name in (
        'partial_mistune_cents','inharmonicity_spread','decay_spread','level_spread'
    ))
    # Register weighting keeps the transition continuous instead of switching to an
    # unrelated treble instrument at one MIDI note.  It reaches full strength two
    # octaves above the authored start point.
    decoh_register=(min(1.0,max(0.0,(midi-decoh_start)/24.0)) if decoh_active else 0.0)

    for k in range(1,partials+1):
        stretch=math.sqrt(max(1e-9,1.0+inharm*(k*k)))
        fundamental=base_hz*k*stretch
        if fundamental>=sr*0.45:
            break
        amp=(1.0/(k**rolloff))
        # Low partials survive longer; upper partials die quickly like real strings.
        decay=base_decay*key_factor/(k**partial_decay_power)
        env=attack_env*np.exp(-t/max(0.02,decay))*noteoff
        for si,spread in enumerate(spreads):
            # S28-G: retain the physical 3-string unison and its mean detune, but
            # avoid making every partial of every string a perfectly coherent
            # fixed-offset oscillator.  Tiny deterministic asymmetries model the
            # fact that real unison strings do not share identical stiffness, decay,
            # excitation and partial mistuning.  The offsets are symmetric across
            # the outer strings, so center pitch / mean detune do not drift.
            pattern=math.sin(0.73*k + 0.11*midi)
            partial_mistune=float(decoh.get('partial_mistune_cents',0.0))*decoh_register*pattern
            cents=spread*(detune*(0.65+0.35*min(1.0,(midi-36)/48.0)) + partial_mistune)
            string_inharm=inharm*(1.0 + spread*float(decoh.get('inharmonicity_spread',0.0))*decoh_register*(0.55+0.45*pattern))
            string_stretch=math.sqrt(max(1e-9,1.0+string_inharm*(k*k)))
            string_fundamental=base_hz*k*string_stretch
            freq=string_fundamental*(2.0**(cents/1200.0))
            phase=0.19*midi + 0.37*k + 0.53*si + strike_global_phase + float(partial_phase_offsets[k]) + float(unison_phase_offsets[si])
            string_decay=decay*(1.0 + spread*float(decoh.get('decay_spread',0.0))*decoh_register*(0.70+0.30*pattern))
            string_level=1.0 + spread*float(decoh.get('level_spread',0.0))*decoh_register*(0.65-0.35*pattern)
            component_env=attack_env*np.exp(-t/max(0.02,string_decay))*noteoff if decoh_active else env
            if off<n and string_count>1:
                if pedal_controlled:
                    # S28-A R2: a pedal-up damper does not leave a coherent detuned
                    # unison beating under one shared 200 ms envelope, nor should it
                    # erase only the side strings.  Model felt contact on every string
                    # with a few milliseconds of deterministic contact spread and
                    # slightly different short damping constants.  All strings are
                    # damped; none is privileged, and pitch is never swept.
                    spread_s=max(0.0,min(.012,float(strings.get('pedal_damper_contact_spread_s',0.0045))))
                    base_tau=max(.035,min(.18,float(strings.get('pedal_damper_unison_decay_s',0.105))))
                    if string_count<=1:
                        order=[0]
                    elif midi % 2:
                        order=list(reversed(range(string_count)))
                    else:
                        order=list(range(string_count))
                    rank=order.index(si)
                    contact_delay=spread_s*(rank/max(1,string_count-1))
                    # Keep the variations bounded and symmetric around the nominal
                    # damping time so the result reads as felt contact, not a filter.
                    center=(string_count-1)/2.0
                    tau=base_tau*(1.0+0.10*(rank-center)/max(1.0,center))
                    extra=np.ones(n,dtype=np.float64)
                    contact=off+int(round(contact_delay*sr))
                    if contact<n:
                        extra[contact:]=np.exp(-(t[contact:]-t[contact])/tau)
                    component_env=env*extra
                else:
                    # Legacy/no-pedal S14 behavior remains byte-stable: collapse
                    # secondary detuned strings quickly after an ordinary key damper
                    # falls so a long exposed unison beating tail cannot emerge.
                    anchor=(string_count-1)//2
                    if si!=anchor:
                        tau=max(.015,float(strings.get('release_detune_damping_s',0.070)))
                        extra=np.ones(n,dtype=np.float64)
                        extra[off:]=np.exp(-(t[off:]-t[off])/tau)
                        component_env=env*extra
            sig=np.sin(2*np.pi*freq*t+phase)*component_env*amp*string_level/string_count
            pan=note_pan + spread*stereo_width*0.16
            l,r=_equal_power(sig,pan)
            left+=l; right+=r

    hammer=_hammer_layer(base_hz,n,sr,midi,v,graph.get('hammer',{}),strike_seed=strike_seed,strike_cfg=strike_cfg)
    hl,hr=_equal_power(hammer,note_pan*0.55)
    left+=hl; right+=hr

    resonance=_resonance_layer(base_hz,n,sr,midi,v,pedal,graph.get('resonance',{}),noteoff_env=noteoff)
    if np.any(resonance):
        # Resonance is broader than the struck string image.
        rl,rr=_equal_power(resonance,note_pan*0.35)
        left+=rl; right+=rr

    # Velocity is not a linear loudness multiplier: preserve soft-note body while
    # letting hammer brightness carry much of the performance difference.
    amp_scale=0.23+0.77*(v**0.82)
    left*=amp_scale
    right*=amp_scale

    # Very gentle body low-pass at soft velocity; hard strikes remain open.
    body=graph.get('body_filter',{})
    soft_cut=float(body.get('soft_cutoff_hz',3800.0))
    hard_cut=float(body.get('hard_cutoff_hz',14500.0))
    cutoff=soft_cut+(hard_cut-soft_cut)*(v**1.35)
    cutoff*=0.86+0.22*max(0.0,min(1.0,(midi-28)/68.0))
    left=_one_pole_lowpass(left,sr,cutoff)
    right=_one_pole_lowpass(right,sr,cutoff)

    # New-design acoustic pianos pass string energy through a bridge transfer stage.
    left=_bridge_transfer(left,sr,graph.get('bridge',{}))
    right=_bridge_transfer(right,sr,graph.get('bridge',{}))

    mechanics=_mechanical_layer(n,sr,midi,v,duration_s,graph.get('mechanics',{}))
    if np.any(mechanics):
        ml,mr=_equal_power(mechanics,note_pan*.22)
        left+=ml; right+=mr

    # Short fade-in/out prevents numerical edge clicks without erasing hammer attack.
    declick_ms=float(graph.get('declick_ms',0.35))
    m=min(n//2,max(1,int(declick_ms*0.001*sr)))
    ramp=_smoothstep01(np.linspace(0,1,m,endpoint=True))
    left[:m]*=ramp; right[:m]*=ramp
    left[-m:]*=ramp[::-1]; right[-m:]*=ramp[::-1]

    gain=float(graph.get('output_gain',0.62))
    stereo=np.stack([left*gain,right*gain],axis=1)
    peak=float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak>1.0:
        stereo/=peak
    return stereo


def piano_tail_seconds(patch:dict):
    if isinstance(patch,dict) and 'piano_design' in patch:
        patch=resolve_piano_design(patch)
    if patch.get('piano_engine')=='electric' or 'electric_piano_graph' in patch:
        return electric_piano_tail_seconds(patch)
    graph=patch.get('piano_graph',patch.get('graph',{}))
    damper=graph.get('damper',{})
    return max(float(damper.get('release_s',0.20)),float(damper.get('pedal_release_s',1.65)))


def apply_piano_soundboard(stereo,sr,patch,events=None,beat_s=1.0):
    """Low-level track-wide soundboard / sympathetic-coupling approximation.

    Unlike per-note resonance, this operates on the summed piano track so notes in a
    chord/phrase excite the same resonant body. Sustain-pedal events increase the wet
    coupling envelope without changing the authored note events.
    """
    if isinstance(patch,dict) and 'piano_design' in patch:
        patch=resolve_piano_design(patch)
    if patch.get('piano_engine')=='electric' or 'electric_piano_graph' in patch:
        return stereo
    graph=patch.get('piano_graph',patch.get('graph',{}))
    cfg=graph.get('soundboard',{})
    gain=float(cfg.get('gain',0.018))
    pedal_gain=float(cfg.get('pedal_gain',0.045))
    if gain<=0 and pedal_gain<=0:
        return stereo
    x=np.asarray(stereo,dtype=np.float64)
    if len(x)==0:
        return x
    taps=cfg.get('taps_ms',[11.7,17.9,29.3,41.1])
    weights=cfg.get('weights',[1.0,.66,.43,.28])
    cross=max(0.0,min(1.0,float(cfg.get('cross',0.32))))
    wet=np.zeros_like(x)
    norm=max(1.0,sum(abs(float(w)) for w in weights))
    for ms,w in zip(taps,weights):
        d=max(1,int(float(ms)*.001*sr))
        if d>=len(x):
            continue
        src=x[:-d]
        same=src*(1.0-cross)
        swap=src[:,::-1]*cross
        wet[d:]+=(same+swap)*(float(w)/norm)

    # S28-A: explicit track-level sustain-pedal curves supersede legacy note-local
    # pedal booleans for sympathetic coupling.  Legacy projects take the byte-stable
    # historical path below when no piano_control event is present.
    explicit_mask=_explicit_sustain_pedal_envelope(events,len(x),sr,beat_s)
    if explicit_mask is not None:
        mask=_causal_pedal_smooth(explicit_mask,sr,.012)
    else:
        mask=np.zeros(len(x),dtype=np.float64)
        pedal_release=float(graph.get('damper',{}).get('pedal_release_s',1.65))
        for ev in events or []:
            perf=ev.get('performance') or {}
            if not perf.get('pedal',False):
                continue
            start=max(0,int(float(ev.get('start_beat',0))*beat_s*sr))
            note_end=float(ev.get('start_beat',0))+float(ev.get('duration_beats',0))
            end=min(len(x),int((note_end*beat_s+pedal_release)*sr))
            if end>start:
                mask[start:end]=1.0
        if np.any(mask):
            # Preserve the historical smoothing exactly for note-local pedal projects.
            smooth=max(1,int(.025*sr))
            kernel=np.ones(smooth,dtype=np.float64)/smooth
            mask=np.convolve(mask,kernel,mode='same')

    # Damper-down body response must not behave like a bank of free-running synth
    # resonators.  Use a deliberately short modal state for the always-on body, then
    # add a separate long component only while authored sustain-pedal activity keeps
    # the strings undamped.  This prevents fixed soundboard modes from singing after
    # an ordinary no-pedal chord release.
    no_pedal_decay=max(.02,min(1.0,float(cfg.get('no_pedal_modal_decay_scale',0.10))))
    if explicit_mask is not None:
        # S28-A R2: after an authored pedal lift, fixed soundboard modes must not
        # continue as a free-running low-frequency resonator bank after the dampers
        # have already stopped the strings.  Keep the long pedal-coupled body while
        # the pedal is down, but use a much shorter structural body state underneath
        # explicit pedal control so release does not leave a pitched 'wah/meow' tail.
        no_pedal_decay=max(.02,min(no_pedal_decay,float(cfg.get('explicit_pedal_up_modal_decay_scale',0.035))))
    modal=_modal_soundboard(x,sr,cfg,decay_scale_multiplier=no_pedal_decay)
    if np.any(mask):
        pedal_modal=_modal_soundboard(x*mask[:,None],sr,cfg,decay_scale_multiplier=1.0)
        pedal_modal_scale=max(0.0,min(1.0,float(cfg.get('pedal_modal_scale',pedal_gain*6.0))))
        pedal_modal*=mask[:,None]*pedal_modal_scale
    else:
        pedal_modal=np.zeros_like(x)
    y=x+wet*(gain+pedal_gain*mask[:,None])+modal+pedal_modal
    peak=float(np.max(np.abs(y)))
    if peak>1.0:
        y/=peak
    return y


__all__=['render_piano_note','piano_tail_seconds','apply_piano_soundboard','render_piano_track_with_controls','resolve_sustain_pedal_position']
