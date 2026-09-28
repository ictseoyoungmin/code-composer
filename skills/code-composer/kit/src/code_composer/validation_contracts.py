from __future__ import annotations

from .composition.harmonic_grammar import COLOR_DEGREE_OFFSETS
from .composition.orchestration import VALID_FOREGROUND_MODES
from .audio.engines import (
    engine_name_for_patch, validate_runtime_patch, InstrumentEngineValidationError,
)

DRUM_ROLES={"kick","snare","hat"}
DEVELOPMENT_STAGES={"legacy","establish","develop","contrast","collapse","culminate"}

class ContractValidationError(ValueError):
    pass

def _object(v,name):
    if not isinstance(v,dict):
        raise ContractValidationError(f"{name} must be an object")
    return v

def _unknown(obj, allowed, name):
    extra=set(obj)-set(allowed)
    if extra:
        raise ContractValidationError(f"{name} has unknown field(s): {sorted(extra)}")

def _num(v,name,lo=None,hi=None):
    if isinstance(v,bool):
        raise ContractValidationError(f"{name} must be numeric")
    try:
        x=float(v)
    except Exception as exc:
        raise ContractValidationError(f"{name} must be numeric") from exc
    if lo is not None and x < lo:
        raise ContractValidationError(f"{name} must be >= {lo}")
    if hi is not None and x > hi:
        raise ContractValidationError(f"{name} must be <= {hi}")
    return x

def _integer(v,name,lo=None,hi=None):
    x=_num(v,name,lo,hi)
    if int(x)!=x:
        raise ContractValidationError(f"{name} must be an integer")
    return int(x)

def _boolean(v,name):
    if not isinstance(v,bool):
        raise ContractValidationError(f"{name} must be boolean")
    return v

def validate_transition_map(transitions, section_ids):
    _object(transitions,"transitions")
    unknown_sections=set(transitions)-set(section_ids)
    if unknown_sections:
        raise ContractValidationError(f"transitions references unknown section(s): {sorted(unknown_sections)}")
    for sid,cfg in transitions.items():
        _object(cfg,f"transitions.{sid}")
        _unknown(cfg,{"entry_gain","entry_soften_beats","pre_fill"},f"transitions.{sid}")
        if "entry_gain" in cfg: _num(cfg["entry_gain"],f"transitions.{sid}.entry_gain",0,2)
        if "entry_soften_beats" in cfg: _num(cfg["entry_soften_beats"],f"transitions.{sid}.entry_soften_beats",0,32)
        if "pre_fill" in cfg: _num(cfg["pre_fill"],f"transitions.{sid}.pre_fill",0,1.5)

_DEVELOPMENT_NUMERIC={
    "lead_density_scale":(0,4),
    "topline_density_scale":(0,4),
    "lead_fragment_scale":(0,4),
    "pad_gain_scale":(0,4),
    "energy_scale":(0,4),
    "rhythm_density_scale":(0,4),
    "fill_scale":(0,4),
    "kick_scale":(0,4),
    "snare_scale":(0,4),
    "hat_scale":(0,4),
}
_DEVELOPMENT_INTS={"register_shift_add":(-48,48),"lead_octave_add":(-4,4)}
_DEVELOPMENT_BOOLS={"bass_active","arp_active"}
_DEVELOPMENT_STRINGS={"motif_variant"}

def _validate_development_profile(profile,name):
    _object(profile,name)
    allowed={"stage"}|set(_DEVELOPMENT_NUMERIC)|set(_DEVELOPMENT_INTS)|_DEVELOPMENT_BOOLS|_DEVELOPMENT_STRINGS
    _unknown(profile,allowed,name)
    if "stage" in profile:
        stage=profile["stage"]
        if stage not in DEVELOPMENT_STAGES:
            raise ContractValidationError(f"{name}.stage must be one of {sorted(DEVELOPMENT_STAGES)}")
    for key,(lo,hi) in _DEVELOPMENT_NUMERIC.items():
        if key in profile: _num(profile[key],f"{name}.{key}",lo,hi)
    for key,(lo,hi) in _DEVELOPMENT_INTS.items():
        if key in profile: _integer(profile[key],f"{name}.{key}",lo,hi)
    for key in _DEVELOPMENT_BOOLS:
        if key in profile: _boolean(profile[key],f"{name}.{key}")
    for key in _DEVELOPMENT_STRINGS:
        if key in profile and (not isinstance(profile[key],str) or not profile[key].strip()):
            raise ContractValidationError(f"{name}.{key} must be a non-empty string")

def validate_development_config(cfg, section_ids, *, runtime=False):
    _object(cfg,"arrangement_development" if runtime else "development")
    allowed={"families","default","sections"}|({"enabled"} if runtime else set())
    _unknown(cfg,allowed,"arrangement_development" if runtime else "development")
    if "enabled" in cfg: _boolean(cfg["enabled"],"arrangement_development.enabled")
    families=cfg.get("families",{})
    _object(families,"development.families")
    for family,members in families.items():
        if not isinstance(family,str) or not family:
            raise ContractValidationError("development family name must be non-empty string")
        if not isinstance(members,list) or any(not isinstance(x,str) for x in members):
            raise ContractValidationError(f"development.families.{family} must be a list of section ids")
        unknown=set(members)-set(section_ids)
        if unknown:
            raise ContractValidationError(f"development.families.{family} references unknown section(s): {sorted(unknown)}")
    _validate_development_profile(cfg.get("default",{}),"development.default")
    sections=cfg.get("sections",{})
    _object(sections,"development.sections")
    unknown=set(sections)-set(section_ids)
    if unknown:
        raise ContractValidationError(f"development references unknown section(s): {sorted(unknown)}")
    for sid,profile in sections.items():
        _validate_development_profile(profile,f"development.sections.{sid}")

_HARMONY_PROFILE_KEYS={
    "colors","cadence_color","normalize_density","motion_weight","center_weight",
    "passing_enabled","passing_degree_offset","passing_beats","passing_color","passing_velocity",
    "progression_variant"
}
def _validate_color(c,name):
    if c not in COLOR_DEGREE_OFFSETS:
        raise ContractValidationError(f"{name} must be one of {sorted(COLOR_DEGREE_OFFSETS)}")

def _validate_harmony_profile(profile,name,require_colors=False):
    _object(profile,name)
    _unknown(profile,_HARMONY_PROFILE_KEYS,name)
    if "colors" in profile:
        colors=profile["colors"]
        if not isinstance(colors,list) or not colors:
            raise ContractValidationError(f"{name}.colors must be a non-empty list")
        for i,c in enumerate(colors): _validate_color(c,f"{name}.colors[{i}]")
    elif require_colors:
        raise ContractValidationError(f"{name}.colors is required")
    if "cadence_color" in profile: _validate_color(profile["cadence_color"],f"{name}.cadence_color")
    if "normalize_density" in profile: _boolean(profile["normalize_density"],f"{name}.normalize_density")
    if "motion_weight" in profile: _num(profile["motion_weight"],f"{name}.motion_weight",0,20)
    if "center_weight" in profile: _num(profile["center_weight"],f"{name}.center_weight",0,20)
    if "passing_enabled" in profile: _boolean(profile["passing_enabled"],f"{name}.passing_enabled")
    if "passing_degree_offset" in profile: _integer(profile["passing_degree_offset"],f"{name}.passing_degree_offset",-14,14)
    if "passing_beats" in profile: _num(profile["passing_beats"],f"{name}.passing_beats",0.01,16)
    if "passing_color" in profile: _validate_color(profile["passing_color"],f"{name}.passing_color")
    if "passing_velocity" in profile: _num(profile["passing_velocity"],f"{name}.passing_velocity",0,2)
    if "progression_variant" in profile:
        if not isinstance(profile["progression_variant"],str) or not profile["progression_variant"].strip():
            raise ContractValidationError(f"{name}.progression_variant must be a non-empty string")

def validate_brief_harmony(harmony, section_ids):
    _object(harmony,"harmony")
    _unknown(harmony,_HARMONY_PROFILE_KEYS|{"sections"},"harmony")
    root={k:v for k,v in harmony.items() if k!="sections"}
    _validate_harmony_profile(root,"harmony",require_colors=True)
    sections=harmony.get("sections",{})
    _object(sections,"harmony.sections")
    unknown=set(sections)-set(section_ids)
    if unknown:
        raise ContractValidationError(f"harmony references unknown section(s): {sorted(unknown)}")
    for sid,profile in sections.items():
        _validate_harmony_profile(profile,f"harmony.sections.{sid}")

def validate_runtime_harmony(grammar, section_ids):
    _object(grammar,"harmonic_grammar")
    _unknown(grammar,{"enabled","default","sections"},"harmonic_grammar")
    if "enabled" in grammar: _boolean(grammar["enabled"],"harmonic_grammar.enabled")
    _validate_harmony_profile(grammar.get("default",{}),"harmonic_grammar.default")
    sections=grammar.get("sections",{})
    _object(sections,"harmonic_grammar.sections")
    unknown=set(sections)-set(section_ids)
    if unknown:
        raise ContractValidationError(f"harmonic_grammar references unknown section(s): {sorted(unknown)}")
    for sid,profile in sections.items():
        _validate_harmony_profile(profile,f"harmonic_grammar.sections.{sid}")

_ORCH_KEYS={"foreground_mode","sparse_role","sparse_density_scale","lead_density_scale","topline_density_scale"}
def _validate_orch_profile(profile,name):
    _object(profile,name)
    _unknown(profile,_ORCH_KEYS,name)
    if "foreground_mode" in profile and profile["foreground_mode"] not in VALID_FOREGROUND_MODES:
        raise ContractValidationError(f"{name}.foreground_mode is invalid")
    if "sparse_role" in profile and profile["sparse_role"] not in {"lead","topline"}:
        raise ContractValidationError(f"{name}.sparse_role must be lead or topline")
    for key in ("sparse_density_scale","lead_density_scale","topline_density_scale"):
        if key in profile: _num(profile[key],f"{name}.{key}",0,4)

def validate_orchestration_config(cfg, section_ids, *, runtime=False):
    name="orchestration_grammar" if runtime else "orchestration"
    _object(cfg,name)
    allowed={"default","sections"}|({"enabled"} if runtime else set())
    _unknown(cfg,allowed,name)
    if "enabled" in cfg: _boolean(cfg["enabled"],f"{name}.enabled")
    _validate_orch_profile(cfg.get("default",{}),f"{name}.default")
    sections=cfg.get("sections",{})
    _object(sections,f"{name}.sections")
    unknown=set(sections)-set(section_ids)
    if unknown:
        raise ContractValidationError(f"{name} references unknown section(s): {sorted(unknown)}")
    for sid,profile in sections.items(): _validate_orch_profile(profile,f"{name}.sections.{sid}")

_RHYTHM_PROFILE_KEYS={"density","kick","snare","hat","fill"}
def _validate_rhythm_profile(profile,name):
    _object(profile,name)
    _unknown(profile,_RHYTHM_PROFILE_KEYS,name)
    for key in _RHYTHM_PROFILE_KEYS:
        if key in profile:
            hi=1.5 if key in {"density","fill"} else 2.0
            _num(profile[key],f"{name}.{key}",0,hi)

def _validate_groove(groove,name):
    _object(groove,name)
    _unknown(groove,{"steps_per_bar","roles","fills"},name)
    steps=_integer(groove.get("steps_per_bar",0),f"{name}.steps_per_bar",1,128)
    roles=_object(groove.get("roles",{}),f"{name}.roles")
    _unknown(roles,DRUM_ROLES,f"{name}.roles")
    for role in DRUM_ROLES:
        cells=roles.get(role)
        if not isinstance(cells,list) or len(cells)!=steps:
            raise ContractValidationError(f"{name}.roles.{role} must have {steps} cells")
        for i,w in enumerate(cells): _num(w,f"{name}.roles.{role}[{i}]",0,1.5)
    fills=groove.get("fills",{})
    _object(fills,f"{name}.fills")
    for fill_name,events in fills.items():
        if not isinstance(events,list):
            raise ContractValidationError(f"{name}.fills.{fill_name} must be a list")
        for i,event in enumerate(events):
            if not isinstance(event,list) or len(event)!=3:
                raise ContractValidationError(f"{name}.fills.{fill_name}[{i}] must be [step, role, weight]")
            step,role,weight=event
            _integer(step,f"{name}.fills.{fill_name}[{i}].step",0,steps-1)
            if role not in DRUM_ROLES:
                raise ContractValidationError(f"{name}.fills.{fill_name}[{i}].role invalid")
            _num(weight,f"{name}.fills.{fill_name}[{i}].weight",0,1.5)

def validate_brief_rhythm(rhythm, section_ids):
    _object(rhythm,"rhythm")
    allowed={"groove","swing","humanize_beats","velocity_jitter","fill_probability","bass_coupling","section_profiles"}
    _unknown(rhythm,allowed,"rhythm")
    _validate_groove(rhythm.get("groove",{}),"rhythm.groove")
    for key,lo,hi in (
        ("swing",0,1),("humanize_beats",0,0.5),("velocity_jitter",0,1),
        ("fill_probability",0,1),("bass_coupling",0,1)):
        if key in rhythm: _num(rhythm[key],f"rhythm.{key}",lo,hi)
    profiles=rhythm.get("section_profiles",{})
    _object(profiles,"rhythm.section_profiles")
    unknown=set(profiles)-set(section_ids)
    if unknown:
        raise ContractValidationError(f"rhythm.section_profiles references unknown section(s): {sorted(unknown)}")
    for sid,p in profiles.items(): _validate_rhythm_profile(p,f"rhythm.section_profiles.{sid}")

def validate_runtime_rhythm(ir, section_ids):
    cfg=ir.get("rhythm_engine")
    if cfg is None: return
    _object(cfg,"rhythm_engine")
    allowed={"groove","steps_per_bar","swing","humanize_beats","velocity_jitter","fill_probability","bass_coupling","section_profiles"}
    _unknown(cfg,allowed,"rhythm_engine")
    groove_id=cfg.get("groove","default")
    if not isinstance(groove_id,str) or groove_id not in ir.get("materials",{}).get("rhythms",{}):
        raise ContractValidationError(f"rhythm_engine.groove refers to unknown rhythm material: {groove_id}")
    groove=ir["materials"]["rhythms"][groove_id]
    _validate_groove(groove,f"materials.rhythms.{groove_id}")
    if "steps_per_bar" in cfg:
        steps=_integer(cfg["steps_per_bar"],"rhythm_engine.steps_per_bar",1,128)
        if steps != int(groove.get("steps_per_bar",steps)):
            raise ContractValidationError("rhythm_engine.steps_per_bar must match selected groove")
    for key,lo,hi in (
        ("swing",0,1),("humanize_beats",0,0.5),("velocity_jitter",0,1),
        ("fill_probability",0,1),("bass_coupling",0,1)):
        if key in cfg: _num(cfg[key],f"rhythm_engine.{key}",lo,hi)
    profiles=cfg.get("section_profiles",{})
    _object(profiles,"rhythm_engine.section_profiles")
    # Legacy engine IR may retain dormant semantic profiles (intro/build/main/break/final)
    # even when the current form uses a subset. Validate their values but do not treat
    # dormant profiles as active section references. Agent-authored Briefs remain strict.
    for sid,p in profiles.items(): _validate_rhythm_profile(p,f"rhythm_engine.section_profiles.{sid}")

def validate_piano_instrument_patch(inst_id, patch):
    """Backward-compatible public validator; actual piano rules live in PianoEngine."""
    if not isinstance(patch,dict):
        return
    try:
        if engine_name_for_patch(patch) != "piano":
            return
        validate_runtime_patch(inst_id,patch)
    except InstrumentEngineValidationError as exc:
        raise ContractValidationError(str(exc)) from exc

def validate_instrument_patch(inst_id, patch):
    if not isinstance(patch,dict) or patch.get("kind") == "percussion":
        return
    try:
        validate_runtime_patch(inst_id,patch)
    except InstrumentEngineValidationError as exc:
        raise ContractValidationError(str(exc)) from exc

def validate_arrangement_profiles(ir, section_ids):
    arrangement=ir.get("arrangement")
    if not isinstance(arrangement,dict): return
    profiles=arrangement.get("profiles",{})
    if not isinstance(profiles,dict):
        raise ContractValidationError("arrangement.profiles must be an object")
    unknown=set(profiles)-set(section_ids)
    # Legacy seeds may keep profiles for semantic section types not present in this form.
    # Only validate values for present sections; do not reject dormant legacy profiles.
    for sid,p in profiles.items():
        if not isinstance(p,dict):
            raise ContractValidationError(f"arrangement.profiles.{sid} must be an object")
        if "entry_gain" in p: _num(p["entry_gain"],f"arrangement.profiles.{sid}.entry_gain",0,2)
        if "entry_soften_beats" in p: _num(p["entry_soften_beats"],f"arrangement.profiles.{sid}.entry_soften_beats",0,32)

REMOVED_ANALYZER_MUTATION_FIELDS = {
    "transition_analysis",
    "transition_material",
    "pre_hook_build",
    "pre_hook_analysis",
}


def validate_drum_control_events(ir):
    instruments = ir.get("instruments", {})
    for track in ir.get("tracks", []):
        patch = instruments.get(track.get("instrument"), {})
        controls = []
        for i, event in enumerate(track.get("events", [])):
            if event.get("event_type") != "drum_control":
                continue
            name = f"track {track.get('id','<unknown>')} drum_control[{i}]"
            if not isinstance(patch, dict) or patch.get("kind") != "percussion":
                raise ContractValidationError(f"{name} requires a percussion instrument")
            _unknown(event, {"event_type","control","start_beat","duration_beats","points","section_id"}, name)
            if event.get("control") != "hi_hat_pedal_openness":
                raise ContractValidationError(f"{name}.control unsupported")
            start = _num(event.get("start_beat", 0.0), f"{name}.start_beat", 0.0)
            duration = _num(event.get("duration_beats", 0.0), f"{name}.duration_beats", 1e-9)
            points = event.get("points")
            if not isinstance(points, list) or len(points) < 2:
                raise ContractValidationError(f"{name}.points must contain at least two points")
            previous = None
            for j, point in enumerate(points):
                if not isinstance(point, dict):
                    raise ContractValidationError(f"{name}.points[{j}] must be an object")
                _unknown(point, {"offset_beats","openness"}, f"{name}.points[{j}]")
                offset = _num(point.get("offset_beats"), f"{name}.points[{j}].offset_beats", 0.0, duration)
                _num(point.get("openness"), f"{name}.points[{j}].openness", 0.0, 1.0)
                if previous is not None and offset <= previous + 1e-12:
                    raise ContractValidationError(f"{name}.points offsets must be strictly increasing")
                previous = offset
            if abs(float(points[0]["offset_beats"])) > 1e-12:
                raise ContractValidationError(f"{name}.points must start at offset_beats=0")
            if abs(float(points[-1]["offset_beats"]) - duration) > 1e-9:
                raise ContractValidationError(f"{name}.points must end at duration_beats")
            controls.append((start, start + duration, name))
        controls.sort()
        for (_, end, prev_name), (start, _, name) in zip(controls, controls[1:]):
            if start < end - 1e-12:
                raise ContractValidationError(f"{name} overlaps {prev_name}; hi-hat pedal curves must be sequential")



def validate_piano_control_events(ir):
    instruments=ir.get("instruments",{})
    for track in ir.get("tracks",[]):
        patch=instruments.get(track.get("instrument"),{})
        controls=[]
        bpm=float(ir.get("transport",{}).get("bpm",120.0))
        beat_ms=60000.0/max(1e-9,bpm)
        for i,event in enumerate(track.get("events",[])):
            if "midi" in event and event.get("event_type") != "piano_control":
                perf=event.get("performance")
                if isinstance(perf,dict) and "piano_attack_offset_ms" in perf:
                    name=f"track {track.get('id','<unknown>')} piano note[{i}].performance.piano_attack_offset_ms"
                    offset=_num(perf.get("piano_attack_offset_ms"),name,-20.0,20.0)
                    effective=float(event.get("start_beat",0.0)) + offset/beat_ms
                    if effective < -1e-12:
                        raise ContractValidationError(f"{name} moves note before beat 0")
            if event.get("event_type") != "piano_control":
                continue
            name=f"track {track.get('id','<unknown>')} piano_control[{i}]"
            if not isinstance(patch,dict) or patch.get("kind") != "piano":
                raise ContractValidationError(f"{name} requires a piano instrument")
            if patch.get("piano_engine")=="electric" or "electric_piano_graph" in patch:
                raise ContractValidationError(f"{name} currently requires an acoustic piano instrument")
            _unknown(event,{"event_type","control","start_beat","duration_beats","points","section_id"},name)
            if event.get("control") != "sustain_pedal":
                raise ContractValidationError(f"{name}.control unsupported")
            start=_num(event.get("start_beat",0.0),f"{name}.start_beat",0.0)
            duration=_num(event.get("duration_beats",0.0),f"{name}.duration_beats",1e-9)
            points=event.get("points")
            if not isinstance(points,list) or len(points)<2:
                raise ContractValidationError(f"{name}.points must contain at least two points")
            previous=None
            for j,point in enumerate(points):
                if not isinstance(point,dict):
                    raise ContractValidationError(f"{name}.points[{j}] must be an object")
                _unknown(point,{"offset_beats","position"},f"{name}.points[{j}]")
                offset=_num(point.get("offset_beats"),f"{name}.points[{j}].offset_beats",0.0,duration)
                _num(point.get("position"),f"{name}.points[{j}].position",0.0,1.0)
                if previous is not None and offset <= previous+1e-12:
                    raise ContractValidationError(f"{name}.points offsets must be strictly increasing")
                previous=offset
            if abs(float(points[0]["offset_beats"]))>1e-12:
                raise ContractValidationError(f"{name}.points must start at offset_beats=0")
            if abs(float(points[-1]["offset_beats"])-duration)>1e-9:
                raise ContractValidationError(f"{name}.points must end at duration_beats")
            controls.append((start,start+duration,name))
        controls.sort()
        for (_,end,prev_name),(start,_,name) in zip(controls,controls[1:]):
            if start < end-1e-12:
                raise ContractValidationError(f"{name} overlaps {prev_name}; sustain-pedal curves must be sequential")


def validate_development_motif_refs(ir):
    cfg=ir.get("arrangement_development")
    if not isinstance(cfg,dict):
        return
    motifs=ir.get("materials",{}).get("motifs",{})
    profiles=[("arrangement_development.default",cfg.get("default",{}))]
    profiles += [(f"arrangement_development.sections.{sid}",p) for sid,p in cfg.get("sections",{}).items()]
    for name,profile in profiles:
        if not isinstance(profile,dict):
            continue
        motif_id=profile.get("motif_variant")
        if motif_id is not None and motif_id not in motifs:
            raise ContractValidationError(f"{name}.motif_variant references unknown motif: {motif_id}")



def validate_harmony_progression_refs(ir):
    grammar=ir.get("harmonic_grammar")
    if not isinstance(grammar,dict):
        return
    progressions=ir.get("materials",{}).get("progressions",{})
    profiles=[("harmonic_grammar.default",grammar.get("default",{}))]
    profiles += [(f"harmonic_grammar.sections.{sid}",p) for sid,p in grammar.get("sections",{}).items()]
    for name,profile in profiles:
        if not isinstance(profile,dict):
            continue
        progression_id=profile.get("progression_variant")
        if progression_id is not None and progression_id not in progressions:
            raise ContractValidationError(f"{name}.progression_variant references unknown progression: {progression_id}")

def validate_runtime_extensions(ir):
    removed = REMOVED_ANALYZER_MUTATION_FIELDS & set(ir)
    if removed:
        raise ContractValidationError(
            "removed analyzer-driven mutation field(s): "
            + ", ".join(sorted(removed))
            + "; author explicit v1.16 transition/performance state instead"
        )
    section_ids={s.get("id") for s in ir.get("form",[]) if isinstance(s,dict)}
    for inst_id,patch in ir.get("instruments",{}).items():
        validate_instrument_patch(inst_id,patch)
    if "harmonic_grammar" in ir:
        validate_runtime_harmony(ir["harmonic_grammar"],section_ids)
        validate_harmony_progression_refs(ir)
    if "orchestration_grammar" in ir:
        validate_orchestration_config(ir["orchestration_grammar"],section_ids,runtime=True)
    if "arrangement_development" in ir:
        validate_development_config(ir["arrangement_development"],section_ids,runtime=True)
        validate_development_motif_refs(ir)
    validate_runtime_rhythm(ir,section_ids)
    validate_arrangement_profiles(ir,section_ids)
    validate_drum_control_events(ir)
    validate_piano_control_events(ir)

__all__=[
    "ContractValidationError","validate_transition_map","validate_development_config","validate_development_motif_refs",
    "validate_brief_harmony","validate_runtime_harmony","validate_harmony_progression_refs","validate_orchestration_config",
    "validate_brief_rhythm","validate_runtime_rhythm","validate_piano_instrument_patch","validate_instrument_patch",
    "validate_arrangement_profiles","validate_drum_control_events","validate_piano_control_events","validate_runtime_extensions","REMOVED_ANALYZER_MUTATION_FIELDS",
]
