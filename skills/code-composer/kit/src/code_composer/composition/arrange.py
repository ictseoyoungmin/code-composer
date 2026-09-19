from copy import deepcopy

from .phrase import PhraseConfig, compose_phrase
from .rhythm import GrooveConfig, generate_rhythm_events, coupled_bass_pattern
from .bass_articulation import articulate_bass
from .topline import resolve_topline
from .harmonic_grammar import color_chord, voice_color_chord, section_harmonic_profile, color_for_slot, passing_spec
from ..core.theory import scale_degree_to_midi, triad_from_degree, nearest_inversion
from ..core.constraints import enforce_forbidden_track_events

from .profiles import DEFAULT_PROFILES, profile_for
from .orchestration import effective_section_profile
from .development import section_development

def _profile(ir, section_id):
    base=profile_for(ir, section_id)
    effective,_=effective_section_profile(ir,section_id,base)
    developed,_=section_development(ir,section_id,effective)
    return developed

def _filter_and_offset(events, start_beat, duration_beats, keep_ratio=1.0, register_shift=0):
    out=[]
    for i, ev in enumerate(events):
        if ev["start_beat"] >= duration_beats:
            continue
        if keep_ratio < 1.0:
            # deterministic thinning by index; preserve phrase boundaries/endpoints more often
            stride = max(1, round(1.0 / max(0.05, keep_ratio)))
            if i % stride != 0 and ev.get("phrase_phase") not in ("cadence",):
                continue
        x=dict(ev)
        x["start_beat"]=round(start_beat + ev["start_beat"], 6)
        x["midi"]=int(ev["midi"] + register_shift)
        out.append(x)
    return out

def _chord_events(ir, section, profile, source):
    root=ir["tonal"]["root"]
    scale=ir["tonal"]["scale"]
    beats_per_bar=ir["transport"]["beats_per_bar"]
    start_beat=section["start_bar"]*beats_per_bar
    total_beats=section["bars"]*beats_per_bar
    prog=ir["materials"]["progressions"][source["progression"]]
    chord_beats=float(source.get("chord_beats", beats_per_bar))
    cursor=0.0
    idx=section["start_bar"] % len(prog["degrees"])
    previous=None
    events=[]

    grammar_enabled=bool(ir.get("harmonic_grammar",{}).get("enabled",False))
    hprofile=section_harmonic_profile(ir,section["id"]) if grammar_enabled else {}
    slot_count=max(1,int(round(total_beats/chord_beats)))
    slot_index=0

    while cursor < total_beats - 1e-9:
        degree=prog["degrees"][idx % len(prog["degrees"])]
        if not grammar_enabled:
            chord=triad_from_degree(root, scale, degree, int(source.get("octave",3)),
                                    seventh=bool(source.get("seventh",True)))
            voiced=nearest_inversion(chord, int(source.get("voice_center",58)))
            if previous is not None:
                candidates=[[n-12 for n in voiced], voiced, [n+12 for n in voiced]]
                voiced=min(candidates, key=lambda c: sum(abs(a-b) for a,b in zip(sorted(previous),sorted(c))))
            color="seventh" if source.get("seventh",True) else "triad"
            velocity_scale=1.0
        else:
            color=color_for_slot(hprofile,slot_index,slot_count)
            chord=color_chord(root,scale,degree,int(source.get("octave",3)),color)
            center=int(source.get("voice_center",58))+int(hprofile.get("voice_center_offset",0))
            voiced=voice_color_chord(
                chord,previous,center,
                motion_weight=float(hprofile.get("motion_weight",1.0)),
                center_weight=float(hprofile.get("center_weight",0.22)),
            )
            base_count=4 if source.get("seventh",True) else 3
            velocity_scale=(base_count/max(1,len(voiced)))**0.5 if hprofile.get("normalize_density",True) else 1.0

        chord_id=f"{section['id']}:{slot_index}:main"
        for note in voiced:
            events.append({
                "start_beat": round(start_beat+cursor,6),
                "duration_beats": chord_beats*float(source.get("gate",0.92)),
                "midi": int(note + profile.get("register_shift",0)//2),
                "velocity": float(source.get("velocity",0.55))*profile["energy"]*profile["pad_gain"]*velocity_scale,
                "section_id": section["id"],
                "arrangement_role": "pad",
                "harmonic_color": color,
                "harmonic_degree": int(degree),
                "harmonic_slot": slot_index,
                "harmonic_chord_id": chord_id,
                "harmonic_passing": False,
            })
        previous=voiced

        if grammar_enabled:
            ps=passing_spec(hprofile,slot_index,slot_count)
            if ps is not None:
                pbeats=min(chord_beats*0.5,max(0.125,float(ps["beats"])))
                pdegree=max(1,int(degree)+int(ps["degree_offset"]))
                pcolor=ps["color"]
                pchord=color_chord(root,scale,pdegree,int(source.get("octave",3)),pcolor)
                center=int(source.get("voice_center",58))+int(hprofile.get("voice_center_offset",0))
                pvoiced=voice_color_chord(pchord,previous,center)
                pstart=start_beat+cursor+chord_beats-pbeats
                # Shorten only the final main slot enough to create space for the passing chord.
                for e in events:
                    if e.get("harmonic_chord_id")==chord_id:
                        e["duration_beats"]=max(0.1,chord_beats-pbeats*0.85)
                pid=f"{section['id']}:{slot_index}:passing"
                base_count=4 if source.get("seventh",True) else 3
                pscale=(base_count/max(1,len(pvoiced)))**0.5 if hprofile.get("normalize_density",True) else 1.0
                for note in pvoiced:
                    events.append({
                        "start_beat":round(pstart,6),
                        "duration_beats":pbeats*0.78,
                        "midi":int(note + profile.get("register_shift",0)//2),
                        "velocity":float(source.get("velocity",0.55))*profile["energy"]*profile["pad_gain"]*float(ps["velocity_scale"])*pscale,
                        "section_id":section["id"],
                        "arrangement_role":"pad",
                        "harmonic_color":pcolor,
                        "harmonic_degree":int(pdegree),
                        "harmonic_slot":slot_index,
                        "harmonic_chord_id":pid,
                        "harmonic_passing":True,
                    })
                previous=pvoiced

        cursor+=chord_beats
        idx+=1
        slot_index+=1
    return events

def _bass_events(ir, section, profile, source, coupled_offsets=None):
    if not profile.get("bass", True):
        return []
    root=ir["tonal"]["root"]
    scale=ir["tonal"]["scale"]
    beats_per_bar=ir["transport"]["beats_per_bar"]
    prog=ir["materials"]["progressions"][source["progression"]]
    events=[]
    for local_bar in range(section["bars"]):
        global_bar=section["start_bar"]+local_bar
        degree=prog["degrees"][global_bar % len(prog["degrees"])]
        midi=scale_degree_to_midi(root, scale, degree, int(source.get("octave",2)))
        pattern = None
        if coupled_offsets and global_bar in coupled_offsets:
            pattern = coupled_offsets[global_bar]
        if not pattern:
            pattern=source.get("pattern",[0.0,2.0])
        for off in pattern:
            events.append({
                "start_beat": round(global_bar*beats_per_bar+float(off),6),
                "duration_beats": float(source.get("duration_beats",0.58)),
                "midi": int(midi),
                "velocity": float(source.get("velocity",0.72))*profile["energy"],
                "section_id": section["id"],
                "arrangement_role": "bass",
                "rhythm_coupled": bool(coupled_offsets and global_bar in coupled_offsets),
            })
    return events

def _arp_events(ir, section, profile, source):
    if not profile.get("arp", False):
        return []
    root=ir["tonal"]["root"]
    scale=ir["tonal"]["scale"]
    beats_per_bar=ir["transport"]["beats_per_bar"]
    prog=ir["materials"]["progressions"][source["progression"]]
    events=[]
    step=float(source.get("step_beats",0.5))
    pattern=source.get("degree_offsets",[0,2,4,2,6,4,2,0])
    for local_bar in range(section["bars"]):
        global_bar=section["start_bar"]+local_bar
        degree=prog["degrees"][global_bar % len(prog["degrees"])]
        local=0.0
        i=0
        while local < beats_per_bar - 1e-9:
            deg=degree + pattern[i % len(pattern)]
            midi=scale_degree_to_midi(root,scale,max(1,deg),int(source.get("octave",4)))
            events.append({
                "start_beat": round(global_bar*beats_per_bar+local,6),
                "duration_beats": step*float(source.get("gate",0.55)),
                "midi": int(midi),
                "velocity": float(source.get("velocity",0.36))*profile["energy"],
                "section_id": section["id"],
                "arrangement_role": "arp",
            })
            local += step
            i += 1
    return events


def _apply_section_entry_shaping(events, ir):
    """
    Scale event velocities near a section entrance using arrangement profile state.

    profile fields:
      entry_gain: multiplier at the exact boundary (default 1.0)
      entry_soften_beats: linear ramp duration in beats (default 0)
    """
    beats_per_bar = ir["transport"]["beats_per_bar"]
    section_map = {s["id"]: s for s in ir["form"]}
    out = []
    for ev in events:
        x = dict(ev)
        sid = x.get("section_id")
        if sid in section_map:
            profile = _profile(ir, sid)
            section_gain = float(profile.get("section_gain", 1.0))
            if "velocity" in x and abs(section_gain-1.0) > 1e-12:
                x["velocity"] = float(x["velocity"]) * section_gain
                x["section_gain_applied"] = section_gain
            entry_gain = float(profile.get("entry_gain", 1.0))
            soften = float(profile.get("entry_soften_beats", 0.0))
            if soften > 0 and entry_gain < 1.0:
                section_start = section_map[sid]["start_bar"] * beats_per_bar
                local = max(0.0, float(x["start_beat"]) - section_start)
                if local < soften:
                    u = local / soften
                    gain = entry_gain + (1.0-entry_gain)*u
                    if "velocity" in x:
                        x["velocity"] = float(x["velocity"]) * gain
                    x["entry_shaped"] = True
                    x["entry_gain_applied"] = gain
        out.append(x)
    return out


def _reserve_topline_space(resolved_tracks, ir):
    """
    Remove instrumental-lead events that collide with active topline phrases.

    This is arrangement logic, not mixing. The topline lane reserves temporal
    space so a future vocal/topline is not forced to compete with an instrumental hook.
    """
    top = next((t for t in resolved_tracks if t.get("id")=="topline"), None)
    lead = next((t for t in resolved_tracks if t.get("id")=="lead"), None)
    if not top or not lead:
        return resolved_tracks

    top_by_section = {}
    for e in top.get("events", []):
        sid = e.get("section_id")
        top_by_section.setdefault(sid, []).append(
            (float(e["start_beat"]), float(e["start_beat"])+float(e["duration_beats"]))
        )

    kept = []
    for e in lead.get("events", []):
        sid = e.get("section_id")
        profile = _profile(ir, sid) if sid else {}
        if not profile.get("topline_active", False):
            kept.append(e)
            continue

        exclusion = float(profile.get("topline_lead_exclusion_beats", 0.08))
        a0 = float(e["start_beat"])
        a1 = a0 + float(e["duration_beats"])
        collision = False
        for b0, b1 in top_by_section.get(sid, []):
            # Pad the protected topline window slightly on both sides.
            b0 -= exclusion
            b1 += exclusion
            if min(a1, b1) - max(a0, b0) > 0:
                collision = True
                break
        if not collision:
            kept.append(e)

    lead["events"] = kept
    return resolved_tracks

def arrange_ir(ir: dict) -> dict:
    out=deepcopy(ir)
    beats_per_bar=ir["transport"]["beats_per_bar"]
    seed=ir["meta"]["global_seed"]
    roles=ir.get("arrangement",{}).get("roles",{})
    motif_id=ir.get("arrangement",{}).get("motif","main")

    resolved_tracks=[]

    rhythm_result = None
    coupled_maps = {}
    if ir.get("rhythm_engine"):
        rcfg = ir["rhythm_engine"]
        groove_cfg = GrooveConfig(
            steps_per_bar=int(rcfg.get("steps_per_bar",16)),
            swing=float(rcfg.get("swing",0.08)),
            humanize_beats=float(rcfg.get("humanize_beats",0.008)),
            velocity_jitter=float(rcfg.get("velocity_jitter",0.035)),
            fill_probability=float(rcfg.get("fill_probability",0.65)),
            bass_coupling=float(rcfg.get("bass_coupling",0.75)),
        )
        rhythm_result = generate_rhythm_events(ir, groove_cfg)
        for sec in ir["form"]:
            coupled_maps[sec["id"]] = coupled_bass_pattern(
                rhythm_result["events"], sec["id"], beats_per_bar, groove_cfg.bass_coupling
            )

    # LEAD: one phrase interpretation per section, same motif identity.
    if "lead" in roles:
        role=roles["lead"]
        events=[]
        section_meta=[]
        for section in ir["form"]:
            p=_profile(ir,section["id"])
            if not p.get("lead_active", True):
                section_meta.append({
                    "section_id": section["id"],
                    "event_count": 0,
                    "profile": p,
                    "transform_log": [],
                })
                continue
            effective_lead_density = float(p["lead_density"])
            if p.get("topline_active", False):
                effective_lead_density *= float(p.get("lead_under_topline", 0.48))
            cfg=PhraseConfig(
                bars=section["bars"],
                beats_per_bar=beats_per_bar,
                base_degree=int(role.get("base_degree",1)),
                octave=int(p.get("lead_octave",role.get("octave",4))),
                density=effective_lead_density,
                tension=float(role.get("tension",0.65))*(0.7+0.3*p["energy"]),
                cadence_strength=float(role.get("cadence_strength",0.82)),
                max_leap_semitones=int(role.get("max_leap_semitones",7)),
            )
            phrase=compose_phrase(
                ir["materials"],ir["tonal"],seed,motif_id,cfg,
                namespace=f"arrange:lead:{section['id']}"
            )
            start=section["start_bar"]*beats_per_bar
            dur=section["bars"]*beats_per_bar
            part=_filter_and_offset(
                phrase["events"],start,dur,
                keep_ratio=float(p.get("lead_fragment",1.0)),
                register_shift=int(p.get("register_shift",0))
            )
            for e in part:
                e["section_id"]=section["id"]
                e["arrangement_role"]="lead"
            events.extend(part)
            section_meta.append({
                "section_id": section["id"],
                "event_count": len(part),
                "profile": p,
                "transform_log": phrase["transform_log"],
            })
        resolved_tracks.append({
            "id":"lead",
            "instrument":role["instrument"],
            "gain":role.get("gain",0.13),
            "pan":role.get("pan",0.08),
            "fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"arranged_role","role":"lead"}},
            "events":sorted(events,key=lambda e:(e["start_beat"],e["midi"])),
            "arrangement_meta":section_meta,
        })

    # TOPLINE / VOCAL-SPACE GUIDE
    if "topline" in roles:
        role=roles["topline"]
        events=[]
        for sec in ir["form"]:
            p=_profile(ir,sec["id"])
            events.extend(resolve_topline(ir,sec,role,p,seed))
        resolved_tracks.append({
            "id":"topline",
            "instrument":role["instrument"],
            "gain":role.get("gain",0.08),
            "pan":role.get("pan",0.0),
            "fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"topline_lane"}},
            "events":sorted(events,key=lambda e:(e["start_beat"],e["midi"])),
        })

    # PAD / BASS / ARP
    if "pad" in roles:
        role=roles["pad"]; events=[]
        for sec in ir["form"]:
            events.extend(_chord_events(ir,sec,_profile(ir,sec["id"]),role["source"]))
        resolved_tracks.append({
            "id":"pad","instrument":role["instrument"],"gain":role.get("gain",0.10),
            "pan":role.get("pan",-0.05),"fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"arranged_role","role":"pad"}},
            "events":sorted(events,key=lambda e:(e["start_beat"],e["midi"]))
        })

    if "bass" in roles:
        role=roles["bass"]; events=[]
        for sec in ir["form"]:
            events.extend(_bass_events(
                ir,sec,_profile(ir,sec["id"]),role["source"],
                coupled_maps.get(sec["id"])
            ))
        events = articulate_bass(
            events, beats_per_bar,
            ir.get("bass_articulation", {})
        )
        resolved_tracks.append({
            "id":"bass","instrument":role["instrument"],"gain":role.get("gain",0.18),
            "pan":role.get("pan",0.0),"fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"arranged_role","role":"bass"}},
            "events":sorted(events,key=lambda e:(e["start_beat"],e["midi"]))
        })

    if "arp" in roles:
        role=roles["arp"]; events=[]
        for sec in ir["form"]:
            events.extend(_arp_events(ir,sec,_profile(ir,sec["id"]),role["source"]))
        resolved_tracks.append({
            "id":"arp","instrument":role["instrument"],"gain":role.get("gain",0.08),
            "pan":role.get("pan",0.15),"fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"arranged_role","role":"arp"}},
            "events":sorted(events,key=lambda e:(e["start_beat"],e["midi"]))
        })

    if rhythm_result is not None and "drums" in roles:
        role=roles["drums"]
        resolved_tracks.append({
            "id":"drums",
            "instrument":role["instrument"],
            "gain":role.get("gain",1.0),
            "pan":role.get("pan",0.0),
            "fx":role.get("fx",{}),
            "source":{"type":"resolved","derived_from":{"type":"rhythm_engine"}},
            "events":rhythm_result["events"],
            "rhythm_meta":{
                "bar_meta":rhythm_result["bar_meta"],
                "config":rhythm_result["config"],
            }
        })

    # First gate: forbidden roles must not influence cross-role arrangement logic.
    resolved_tracks = enforce_forbidden_track_events(resolved_tracks, ir)
    resolved_tracks = _reserve_topline_space(resolved_tracks, ir)

    for track in resolved_tracks:
        track["events"] = _apply_section_entry_shaping(track.get("events", []), ir)

    # Final gate: downstream arrangement shaping may never reintroduce a forbidden role.
    resolved_tracks = enforce_forbidden_track_events(resolved_tracks, ir)

    out["tracks"]=resolved_tracks
    out["arrangement_resolved"]=True
    return out
