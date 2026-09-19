from collections import Counter
def analyze_bass_articulation(resolved_ir):
    tr=next((t for t in resolved_ir["tracks"] if t["id"]=="bass"),None)
    if not tr: return {"present":False}
    c=Counter(e.get("bass_articulation","plain") for e in tr.get("events",[]))
    ev=tr.get("events",[])
    return {
        "present":True,
        "event_count":len(ev),
        "articulation_counts":dict(c),
        "velocity_min":min((e.get("velocity",0) for e in ev),default=0),
        "velocity_max":max((e.get("velocity",0) for e in ev),default=0),
        "duration_min":min((e.get("duration_beats",0) for e in ev),default=0),
        "duration_max":max((e.get("duration_beats",0) for e in ev),default=0),
    }
