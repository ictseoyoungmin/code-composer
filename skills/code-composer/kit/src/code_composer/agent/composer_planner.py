from dataclasses import dataclass, asdict
from copy import deepcopy

from .composition_brief import (
    CompositionBrief,
    brief_to_dict,
    validate_brief,
)
from ..audio.piano_design import resolve_piano_design
from ..presets import materialize_preset
from ..composition.motif_development import motif_identity_metrics


@dataclass(frozen=True)
class ComposerPlan:
    brief: CompositionBrief
    transport: dict
    tonal: dict
    form: dict
    materials: dict
    rhythm: dict
    transitions: dict
    orchestration: dict
    harmony: dict
    development: dict
    sound_palette: dict
    rationale: tuple[str, ...]


def compile_brief(seed_ir: dict, brief: CompositionBrief) -> ComposerPlan:
    """Compile an agent-authored musical brief into an executable IR plan.

    This function intentionally does not interpret natural language and does not map
    style words to presets. All musical judgments must already be explicit in `brief`.
    The compiler validates contracts, normalizes serializable structures, and preserves
    hard constraints.
    """
    validate_brief(brief, seed_ir)

    normalized_sections=[]
    start_bar=0
    for sec in brief.form['sections']:
        bars=int(sec['bars'])
        normalized_sections.append({
            'id':str(sec['id']),
            'start_bar':start_bar,
            'bars':bars,
            'energy':float(sec['energy']),
        })
        start_bar += bars
    section_ids=[s['id'] for s in normalized_sections]

    orchestration={
        'enabled': True,
        'default': deepcopy(brief.orchestration.get('default',{'foreground_mode':'none'})),
        'sections': deepcopy(brief.orchestration.get('sections',{})),
    }
    for sid in section_ids:
        orchestration['sections'].setdefault(sid, {'foreground_mode':'none'})

    harmony={
        'enabled': True,
        'default': {
            'colors': list(brief.harmony['colors']),
            'normalize_density': bool(brief.harmony.get('normalize_density',True)),
            'motion_weight': float(brief.harmony.get('motion_weight',1.0)),
            'center_weight': float(brief.harmony.get('center_weight',0.22)),
        },
        'sections': deepcopy(brief.harmony.get('sections',{})),
    }
    for sid in section_ids:
        harmony['sections'].setdefault(sid,{
            'colors': list(brief.harmony['colors']),
            'cadence_color': brief.harmony.get('cadence_color',brief.harmony['colors'][-1]),
        })

    development={
        'enabled': True,
        'families': deepcopy(brief.development.get('families',{})),
        'default': deepcopy(brief.development.get('default',{'stage':'develop'})),
        'sections': deepcopy(brief.development.get('sections',{})),
    }
    for sid in section_ids:
        development['sections'].setdefault(sid,{'stage':'develop'})

    return ComposerPlan(
        brief=brief,
        transport=deepcopy(brief.transport),
        tonal=deepcopy(brief.tonal),
        form={'sections':normalized_sections},
        materials=deepcopy(brief.materials),
        rhythm=deepcopy(brief.rhythm),
        transitions=deepcopy(brief.transitions),
        orchestration=orchestration,
        harmony=harmony,
        development=development,
        sound_palette=deepcopy(brief.sound_palette),
        rationale=tuple(brief.rationale),
    )


def apply_composer_plan(seed_ir: dict, plan: ComposerPlan) -> dict:
    out=deepcopy(seed_ir)

    out['transport'].update(plan.transport)
    out['tonal'].update(plan.tonal)
    out['hard_constraints']=deepcopy(plan.brief.hard_constraints)

    out['form']=deepcopy(plan.form['sections'])

    mats=out.setdefault('materials',{})
    mats.setdefault('motifs',{})['main']={
        'intervals': list(plan.materials['motif']),
        'rhythm': list(plan.materials['motif_rhythm']),
    }
    for variant_id,spec in plan.materials.get('motif_variants',{}).items():
        metrics=motif_identity_metrics(
            plan.materials['motif'],plan.materials['motif_rhythm'],
            spec['intervals'],spec['rhythm'],
        )
        mats['motifs'][variant_id]={
            'intervals':list(spec['intervals']),
            'rhythm':[float(x) for x in spec['rhythm']],
            'source_motif_id':'main',
            'identity':metrics,
            'identity_floor':float(spec['identity_floor']),
            'identity_hard_min':(
                float(spec['identity_hard_min']) if spec.get('identity_hard_min') is not None else None
            ),
            'identity_target_met':bool(metrics['score'] + 1e-12 >= float(spec['identity_floor'])),
        }
    mats.setdefault('progressions',{})['home']={
        'degrees': list(plan.materials['progression'])
    }
    for variant_id,spec in plan.materials.get('progression_variants',{}).items():
        mats['progressions'][variant_id]={
            'degrees':list(spec['degrees']),
            'source_progression_id':'home',
        }
    mats.setdefault('rhythms',{})['composer']=deepcopy(plan.rhythm['groove'])

    arrangement=out.setdefault('arrangement',{})
    arrangement['motif']='main'
    for role in arrangement.get('roles',{}).values():
        source=role.get('source')
        if isinstance(source,dict) and 'progression' in source:
            source['progression']='home'

    rcfg=out.setdefault('rhythm_engine',{})
    rcfg['groove']='composer'
    rcfg['steps_per_bar']=int(plan.rhythm['groove']['steps_per_bar'])
    rcfg['swing']=float(plan.rhythm.get('swing',0.0))
    rcfg['humanize_beats']=float(plan.rhythm.get('humanize_beats',0.0))
    rcfg['velocity_jitter']=float(plan.rhythm.get('velocity_jitter',0.0))
    rcfg['fill_probability']=float(plan.rhythm.get('fill_probability',0.65))
    rcfg['bass_coupling']=float(plan.rhythm.get('bass_coupling',0.75))
    rcfg['section_profiles']=deepcopy(plan.rhythm.get('section_profiles',{}))
    for sec in out.get('form',[]):
        rcfg['section_profiles'].setdefault(sec['id'],{
            'density':0.75,'kick':0.85,'snare':0.80,'hat':0.76,'fill':0.40
        })

    profiles=arrangement.setdefault('profiles',{})
    for sid,cfg in plan.transitions.items():
        p=profiles.setdefault(sid,{})
        p['entry_gain']=float(cfg.get('entry_gain',1.0))
        p['entry_soften_beats']=float(cfg.get('entry_soften_beats',0.0))

    form=out.get('form',[])
    index={sec['id']:i for i,sec in enumerate(form)}
    for target,cfg in plan.transitions.items():
        i=index.get(target)
        if i is None or i<=0:
            continue
        prev=form[i-1]['id']
        pp=rcfg['section_profiles'].setdefault(prev,{
            'density':0.75,'kick':0.85,'snare':0.80,'hat':0.76,'fill':0.40
        })
        if 'pre_fill' in cfg:
            pp['fill']=max(float(pp.get('fill',0.0)),float(cfg['pre_fill']))

    # Sound palette is agent-authored. The compiler only validates and routes patches
    # to the instrument IDs already owned by arrangement roles.
    palette_roles=plan.sound_palette.get('roles',{}) if isinstance(plan.sound_palette,dict) else {}
    instruments=out.setdefault('instruments',{})
    for role,spec in palette_roles.items():
        role_cfg=arrangement.get('roles',{}).get(role,{})
        instrument_id=role_cfg.get('instrument')
        if instrument_id is None:
            continue
        if 'preset_id' in spec:
            patch=materialize_preset(
                str(spec['preset_id']),
                version=spec.get('preset_version'),
                patch_overrides=spec.get('patch_overrides'),
                role=role,
            )
        else:
            patch=deepcopy(spec['patch'])
        if isinstance(patch,dict) and (patch.get('kind')=='piano' or 'piano_design' in patch):
            patch=resolve_piano_design(patch)
        instruments[instrument_id]=patch

    out['sound_palette_resolved']=deepcopy(plan.sound_palette)
    out['orchestration_grammar']=deepcopy(plan.orchestration)
    out['harmonic_grammar']=deepcopy(plan.harmony)
    out['arrangement_development']=deepcopy(plan.development)
    out['composer_plan']={
        'source':'agent_authored_composition_brief',
        'brief':brief_to_dict(plan.brief),
        'rationale':list(plan.rationale),
    }
    return out


def plan_to_dict(plan: ComposerPlan) -> dict:
    return {
        'brief':brief_to_dict(plan.brief),
        'transport':deepcopy(plan.transport),
        'tonal':deepcopy(plan.tonal),
        'form':deepcopy(plan.form),
        'materials':deepcopy(plan.materials),
        'rhythm':deepcopy(plan.rhythm),
        'transitions':deepcopy(plan.transitions),
        'orchestration':deepcopy(plan.orchestration),
        'harmony':deepcopy(plan.harmony),
        'development':deepcopy(plan.development),
        'sound_palette':deepcopy(plan.sound_palette),
        'rationale':list(plan.rationale),
    }


__all__=['ComposerPlan','compile_brief','apply_composer_plan','plan_to_dict']
