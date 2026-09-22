from collections import Counter
from statistics import mean
from ..core.theory import voice_leading_cost

def analyze_harmony(resolved_ir):
    pad=next((t for t in resolved_ir.get("tracks",[]) if t.get("id")=="pad"),None)
    if not pad: return {"present":False}
    groups={}
    for e in pad.get("events",[]):
        if e.get("transition_material") or "midi" not in e:
            continue
        key=(e.get("section_id"),float(e["start_beat"]),e.get("harmonic_chord_id",f"{e.get('section_id')}:{e['start_beat']}"))
        groups.setdefault(key,[]).append(e)
    ordered=sorted(groups.items(),key=lambda kv:(float(kv[0][1]),str(kv[0][0])))
    colors=Counter()
    passing=0
    spans=[]
    movements=[]
    by_section={}
    previous=None
    for (sid,start,cid),events in ordered:
        notes=sorted(int(e["midi"]) for e in events)
        color=events[0].get("harmonic_color","unannotated")
        colors[color]+=1
        is_passing=bool(events[0].get("harmonic_passing",False))
        passing+=int(is_passing)
        if notes: spans.append(max(notes)-min(notes))
        if previous is not None: movements.append(voice_leading_cost(previous,notes))
        previous=notes
        sec=by_section.setdefault(sid,{"chords":0,"colors":Counter(),"passing":0,"progressions":Counter(),"degree_path":[]})
        sec["chords"]+=1; sec["colors"][color]+=1; sec["passing"]+=int(is_passing)
        progression_id=events[0].get("harmonic_progression_id")
        if progression_id is not None:
            sec["progressions"][progression_id]+=1
        if not is_passing and events[0].get("harmonic_degree") is not None:
            sec["degree_path"].append(int(events[0]["harmonic_degree"]))
    result={
        "present":True,
        "chord_count":len(ordered),
        "color_counts":dict(colors),
        "unique_colors":len(colors),
        "passing_chords":passing,
        "mean_voice_leading_cost":mean(movements) if movements else 0.0,
        "max_voice_leading_cost":max(movements) if movements else 0.0,
        "mean_chord_span":mean(spans) if spans else 0.0,
        "sections":{sid:{"chords":v["chords"],"colors":dict(v["colors"]),"passing":v["passing"]} for sid,v in by_section.items()},
    }
    lineage={
        sid:{"progression_ids":dict(v["progressions"]),"degree_path":list(v["degree_path"])}
        for sid,v in by_section.items() if v["progressions"]
    }
    if lineage:
        result["progression_lineage"]=lineage
    return result
