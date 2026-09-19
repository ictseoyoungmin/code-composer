from collections import defaultdict

def analyze_rhythm(resolved_ir):
    drums=next((t for t in resolved_ir["tracks"] if t["id"]=="drums"),None)
    bass=next((t for t in resolved_ir["tracks"] if t["id"]=="bass"),None)
    if not drums:
        return {}

    report=defaultdict(lambda:{
        "kick":0,"snare":0,"hat":0,"fills":0,"events":0,
        "velocity_sum":0.0
    })

    for ev in drums["events"]:
        s=ev["section_id"]
        role=ev["drum"]
        report[s][role]+=1
        report[s]["events"]+=1
        report[s]["velocity_sum"]+=ev["velocity"]
        if ev.get("rhythm_origin")=="fill":
            report[s]["fills"]+=1

    for s,r in report.items():
        r["mean_velocity"]=r["velocity_sum"]/max(1,r["events"])
        del r["velocity_sum"]

    # Bass/kick coupling: bass onset near kick onset within 0.08 beat
    coupling={}
    if bass:
        for s in report:
            kicks=[e["start_beat"] for e in drums["events"]
                   if e["section_id"]==s and e["drum"]=="kick"]
            basses=[e["start_beat"] for e in bass["events"]
                    if e["section_id"]==s]
            if not basses:
                coupling[s]=0.0
                continue
            matches=0
            for b in basses:
                if any(abs(b-k)<=0.08 for k in kicks):
                    matches+=1
            coupling[s]=matches/len(basses)
    return {"sections":dict(report),"bass_kick_coupling":coupling}

def rhythmic_contrast(report):
    sections=report.get("sections",{})
    order=[s for s in ("intro","build","main","break","final") if s in sections]
    if len(order)<2:
        return 0.0
    vals=[sections[s]["events"] for s in order]
    diffs=[abs(a-b)/max(1,a+b) for a,b in zip(vals,vals[1:])]
    return sum(diffs)/len(diffs)
