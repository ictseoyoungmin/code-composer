from collections import defaultdict
from statistics import mean

def analyze_arrangement(resolved_ir):
    by_section=defaultdict(lambda: defaultdict(list))
    for track in resolved_ir["tracks"]:
        role=track["id"]
        for ev in track.get("events",[]):
            sid=ev.get("section_id","unknown")
            by_section[sid][role].append(ev)

    report={}
    for sid, roles in by_section.items():
        lead=roles.get("lead",[])
        all_events=[e for events in roles.values() for e in events]
        report[sid]={
            "roles_present":sorted([r for r,events in roles.items() if events]),
            "event_count":len(all_events),
            "lead_event_count":len(lead),
            "lead_mean_pitch":mean([e["midi"] for e in lead]) if lead else None,
            "lead_pitch_range":(max(e["midi"] for e in lead)-min(e["midi"] for e in lead)) if lead else 0,
            "mean_velocity":mean([e["velocity"] for e in all_events]) if all_events else 0.0,
        }
    return report

def section_contrast_score(report):
    sections=[s for s in ("intro","build","main","break","final") if s in report]
    if len(sections)<2:
        return 0.0
    vectors=[]
    for s in sections:
        r=report[s]
        vectors.append((
            r["event_count"],
            r["lead_mean_pitch"] or 0,
            len(r["roles_present"]),
            r["mean_velocity"],
        ))
    diffs=[]
    for a,b in zip(vectors,vectors[1:]):
        d=(abs(a[0]-b[0])/max(1,a[0]+b[0])
           + abs(a[1]-b[1])/24
           + abs(a[2]-b[2])/4
           + abs(a[3]-b[3]))
        diffs.append(d)
    return sum(diffs)/len(diffs)
