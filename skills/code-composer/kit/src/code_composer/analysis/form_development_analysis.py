from collections import defaultdict
from statistics import mean

def _mean_midi(events):
    xs=[e["midi"] for e in events if "midi" in e]
    return mean(xs) if xs else None

def analyze_form_development(resolved_ir):
    by_section=defaultdict(lambda:defaultdict(list))
    for track in resolved_ir.get("tracks",[]):
        tid=track.get("id")
        for ev in track.get("events",[]):
            by_section[ev.get("section_id","unknown")][tid].append(ev)

    cfg=resolved_ir.get("arrangement_development",{})
    sections_cfg=cfg.get("sections",{})
    rows=[]
    for sec in resolved_ir.get("form",[]):
        sid=sec["id"]
        t=by_section[sid]
        lead=t.get("lead",[])
        top=t.get("topline",[])
        drums=t.get("drums",[])
        pad=t.get("pad",[])
        bass=t.get("bass",[])
        rows.append({
            "section_id":sid,
            "stage":sections_cfg.get(sid,{}).get("stage","legacy"),
            "lead_events":len(lead),
            "topline_events":len(top),
            "foreground_events":len(lead)+len(top),
            "drum_events":len(drums),
            "pad_events":len(pad),
            "bass_events":len(bass),
            "lead_mean_midi":_mean_midi(lead),
            "topline_mean_midi":_mean_midi(top),
            "total_events":sum(len(v) for v in t.values()),
        })

    families={}
    for family,ids in cfg.get("families",{}).items():
        seq=[next((r for r in rows if r["section_id"]==sid),None) for sid in ids]
        seq=[r for r in seq if r is not None]
        if not seq:
            continue
        signatures=[
            (r["foreground_events"],r["drum_events"],r["pad_events"],r["bass_events"],
             None if r["lead_mean_midi"] is None else round(r["lead_mean_midi"],2))
            for r in seq
        ]
        families[family]={
            "sections":[r["section_id"] for r in seq],
            "stages":[r["stage"] for r in seq],
            "distinct_signatures":len(set(signatures)),
            "foreground_delta":seq[-1]["foreground_events"]-seq[0]["foreground_events"],
            "drum_delta":seq[-1]["drum_events"]-seq[0]["drum_events"],
            "lead_register_delta":(
                None if seq[0]["lead_mean_midi"] is None or seq[-1]["lead_mean_midi"] is None
                else seq[-1]["lead_mean_midi"]-seq[0]["lead_mean_midi"]
            ),
        }

    return {"sections":rows,"families":families}

__all__=["analyze_form_development"]
