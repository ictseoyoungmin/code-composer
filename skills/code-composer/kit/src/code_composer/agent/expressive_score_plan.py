from __future__ import annotations

from dataclasses import dataclass, asdict
from copy import deepcopy


class ExpressivePlanValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExpressiveValidationContext:
    section_ids: tuple[str, ...]
    role_ids: tuple[str, ...]
    source_material_ids: tuple[str, ...]
    section_spans: dict[str, tuple[float, float]] | None = None


@dataclass(frozen=True)
class ExpressiveScorePlan:
    version: str
    narrative: dict
    phrases: tuple[dict, ...]
    motif_statements: tuple[dict, ...]
    register_plans: dict
    orchestration_sections: dict
    transitions: tuple[dict, ...]


def expressive_score_plan_from_dict(data: dict) -> ExpressiveScorePlan:
    if not isinstance(data, dict):
        raise ExpressivePlanValidationError("expressive score plan must be an object")
    required=(
        "version","narrative","phrases","motif_statements",
        "register_plans","orchestration_sections","transitions",
    )
    missing=[k for k in required if k not in data]
    if missing:
        raise ExpressivePlanValidationError(f"missing expressive score plan fields: {missing}")
    unknown=set(data)-set(required)
    if unknown:
        raise ExpressivePlanValidationError(f"unknown expressive score plan fields: {sorted(unknown)}")
    return ExpressiveScorePlan(
        version=str(data["version"]),
        narrative=deepcopy(data["narrative"]),
        phrases=tuple(deepcopy(data["phrases"])),
        motif_statements=tuple(deepcopy(data["motif_statements"])),
        register_plans=deepcopy(data["register_plans"]),
        orchestration_sections=deepcopy(data["orchestration_sections"]),
        transitions=tuple(deepcopy(data["transitions"])),
    )


def expressive_score_plan_to_dict(plan: ExpressiveScorePlan) -> dict:
    out=asdict(plan)
    out["phrases"]=[deepcopy(x) for x in plan.phrases]
    out["motif_statements"]=[deepcopy(x) for x in plan.motif_statements]
    out["transitions"]=[deepcopy(x) for x in plan.transitions]
    return out


def _fail(msg: str):
    raise ExpressivePlanValidationError(msg)


def _obj(v, name):
    if not isinstance(v,dict):
        _fail(f"{name} must be an object")
    return v


def _list(v,name):
    if not isinstance(v,list):
        _fail(f"{name} must be a list")
    return v


def _num(v,name,lo=None,hi=None):
    if isinstance(v,bool):
        _fail(f"{name} must be numeric")
    try:
        x=float(v)
    except Exception as exc:
        raise ExpressivePlanValidationError(f"{name} must be numeric") from exc
    if lo is not None and x<lo:
        _fail(f"{name} must be >= {lo}")
    if hi is not None and x>hi:
        _fail(f"{name} must be <= {hi}")
    return x


def _integer(v,name,lo=None,hi=None):
    x=_num(v,name,lo,hi)
    if int(x)!=x:
        _fail(f"{name} must be an integer")
    return int(x)


def _curve(points,name,value_lo=None,value_hi=None,require_endpoints=True):
    _list(points,name)
    if len(points)<2:
        _fail(f"{name} must contain at least two control points")
    positions=[]
    for i,p in enumerate(points):
        if not isinstance(p,list) or len(p)!=2:
            _fail(f"{name}[{i}] must be [position, value]")
        pos=_num(p[0],f"{name}[{i}].position",0,1)
        _num(p[1],f"{name}[{i}].value",value_lo,value_hi)
        positions.append(pos)
    if any(b<=a for a,b in zip(positions,positions[1:])):
        _fail(f"{name} positions must be strictly increasing")
    if require_endpoints and (abs(positions[0])>1e-9 or abs(positions[-1]-1.0)>1e-9):
        _fail(f"{name} must start at 0.0 and end at 1.0")


TRANSFORM_OPS={
    "exact","fragment","sequence","transpose","register_shift","rhythm_scale",
    "rhythm_rewrite","inversion","retrograde","cadence_rewrite","ornament",
    "call","response",
}
ARTICULATIONS={"legato","tenuto","neutral","staccato","accent","marcato","pizzicato","harmonic","spiccato"}
INSTRUMENT_EXPRESSION_CURVE_RANGES={
    "bow_pressure": (0.0, 1.0),
    "bow_speed": (0.0, 1.0),
    "bow_position": (0.035, 0.45),
    "bow_noise_gain": (0.0, 0.05),
    "vibrato_rate_hz": (0.0, 12.0),
    "vibrato_depth_cents": (0.0, 100.0),
    "vibrato_onset_s": (0.0, 4.0),
}
OVERLAP_POLICIES={"allow","avoid","primary_wins","short_only"}
MOTION_POLICIES={"free","smooth","contrary","oblique","stepwise_preferred"}
BASS_APPROACHES={"none","step","chromatic","scale","pedal"}


def _validate_transform(t,name):
    _obj(t,name)
    allowed={"op","start","length","semitones","scale_degrees","factor","rhythm","intervals","responds_to"}
    unknown=set(t)-allowed
    if unknown:
        _fail(f"{name} has unknown field(s): {sorted(unknown)}")
    op=t.get("op")
    if op not in TRANSFORM_OPS:
        _fail(f"{name}.op must be one of {sorted(TRANSFORM_OPS)}")
    if "start" in t: _integer(t["start"],f"{name}.start",0)
    if "length" in t: _integer(t["length"],f"{name}.length",1)
    if "semitones" in t: _integer(t["semitones"],f"{name}.semitones",-36,36)
    if "scale_degrees" in t: _integer(t["scale_degrees"],f"{name}.scale_degrees",-14,14)
    if "factor" in t: _num(t["factor"],f"{name}.factor",1e-9,8)
    if "rhythm" in t:
        vals=_list(t["rhythm"],f"{name}.rhythm")
        if not vals: _fail(f"{name}.rhythm must be non-empty")
        for i,v in enumerate(vals): _num(v,f"{name}.rhythm[{i}]",1e-9)
    if "intervals" in t:
        vals=_list(t["intervals"],f"{name}.intervals")
        if not vals: _fail(f"{name}.intervals must be non-empty")
        for i,v in enumerate(vals): _integer(v,f"{name}.intervals[{i}]",-24,24)
    if "responds_to" in t and (not isinstance(t["responds_to"],str) or not t["responds_to"].strip()):
        _fail(f"{name}.responds_to must be a non-empty statement ID")

    # Operation-specific minimum parameter contracts.
    if op=="fragment" and not {"start","length"} <= set(t):
        _fail(f"{name}: fragment requires start and length")
    if op=="sequence" and "scale_degrees" not in t:
        _fail(f"{name}: sequence requires scale_degrees")
    if op in {"transpose","register_shift"} and "semitones" not in t:
        _fail(f"{name}: {op} requires semitones")
    if op=="rhythm_scale" and "factor" not in t:
        _fail(f"{name}: rhythm_scale requires factor")
    if op=="rhythm_rewrite" and "rhythm" not in t:
        _fail(f"{name}: rhythm_rewrite requires rhythm")
    if op=="cadence_rewrite":
        if "intervals" not in t:
            _fail(f"{name}: cadence_rewrite requires intervals")
        if "rhythm" in t and len(t["rhythm"]) != len(t["intervals"]):
            _fail(f"{name}: cadence_rewrite rhythm length must match intervals")
    if op=="ornament":
        if "start" not in t or "intervals" not in t or "rhythm" not in t:
            _fail(f"{name}: ornament requires start, intervals and rhythm")
        if len(t["rhythm"]) != len(t["intervals"]):
            _fail(f"{name}: ornament rhythm length must match intervals")
    if op=="call":
        if "intervals" not in t or "rhythm" not in t:
            _fail(f"{name}: call requires explicit intervals and rhythm")
        if len(t["rhythm"]) != len(t["intervals"]):
            _fail(f"{name}: call rhythm length must match intervals")
    if op=="response":
        if "intervals" not in t or "rhythm" not in t or "responds_to" not in t:
            _fail(f"{name}: response requires explicit intervals, rhythm and responds_to")
        if len(t["rhythm"]) != len(t["intervals"]):
            _fail(f"{name}: response rhythm length must match intervals")


def validate_expressive_score_plan(
    plan: ExpressiveScorePlan,
    context: ExpressiveValidationContext,
) -> None:
    if plan.version!="1.16":
        _fail("expressive score plan version must be 1.16")

    sections=tuple(context.section_ids)
    section_set=set(sections)
    roles=set(context.role_ids)
    source_materials=set(context.source_material_ids)

    if not sections or len(section_set)!=len(sections):
        _fail("validation context section_ids must be unique and non-empty")
    if len(roles)!=len(context.role_ids):
        _fail("validation context role_ids must be unique")
    if len(source_materials)!=len(context.source_material_ids):
        _fail("validation context source_material_ids must be unique")

    narrative=_obj(plan.narrative,"narrative")
    unknown=set(narrative)-{"arc","section_intents"}
    if unknown:
        _fail(f"narrative has unknown field(s): {sorted(unknown)}")
    if not isinstance(narrative.get("arc"),str) or not narrative["arc"].strip():
        _fail("narrative.arc must be a non-empty string")
    intents=narrative.get("section_intents",{})
    _obj(intents,"narrative.section_intents")
    unknown_sections=set(intents)-section_set
    if unknown_sections:
        _fail(f"narrative.section_intents references unknown section(s): {sorted(unknown_sections)}")
    for sid,text in intents.items():
        if not isinstance(text,str) or not text.strip():
            _fail(f"narrative.section_intents.{sid} must be non-empty string")

    statement_ids=[]
    statement_map={}
    for i,stmt in enumerate(plan.motif_statements):
        name=f"motif_statements[{i}]"
        _obj(stmt,name)
        allowed={"statement_id","source_motif_id","section_id","transform_chain","identity_floor","identity_hard_min","cadence_rule"}
        unknown=set(stmt)-allowed
        if unknown:
            _fail(f"{name} has unknown field(s): {sorted(unknown)}")
        sid=stmt.get("statement_id")
        if not isinstance(sid,str) or not sid:
            _fail(f"{name}.statement_id must be non-empty string")
        statement_ids.append(sid)
        statement_map[sid]=stmt
        source=stmt.get("source_motif_id")
        if source not in source_materials:
            _fail(f"{name}.source_motif_id references unknown source material: {source}")
        section=stmt.get("section_id")
        if section not in section_set:
            _fail(f"{name}.section_id references unknown section: {section}")
        chain=_list(stmt.get("transform_chain"),f"{name}.transform_chain")
        if not chain:
            _fail(f"{name}.transform_chain must be non-empty")
        for j,t in enumerate(chain):
            _validate_transform(t,f"{name}.transform_chain[{j}]")
        floor=_num(stmt.get("identity_floor"),f"{name}.identity_floor",0,1)
        if "identity_hard_min" in stmt:
            hard=_num(stmt["identity_hard_min"],f"{name}.identity_hard_min",0,1)
            if hard > floor + 1e-12:
                _fail(f"{name}.identity_hard_min cannot exceed identity_floor")
        if "cadence_rule" in stmt and not isinstance(stmt["cadence_rule"],str):
            _fail(f"{name}.cadence_rule must be string")
    if len(statement_ids)!=len(set(statement_ids)):
        _fail("motif statement IDs must be unique")
    statement_set=set(statement_ids)
    statement_index={sid:i for i,sid in enumerate(statement_ids)}
    for i,stmt in enumerate(plan.motif_statements):
        for j,t in enumerate(stmt["transform_chain"]):
            if t.get("op") != "response":
                continue
            name=f"motif_statements[{i}].transform_chain[{j}]"
            target=t["responds_to"]
            if target not in statement_map:
                _fail(f"{name}.responds_to references unknown statement: {target}")
            if statement_index[target] >= i:
                _fail(f"{name}.responds_to must reference an earlier call statement")
            target_stmt=statement_map[target]
            if not any(op.get("op")=="call" for op in target_stmt["transform_chain"]):
                _fail(f"{name}.responds_to must reference a statement containing a call transform")

    phrase_ids=[]
    for i,phrase in enumerate(plan.phrases):
        name=f"phrases[{i}]"
        _obj(phrase,name)
        allowed={
            "phrase_id","section_id","role","source_material","start_beat","duration_beats",
            "dynamic_curve","timing_curve_ms","gate_curve","articulation_curve",
            "accent_points","apex_position","breath_after_beats","instrument_expression_curves",
        }
        unknown=set(phrase)-allowed
        if unknown:
            _fail(f"{name} has unknown field(s): {sorted(unknown)}")
        pid=phrase.get("phrase_id")
        if not isinstance(pid,str) or not pid:
            _fail(f"{name}.phrase_id must be non-empty string")
        phrase_ids.append(pid)
        section=phrase.get("section_id")
        if section not in section_set:
            _fail(f"{name}.section_id references unknown section: {section}")
        role=phrase.get("role")
        if role not in roles:
            _fail(f"{name}.role references unknown role: {role}")
        source=phrase.get("source_material")
        if source not in source_materials and source not in statement_set:
            _fail(f"{name}.source_material references unknown material/statement: {source}")
        if source in statement_set and statement_map[source].get("section_id") != section:
            _fail(
                f"{name}.source_material statement {source} belongs to section "
                f"{statement_map[source].get('section_id')}, not {section}"
            )
        start=_num(phrase.get("start_beat"),f"{name}.start_beat",0)
        duration=_num(phrase.get("duration_beats"),f"{name}.duration_beats",1e-9)
        _curve(phrase.get("dynamic_curve"),f"{name}.dynamic_curve",0,1)
        _curve(phrase.get("timing_curve_ms"),f"{name}.timing_curve_ms",-30,30)
        _curve(phrase.get("gate_curve"),f"{name}.gate_curve",0.05,2.0)

        arts=_list(phrase.get("articulation_curve"),f"{name}.articulation_curve")
        if not arts:
            _fail(f"{name}.articulation_curve must be non-empty")
        last_pos=-1.0
        for j,a in enumerate(arts):
            _obj(a,f"{name}.articulation_curve[{j}]")
            if set(a)!={"position","articulation"}:
                _fail(f"{name}.articulation_curve[{j}] must contain position and articulation only")
            pos=_num(a["position"],f"{name}.articulation_curve[{j}].position",0,1)
            if pos<last_pos:
                _fail(f"{name}.articulation_curve positions must be non-decreasing")
            last_pos=pos
            if a["articulation"] not in ARTICULATIONS:
                _fail(f"{name}.articulation_curve[{j}].articulation invalid")

        accents=_list(phrase.get("accent_points"),f"{name}.accent_points")
        last=-1.0
        for j,a in enumerate(accents):
            _obj(a,f"{name}.accent_points[{j}]")
            if set(a)!={"position","amount"}:
                _fail(f"{name}.accent_points[{j}] must contain position and amount only")
            pos=_num(a["position"],f"{name}.accent_points[{j}].position",0,1)
            if pos<last:
                _fail(f"{name}.accent_points positions must be non-decreasing")
            last=pos
            _num(a["amount"],f"{name}.accent_points[{j}].amount",-1,1)
        if "apex_position" in phrase:
            _num(phrase["apex_position"],f"{name}.apex_position",0,1)

        expression_curves=phrase.get("instrument_expression_curves",{})
        _obj(expression_curves,f"{name}.instrument_expression_curves")
        unknown_expression=set(expression_curves)-set(INSTRUMENT_EXPRESSION_CURVE_RANGES)
        if unknown_expression:
            _fail(
                f"{name}.instrument_expression_curves has unsupported control(s): "
                f"{sorted(unknown_expression)}"
            )
        for control,points in expression_curves.items():
            lo,hi=INSTRUMENT_EXPRESSION_CURVE_RANGES[control]
            _curve(points,f"{name}.instrument_expression_curves.{control}",lo,hi)

        _num(phrase.get("breath_after_beats"),f"{name}.breath_after_beats",0,8)

        if context.section_spans is not None:
            if section not in context.section_spans:
                _fail(f"validation context missing section span for {section}")
            sec_start,sec_end=context.section_spans[section]
            if start < sec_start-1e-9 or start+duration > sec_end+1e-9:
                _fail(
                    f"{name} [{start},{start+duration}] exceeds section {section} "
                    f"span [{sec_start},{sec_end}]"
                )
    if len(phrase_ids)!=len(set(phrase_ids)):
        _fail("phrase IDs must be unique")

    # E1 execution contract: a single role cannot carry two overlapping phrase
    # envelopes, and authored breath must remain real silence before the next
    # phrase for that role. Polyphony should use separate roles/voices rather than
    # ambiguous overlapping performance envelopes.
    by_role={}
    for phrase in plan.phrases:
        by_role.setdefault(phrase["role"],[]).append(phrase)
    for role,items in by_role.items():
        items=sorted(items,key=lambda p:(float(p["start_beat"]),p["phrase_id"]))
        for a,b in zip(items,items[1:]):
            a_end=(float(a["start_beat"])+float(a["duration_beats"])+
                   float(a.get("breath_after_beats",0.0)))
            if a_end > float(b["start_beat"]) + 1e-9:
                _fail(
                    f"phrases for role {role} overlap authored phrase/breath: "
                    f"{a['phrase_id']} -> {b['phrase_id']}"
                )

    for role,cfg in plan.register_plans.items():
        name=f"register_plans.{role}"
        if role not in roles:
            _fail(f"{name} references unknown role")
        _obj(cfg,name)
        allowed={
            "hard_range","preferred_range","center","max_span","min_intervoice_distance",
            "overlap_policy","motion_policy",
        }
        unknown=set(cfg)-allowed
        if unknown: _fail(f"{name} has unknown field(s): {sorted(unknown)}")
        for key in ("hard_range","preferred_range"):
            vals=cfg.get(key)
            if not isinstance(vals,list) or len(vals)!=2:
                _fail(f"{name}.{key} must be [low, high]")
            lo=_integer(vals[0],f"{name}.{key}[0]",0,127)
            hi=_integer(vals[1],f"{name}.{key}[1]",0,127)
            if lo>hi: _fail(f"{name}.{key} low must be <= high")
        h0,h1=cfg["hard_range"]
        p0,p1=cfg["preferred_range"]
        if p0<h0 or p1>h1:
            _fail(f"{name}.preferred_range must lie within hard_range")
        center=_num(cfg.get("center"),f"{name}.center",0,127)
        if not h0<=center<=h1:
            _fail(f"{name}.center must lie within hard_range")
        max_span=_integer(cfg.get("max_span"),f"{name}.max_span",0,60)
        if max_span > h1-h0:
            _fail(f"{name}.max_span cannot exceed hard_range width")
        _integer(cfg.get("min_intervoice_distance"),f"{name}.min_intervoice_distance",0,24)
        if cfg.get("overlap_policy","allow") not in OVERLAP_POLICIES:
            _fail(f"{name}.overlap_policy invalid")
        if cfg.get("motion_policy","free") not in MOTION_POLICIES:
            _fail(f"{name}.motion_policy invalid")

    orch_sections=set(plan.orchestration_sections)
    unknown=orch_sections-section_set
    if unknown:
        _fail(f"orchestration_sections references unknown section(s): {sorted(unknown)}")
    missing=section_set-orch_sections
    if missing:
        _fail(f"orchestration_sections missing section(s): {sorted(missing)}")
    for section,cfg in plan.orchestration_sections.items():
        name=f"orchestration_sections.{section}"
        _obj(cfg,name)
        allowed={
            "primary_roles","secondary_roles","decorative_roles","max_simultaneous_roles",
            "allowed_overlaps","phrase_gap_only_roles","silence_roles","ensemble_interaction",
        }
        unknown=set(cfg)-allowed
        if unknown: _fail(f"{name} has unknown field(s): {sorted(unknown)}")
        groups={}
        for key in ("primary_roles","secondary_roles","decorative_roles","silence_roles"):
            vals=_list(cfg.get(key),f"{name}.{key}")
            if len(vals)!=len(set(vals)):
                _fail(f"{name}.{key} contains duplicate roles")
            bad=set(vals)-roles
            if bad: _fail(f"{name}.{key} references unknown role(s): {sorted(bad)}")
            groups[key]=set(vals)
        active=groups["primary_roles"]|groups["secondary_roles"]|groups["decorative_roles"]
        if (
            groups["primary_roles"] & groups["secondary_roles"]
            or groups["primary_roles"] & groups["decorative_roles"]
            or groups["secondary_roles"] & groups["decorative_roles"]
        ):
            _fail(f"{name} active role groups must be disjoint")
        if active & groups["silence_roles"]:
            _fail(f"{name}.silence_roles cannot also be active")
        max_roles=_integer(cfg.get("max_simultaneous_roles"),f"{name}.max_simultaneous_roles",1,16)
        if max_roles>max(1,len(active)):
            _fail(f"{name}.max_simultaneous_roles cannot exceed active role count")
        if max_roles < len(groups["primary_roles"]):
            _fail(f"{name}.max_simultaneous_roles cannot be smaller than primary role count")
        gaps=_list(cfg.get("phrase_gap_only_roles",[]),f"{name}.phrase_gap_only_roles")
        if len(gaps)!=len(set(gaps)):
            _fail(f"{name}.phrase_gap_only_roles contains duplicates")
        if not set(gaps)<=groups["decorative_roles"]:
            _fail(f"{name}.phrase_gap_only_roles must be decorative roles")
        overlaps=_list(cfg.get("allowed_overlaps",[]),f"{name}.allowed_overlaps")
        seen_pairs=set()
        for j,pair in enumerate(overlaps):
            if not isinstance(pair,list) or len(pair)!=2:
                _fail(f"{name}.allowed_overlaps[{j}] must be [role_a, role_b]")
            a,b=pair
            if a==b: _fail(f"{name}.allowed_overlaps[{j}] roles must differ")
            if a not in roles or b not in roles:
                _fail(f"{name}.allowed_overlaps[{j}] references unknown role")
            if a not in active or b not in active:
                _fail(f"{name}.allowed_overlaps[{j}] must reference active roles in the section")
            key=tuple(sorted((a,b)))
            if key in seen_pairs:
                _fail(f"{name}.allowed_overlaps contains duplicate pair {key}")
            seen_pairs.add(key)

        interaction=cfg.get("ensemble_interaction")
        if interaction is not None:
            _obj(interaction,f"{name}.ensemble_interaction")
            allowed_interaction={
                "enabled","leader_role","timing_offsets_ms","overlap_velocity_scales",
            }
            unknown=set(interaction)-allowed_interaction
            if unknown:
                _fail(
                    f"{name}.ensemble_interaction has unknown field(s): {sorted(unknown)}"
                )
            enabled=interaction.get("enabled",True)
            if not isinstance(enabled,bool):
                _fail(f"{name}.ensemble_interaction.enabled must be boolean")
            if enabled:
                leader=interaction.get("leader_role")
                if not isinstance(leader,str) or not leader:
                    _fail(f"{name}.ensemble_interaction.leader_role must be non-empty string")
                if leader not in active:
                    _fail(f"{name}.ensemble_interaction.leader_role must be active in section")
                timing=interaction.get("timing_offsets_ms",{})
                _obj(timing,f"{name}.ensemble_interaction.timing_offsets_ms")
                for role,value in timing.items():
                    if role not in active:
                        _fail(
                            f"{name}.ensemble_interaction.timing_offsets_ms references "
                            f"inactive role {role}"
                        )
                    _num(
                        value,
                        f"{name}.ensemble_interaction.timing_offsets_ms.{role}",
                        -30,30,
                    )
                scales=interaction.get("overlap_velocity_scales",{})
                _obj(scales,f"{name}.ensemble_interaction.overlap_velocity_scales")
                for role,value in scales.items():
                    if role not in active:
                        _fail(
                            f"{name}.ensemble_interaction.overlap_velocity_scales references "
                            f"inactive role {role}"
                        )
                    if role==leader:
                        _fail(
                            f"{name}.ensemble_interaction leader role cannot yield to itself"
                        )
                    _num(
                        value,
                        f"{name}.ensemble_interaction.overlap_velocity_scales.{role}",
                        .5,1.0,
                    )

    transition_pairs=[]
    section_index={sid:i for i,sid in enumerate(sections)}
    for i,t in enumerate(plan.transitions):
        name=f"transitions[{i}]"
        _obj(t,name)
        allowed={
            "from_section","to_section","harmonic_anticipation","pickup","bass_approach",
            "cadence_extension","texture_subtraction","silence_beats",
            "register_preparation","rhythm_fill",
        }
        unknown=set(t)-allowed
        if unknown: _fail(f"{name} has unknown field(s): {sorted(unknown)}")
        a=t.get("from_section"); b=t.get("to_section")
        if a not in section_set or b not in section_set:
            _fail(f"{name} references unknown section")
        if a==b: _fail(f"{name} cannot transition a section to itself")
        if section_index[b] != section_index[a]+1:
            _fail(f"{name} must connect adjacent sections in form order")
        pair=(a,b)
        if pair in transition_pairs:
            _fail(f"duplicate transition {a}->{b}")
        transition_pairs.append(pair)

        anticipation=t.get("harmonic_anticipation",{})
        _obj(anticipation,f"{name}.harmonic_anticipation")
        unknown=set(anticipation)-{"enabled","role","beats","target_degree","chord_intervals","velocity","gate"}
        if unknown: _fail(f"{name}.harmonic_anticipation unknown field(s): {sorted(unknown)}")
        enabled=anticipation.get("enabled",False)
        if not isinstance(enabled,bool): _fail(f"{name}.harmonic_anticipation.enabled must be boolean")
        if enabled:
            req={"role","beats","target_degree","chord_intervals","velocity","gate"}
            missing=req-set(anticipation)
            if missing: _fail(f"{name}.harmonic_anticipation missing fields: {sorted(missing)}")
            if anticipation["role"] not in roles: _fail(f"{name}.harmonic_anticipation.role references unknown role")
            _num(anticipation["beats"],f"{name}.harmonic_anticipation.beats",1e-9,8)
            _integer(anticipation["target_degree"],f"{name}.harmonic_anticipation.target_degree",1,7)
            ints=_list(anticipation["chord_intervals"],f"{name}.harmonic_anticipation.chord_intervals")
            if not ints or len(ints)>8: _fail(f"{name}.harmonic_anticipation.chord_intervals must contain 1..8 values")
            if len(ints)!=len(set(ints)): _fail(f"{name}.harmonic_anticipation.chord_intervals must be unique")
            for j,v in enumerate(ints): _integer(v,f"{name}.harmonic_anticipation.chord_intervals[{j}]",-14,14)
            _num(anticipation["velocity"],f"{name}.harmonic_anticipation.velocity",.01,1)
            _num(anticipation["gate"],f"{name}.harmonic_anticipation.gate",.05,2)

        pickup=t.get("pickup",{})
        _obj(pickup,f"{name}.pickup")
        unknown=set(pickup)-{"enabled","role","beats","degrees","rhythm","octave","velocity"}
        if unknown: _fail(f"{name}.pickup unknown field(s): {sorted(unknown)}")
        enabled=pickup.get("enabled",False)
        if not isinstance(enabled,bool): _fail(f"{name}.pickup.enabled must be boolean")
        if enabled:
            req={"role","beats","degrees","rhythm","octave","velocity"}
            missing=req-set(pickup)
            if missing: _fail(f"{name}.pickup missing fields: {sorted(missing)}")
            if pickup["role"] not in roles: _fail(f"{name}.pickup.role references unknown role")
            beats=_num(pickup["beats"],f"{name}.pickup.beats",1e-9,8)
            deg=_list(pickup["degrees"],f"{name}.pickup.degrees")
            rhy=_list(pickup["rhythm"],f"{name}.pickup.rhythm")
            if not deg or len(deg)!=len(rhy): _fail(f"{name}.pickup degrees/rhythm must be same non-zero length")
            if len(deg)>16: _fail(f"{name}.pickup supports at most 16 notes")
            for j,v in enumerate(deg): _integer(v,f"{name}.pickup.degrees[{j}]",-14,21)
            total=0.0
            for j,v in enumerate(rhy): total += _num(v,f"{name}.pickup.rhythm[{j}]",1e-9,8)
            if total > beats + 1e-9: _fail(f"{name}.pickup rhythm total exceeds pickup beats")
            _integer(pickup["octave"],f"{name}.pickup.octave",0,8)
            _num(pickup["velocity"],f"{name}.pickup.velocity",.01,1)

        bass=t.get("bass_approach",{"type":"none"})
        _obj(bass,f"{name}.bass_approach")
        unknown=set(bass)-{"type","beats","direction","steps","velocity"}
        if unknown: _fail(f"{name}.bass_approach unknown field(s): {sorted(unknown)}")
        kind=bass.get("type")
        if kind not in BASS_APPROACHES: _fail(f"{name}.bass_approach.type invalid")
        if kind != "none":
            req={"beats","velocity"}
            if kind in {"step","chromatic","scale"}: req|={"direction","steps"}
            missing=req-set(bass)
            if missing: _fail(f"{name}.bass_approach missing fields: {sorted(missing)}")
            _num(bass["beats"],f"{name}.bass_approach.beats",1e-9,8)
            _num(bass["velocity"],f"{name}.bass_approach.velocity",.01,1)
            if kind in {"step","chromatic","scale"}:
                if bass["direction"] not in {"below","above"}: _fail(f"{name}.bass_approach.direction invalid")
                _integer(bass["steps"],f"{name}.bass_approach.steps",1,8)

        cadence=t.get("cadence_extension",{})
        _obj(cadence,f"{name}.cadence_extension")
        unknown=set(cadence)-{"roles","beats"}
        if unknown: _fail(f"{name}.cadence_extension unknown field(s): {sorted(unknown)}")
        if cadence:
            if set(cadence)!={"roles","beats"}: _fail(f"{name}.cadence_extension requires roles and beats")
            vals=_list(cadence["roles"],f"{name}.cadence_extension.roles")
            if not vals or len(vals)!=len(set(vals)): _fail(f"{name}.cadence_extension.roles must be unique and non-empty")
            bad=set(vals)-roles
            if bad: _fail(f"{name}.cadence_extension unknown role(s): {sorted(bad)}")
            _num(cadence["beats"],f"{name}.cadence_extension.beats",1e-9,16)

        subtraction=t.get("texture_subtraction",{})
        _obj(subtraction,f"{name}.texture_subtraction")
        unknown=set(subtraction)-{"roles","beats"}
        if unknown: _fail(f"{name}.texture_subtraction unknown field(s): {sorted(unknown)}")
        if subtraction:
            if set(subtraction)!={"roles","beats"}: _fail(f"{name}.texture_subtraction requires roles and beats")
            vals=_list(subtraction["roles"],f"{name}.texture_subtraction.roles")
            if not vals or len(vals)!=len(set(vals)): _fail(f"{name}.texture_subtraction.roles must be unique and non-empty")
            bad=set(vals)-roles
            if bad: _fail(f"{name}.texture_subtraction unknown role(s): {sorted(bad)}")
            _num(subtraction["beats"],f"{name}.texture_subtraction.beats",1e-9,16)

        if "silence_beats" in t: _num(t["silence_beats"],f"{name}.silence_beats",0,8)

        prep=t.get("register_preparation",{})
        _obj(prep,f"{name}.register_preparation")
        bad=set(prep)-roles
        if bad: _fail(f"{name}.register_preparation unknown role(s): {sorted(bad)}")
        for role,cfg in prep.items():
            _obj(cfg,f"{name}.register_preparation.{role}")
            if set(cfg)!={"semitones","beats"}: _fail(f"{name}.register_preparation.{role} requires semitones and beats")
            _integer(cfg["semitones"],f"{name}.register_preparation.{role}.semitones",-24,24)
            _num(cfg["beats"],f"{name}.register_preparation.{role}.beats",1e-9,16)

        fill=t.get("rhythm_fill",{})
        _obj(fill,f"{name}.rhythm_fill")
        unknown=set(fill)-{"role","events"}
        if unknown: _fail(f"{name}.rhythm_fill unknown field(s): {sorted(unknown)}")
        if fill:
            if set(fill)!={"role","events"}: _fail(f"{name}.rhythm_fill requires role and events")
            if fill["role"] not in roles: _fail(f"{name}.rhythm_fill.role references unknown role")
            events=_list(fill["events"],f"{name}.rhythm_fill.events")
            if not events or len(events)>32: _fail(f"{name}.rhythm_fill.events must contain 1..32 events")
            for j,event in enumerate(events):
                en=f"{name}.rhythm_fill.events[{j}]"
                _obj(event,en)
                allowed_event={"offset_beats","drum","duration_beats","velocity","pan","articulation","strike_force","strike_position"}
                unknown_event=set(event)-allowed_event
                if unknown_event: _fail(f"{en} unknown field(s): {sorted(unknown_event)}")
                req={"offset_beats","drum","duration_beats","velocity"}
                missing=req-set(event)
                if missing: _fail(f"{en} missing fields: {sorted(missing)}")
                _num(event["offset_beats"],f"{en}.offset_beats",-8,-1e-12)
                if not isinstance(event["drum"],str) or not event["drum"]: _fail(f"{en}.drum must be non-empty string")
                _num(event["duration_beats"],f"{en}.duration_beats",1e-9,2)
                _num(event["velocity"],f"{en}.velocity",.01,1)
                if "pan" in event: _num(event["pan"],f"{en}.pan",-1,1)
                if "articulation" in event and (not isinstance(event["articulation"],str) or not event["articulation"]): _fail(f"{en}.articulation must be non-empty string")
                if "strike_force" in event: _num(event["strike_force"],f"{en}.strike_force",0,1)
                if "strike_position" in event: _num(event["strike_position"],f"{en}.strike_position",0,1)


def build_validation_context_from_composition(
    *,
    form: list[dict],
    role_ids,
    source_material_ids,
    beats_per_bar: float = 4.0,
) -> ExpressiveValidationContext:
    section_ids=[]
    section_spans={}
    cursor=0.0
    for i,sec in enumerate(form):
        if not isinstance(sec,dict) or "id" not in sec:
            _fail(f"form[{i}] must contain id")
        sid=str(sec["id"])
        if "start_bar" in sec:
            start=float(sec["start_bar"])*beats_per_bar
        else:
            start=cursor
        if "bars" not in sec:
            _fail(f"form[{i}] missing bars")
        end=start+float(sec["bars"])*beats_per_bar
        section_ids.append(sid)
        section_spans[sid]=(start,end)
        cursor=end
    return ExpressiveValidationContext(
        section_ids=tuple(section_ids),
        role_ids=tuple(role_ids),
        source_material_ids=tuple(source_material_ids),
        section_spans=section_spans,
    )


__all__=[
    "ExpressivePlanValidationError",
    "ExpressiveValidationContext",
    "ExpressiveScorePlan",
    "expressive_score_plan_from_dict",
    "expressive_score_plan_to_dict",
    "validate_expressive_score_plan",
    "build_validation_context_from_composition",
]
