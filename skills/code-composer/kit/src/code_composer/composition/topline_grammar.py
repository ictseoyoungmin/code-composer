from copy import deepcopy
from ..core.theory import NOTE_TO_PC, SCALES

def _shift_scale_steps(midi, tonal, steps):
    root_pc=NOTE_TO_PC[tonal["root"]]
    pcs={(root_pc+i)%12 for i in SCALES[tonal["scale"]]}
    direction=1 if steps>=0 else -1
    current=int(midi)
    for _ in range(abs(int(steps))):
        n=current+direction
        while n%12 not in pcs:
            n+=direction
        current=n
    return current

def apply_topline_grammar(events, section, tonal, beats_per_bar, cfg=None):
    cfg=cfg or {}
    if not cfg.get("enabled",False) or not events:
        return events

    phrase_bars=max(1,int(cfg.get("phrase_bars",2)))
    phrase_beats=phrase_bars*float(beats_per_bar)
    section_start=float(section["start_bar"])*float(beats_per_bar)
    section_end=section_start+float(section["bars"])*float(beats_per_bar)
    unit_count=max(1,int((section_end-section_start+phrase_beats-1e-9)//phrase_beats))
    breathing=float(cfg.get("breathing_beats",0.35))
    pickup=float(cfg.get("pickup_beats",0.25))
    response_steps=int(cfg.get("response_scale_steps",-1))
    tension_steps=int(cfg.get("tension_scale_steps",1))

    grouped={i:[] for i in range(unit_count)}
    for ev in sorted(events,key=lambda e:(e["start_beat"],e["midi"])):
        idx=min(unit_count-1,max(0,int((float(ev["start_beat"])-section_start)//phrase_beats)))
        grouped[idx].append(deepcopy(ev))

    out=[]
    for idx in range(unit_count):
        unit_start=section_start+idx*phrase_beats
        unit_end=min(section_end,unit_start+phrase_beats)
        is_response=(idx%2)==1
        is_last=idx==unit_count-1
        is_tension=unit_count>=3 and idx==unit_count-2

        if is_last and is_response:
            role="release_response"
        elif is_tension:
            role="tension_call" if not is_response else "tension_response"
        else:
            role="response" if is_response else "call"

        unit=[]
        for j,ev in enumerate(grouped[idx]):
            x=deepcopy(ev)
            # Explicit phrase breathing except final cadence material.
            in_breath=float(x["start_beat"]) >= unit_end-breathing
            cadence=x.get("phrase_phase")=="cadence"
            if in_breath and not (is_last and cadence):
                continue

            x["topline_phrase_index"]=idx
            x["topline_phrase_role"]=role
            x["topline_hook_anchor"]=(j==0 and not is_response)

            # Call preserves motif. Response gets a restrained scale-safe answer.
            if is_response and not is_last and j%3==2:
                x["midi"]=_shift_scale_steps(x["midi"],tonal,response_steps)
                x["topline_variation"]="response_step"
            elif is_tension and j%3==1:
                x["midi"]=_shift_scale_steps(x["midi"],tonal,tension_steps)
                x["velocity"]=min(1.0,float(x.get("velocity",0.6))*1.06)
                x["topline_variation"]="tension_lift"

            if is_response:
                x["velocity"]=float(x.get("velocity",0.6))*float(cfg.get("response_velocity",0.96))
            else:
                x["velocity"]=float(x.get("velocity",0.6))*float(cfg.get("call_velocity",1.02))

            # Slightly shorter calls, more connected responses.
            gate=float(cfg.get("response_gate",1.02) if is_response else cfg.get("call_gate",0.92))
            x["duration_beats"]=round(float(x["duration_beats"])*gate,6)
            unit.append(x)

        # Add a quiet pickup into response phrases.
        if is_response and unit and pickup>0:
            first=min(unit,key=lambda e:e["start_beat"])
            pickup_start=unit_start-pickup
            if pickup_start>=section_start:
                p=deepcopy(first)
                p["start_beat"]=round(pickup_start,6)
                p["duration_beats"]=round(min(pickup*0.72,float(first["duration_beats"])*0.55),6)
                p["velocity"]=float(first.get("velocity",0.5))*float(cfg.get("pickup_velocity",0.42))
                p["topline_phrase_index"]=idx
                p["topline_phrase_role"]="pickup"
                p["topline_pickup"]=True
                p["topline_hook_anchor"]=False
                unit.append(p)

        out.extend(unit)

    return sorted(out,key=lambda e:(float(e["start_beat"]),int(e["midi"])))
