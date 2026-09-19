from collections import Counter,defaultdict

def analyze_orchestration(resolved_ir):
    form=resolved_ir.get("form",[])
    events_by_section=defaultdict(lambda:Counter())
    track_present={t.get("id"):len(t.get("events",[])) for t in resolved_ir.get("tracks",[])}

    for t in resolved_ir.get("tracks",[]):
        tid=t.get("id")
        for e in t.get("events",[]):
            events_by_section[e.get("section_id","unknown")][tid]+=1

    sections=[]
    zero_foreground=0
    for sec in form:
        sid=sec["id"]
        c=events_by_section[sid]
        lead=c.get("lead",0)
        topline=c.get("topline",0)
        if lead==0 and topline==0:
            zero_foreground+=1
        sections.append({
            "section_id":sid,
            "lead_events":lead,
            "topline_events":topline,
            "foreground_events":lead+topline,
            "pad_events":c.get("pad",0),
            "bass_events":c.get("bass",0),
            "drum_events":c.get("drums",0),
            "arp_events":c.get("arp",0),
        })

    return {
        "track_event_counts":track_present,
        "sections":sections,
        "sections_without_foreground":zero_foreground,
        "sections_with_foreground":len(form)-zero_foreground,
    }

__all__=["analyze_orchestration"]
