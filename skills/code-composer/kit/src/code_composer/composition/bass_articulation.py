from copy import deepcopy

def articulate_bass(events, beats_per_bar, cfg=None):
    cfg=cfg or {}
    if not cfg.get("enabled",False):
        return events
    out=[]
    base_duration=float(cfg.get("base_duration_beats",0.58))
    for i,e in enumerate(sorted(events,key=lambda x:x["start_beat"])):
        x=deepcopy(e)
        beat=float(x["start_beat"])
        local=beat % beats_per_bar
        coupled=bool(x.get("rhythm_coupled",False))
        perf={}
        # Downbeat = accented anchor.
        if local < 0.08:
            art="accent"
            x["velocity"]*=float(cfg.get("accent_velocity",1.10))
            x["duration_beats"]=base_duration*float(cfg.get("accent_gate",0.92))
            perf={"attack_scale":0.72,"release_scale":0.86}
        # Offbeat coupled notes = shorter punch.
        elif coupled and (abs(local-round(local)) > 0.12 or int(round(local)) % 2 == 1):
            art="short"
            x["duration_beats"]=base_duration*float(cfg.get("short_gate",0.58))
            perf={"attack_scale":0.82,"release_scale":0.55}
        else:
            art="legato"
            x["duration_beats"]=base_duration*float(cfg.get("legato_gate",1.12))
            perf={"attack_scale":1.0,"release_scale":1.18}

        x["bass_articulation"]=art
        x["performance"]=perf
        out.append(x)

        # Sparse deterministic ghost after selected anchors.
        if cfg.get("ghost_notes",True) and art=="accent" and i % 2 == 0:
            g=deepcopy(x)
            g["start_beat"]=round(beat+float(cfg.get("ghost_offset_beats",0.75)),6)
            g["duration_beats"]=base_duration*float(cfg.get("ghost_gate",0.38))
            g["velocity"]*=float(cfg.get("ghost_velocity",0.34))
            g["bass_articulation"]="ghost"
            g["performance"]={"attack_scale":0.9,"release_scale":0.42}
            g["rhythm_coupled"]=False
            out.append(g)

    # Slide-like approach into a new bar/chord: quiet note just before next downbeat.
    if cfg.get("approach_notes",True):
        anchors=[e for e in out if e.get("bass_articulation")=="accent"]
        for j,a in enumerate(anchors[1:]):
            beat=float(a["start_beat"])
            p=deepcopy(a)
            p["start_beat"]=round(beat-float(cfg.get("approach_offset_beats",0.25)),6)
            p["duration_beats"]=float(cfg.get("approach_duration_beats",0.20))
            p["velocity"]*=float(cfg.get("approach_velocity",0.42))
            p["midi"]=int(a["midi"])-2
            p["bass_articulation"]="approach"
            p["performance"]={
                "pitch_start_cents":0.0,
                "pitch_end_cents":200.0,
                "pitch_time_s":float(cfg.get("approach_pitch_time_s",0.10)),
                "attack_scale":0.78,
                "release_scale":0.50,
            }
            p["rhythm_coupled"]=False
            out.append(p)

    return sorted(out,key=lambda e:(e["start_beat"],e["midi"]))
