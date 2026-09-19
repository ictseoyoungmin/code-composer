from collections import defaultdict

def _intervals(events):
    return [
        (float(e["start_beat"]), float(e["start_beat"])+float(e["duration_beats"]))
        for e in events
    ]

def _overlap(a, b):
    return max(0.0, min(a[1],b[1]) - max(a[0],b[0]))

def analyze_topline_space(resolved_ir):
    topline = next((t for t in resolved_ir["tracks"] if t["id"]=="topline"), None)
    lead = next((t for t in resolved_ir["tracks"] if t["id"]=="lead"), None)
    if not topline:
        return {"present":False,"sections":{}}

    by_top=defaultdict(list)
    by_lead=defaultdict(list)
    for e in topline.get("events",[]):
        by_top[e.get("section_id","unknown")].append(e)
    if lead:
        for e in lead.get("events",[]):
            by_lead[e.get("section_id","unknown")].append(e)

    sections={}
    for sid, events in by_top.items():
        top_i=_intervals(events)
        lead_i=_intervals(by_lead.get(sid,[]))
        top_dur=sum(b-a for a,b in top_i)
        overlap=sum(_overlap(a,b) for a in top_i for b in lead_i)
        sections[sid]={
            "topline_event_count":len(events),
            "topline_duration_beats":top_dur,
            "lead_event_count":len(by_lead.get(sid,[])),
            "lead_overlap_beats":overlap,
            "lead_overlap_ratio": overlap/max(top_dur,1e-9),
        }

    return {"present":True,"sections":sections}

def topline_space_score(report):
    if not report.get("present"):
        return 0.0
    vals=[]
    for sec in report["sections"].values():
        # 1.0 means no instrumental-lead collision with topline.
        vals.append(max(0.0,1.0-sec["lead_overlap_ratio"]))
    return sum(vals)/max(1,len(vals))
