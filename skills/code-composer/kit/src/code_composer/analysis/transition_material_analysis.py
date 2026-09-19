from collections import Counter,defaultdict

def analyze_transition_material(resolved_ir):
    types=Counter(); sections=defaultdict(Counter); tracks=defaultdict(Counter)
    for tr in resolved_ir.get("tracks",[]):
        for ev in tr.get("events",[]):
            kind=ev.get("transition_material")
            if not kind: continue
            types[kind]+=1
            sections[ev.get("section_id","unknown")][kind]+=1
            tracks[tr.get("id","unknown")][kind]+=1
    return {
        "total_events":sum(types.values()),
        "by_type":dict(types),
        "by_section":{k:dict(v) for k,v in sections.items()},
        "by_track":{k:dict(v) for k,v in tracks.items()},
    }
