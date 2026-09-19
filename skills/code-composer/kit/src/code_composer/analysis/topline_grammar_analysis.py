from collections import Counter,defaultdict
from statistics import mean

def _contour(events):
    pitches=[e["midi"] for e in sorted(events,key=lambda x:x["start_beat"])]
    return [1 if b>a else -1 if b<a else 0 for a,b in zip(pitches,pitches[1:])]

def _contour_similarity(a,b):
    n=min(len(a),len(b))
    if n==0: return 0.0
    return sum(1 for x,y in zip(a[:n],b[:n]) if x==y)/n

def analyze_topline_grammar(resolved_ir):
    top=next((t for t in resolved_ir["tracks"] if t["id"]=="topline"),None)
    if not top:
        return {"present":False}
    ev=top.get("events",[])
    roles=Counter(e.get("topline_phrase_role","plain") for e in ev)
    pickups=sum(1 for e in ev if e.get("topline_pickup"))
    anchors=sum(1 for e in ev if e.get("topline_hook_anchor"))
    variations=Counter(e.get("topline_variation") for e in ev if e.get("topline_variation"))

    grouped=defaultdict(lambda:defaultdict(list))
    for e in ev:
        grouped[e.get("section_id","unknown")][e.get("topline_phrase_index",-1)].append(e)

    pair_scores=[]
    breathing_gaps=[]
    cadence_endings=[]
    for sid,units in grouped.items():
        ids=sorted(i for i in units if i>=0)
        for a,b in zip(ids[0::2],ids[1::2]):
            ca=_contour([e for e in units[a] if not e.get("topline_pickup")])
            cb=_contour([e for e in units[b] if not e.get("topline_pickup")])
            pair_scores.append(_contour_similarity(ca,cb))
        for i in ids[:-1]:
            cur=max(float(e["start_beat"])+float(e["duration_beats"]) for e in units[i])
            nxt=min(float(e["start_beat"]) for e in units[i+1] if not e.get("topline_pickup"))
            breathing_gaps.append(max(0.0,nxt-cur))
        last=units[ids[-1]] if ids else []
        if len(last)>=2:
            notes=[e["midi"] for e in sorted(last,key=lambda x:x["start_beat"]) if not e.get("topline_pickup")]
            if len(notes)>=2: cadence_endings.append(notes[-2:])

    return {
        "present":True,
        "event_count":len(ev),
        "role_counts":dict(roles),
        "pickup_count":pickups,
        "hook_anchor_count":anchors,
        "variation_counts":dict(variations),
        "mean_call_response_contour_similarity":mean(pair_scores) if pair_scores else 0.0,
        "mean_phrase_gap_beats":mean(breathing_gaps) if breathing_gaps else 0.0,
        "cadence_endings":cadence_endings,
        "unique_cadence_endings":len({tuple(x) for x in cadence_endings}),
    }
