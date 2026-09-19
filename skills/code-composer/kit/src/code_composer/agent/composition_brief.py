from dataclasses import dataclass, asdict
from copy import deepcopy

from ..core.theory import NOTE_TO_PC, SCALES
from ..composition.harmonic_grammar import COLOR_DEGREE_OFFSETS
from ..composition.orchestration import VALID_FOREGROUND_MODES
from ..audio.engines import validate_authoring_patch, InstrumentEngineValidationError
from ..presets import materialize_preset, PresetError
from ..validation_contracts import (
    ContractValidationError,
    validate_transition_map,
    validate_development_config,
    validate_brief_harmony,
    validate_orchestration_config,
    validate_brief_rhythm,
)
from ..core.constraints import (
    HARD_CONSTRAINT_KEYS, FORBIDDEN_ROLE_NAMES, HardConstraintError,
    validate_hard_constraints_dict,
)


PITCHED_SOUND_ROLES={'lead','topline','pad','bass','arp'}
SOUND_ROLES=PITCHED_SOUND_ROLES | {'drums'}
WAVEFORMS={'sine','saw','square','triangle'}
FILTER_TYPES={'none','lowpass','highpass','bandpass'}
WAVESHAPERS={'none','tanh','softclip'}


@dataclass(frozen=True)
class CompositionBrief:
    source_prompt: str
    concept: str
    hard_constraints: dict
    transport: dict
    tonal: dict
    form: dict
    materials: dict
    rhythm: dict
    orchestration: dict
    harmony: dict
    development: dict
    transitions: dict
    sound_palette: dict
    rationale: tuple[str, ...] = ()


class BriefValidationError(ValueError):
    pass


def brief_from_dict(data: dict) -> CompositionBrief:
    required = (
        'source_prompt','concept','hard_constraints','transport','tonal','form',
        'materials','rhythm','orchestration','harmony','development','transitions'
    )
    missing=[k for k in required if k not in data]
    if missing:
        raise BriefValidationError(f'missing brief fields: {missing}')
    return CompositionBrief(
        source_prompt=str(data['source_prompt']),
        concept=str(data['concept']),
        hard_constraints=deepcopy(data['hard_constraints']),
        transport=deepcopy(data['transport']),
        tonal=deepcopy(data['tonal']),
        form=deepcopy(data['form']),
        materials=deepcopy(data['materials']),
        rhythm=deepcopy(data['rhythm']),
        orchestration=deepcopy(data['orchestration']),
        harmony=deepcopy(data['harmony']),
        development=deepcopy(data['development']),
        transitions=deepcopy(data['transitions']),
        sound_palette=deepcopy(data.get('sound_palette',{'roles':{}})),
        rationale=tuple(data.get('rationale',())),
    )


def brief_to_dict(brief: CompositionBrief) -> dict:
    out=asdict(brief)
    out['rationale']=list(brief.rationale)
    return out


def _num(v, name, lo, hi):
    try:
        x=float(v)
    except Exception as exc:
        raise BriefValidationError(f'{name} must be numeric') from exc
    if not (lo <= x <= hi):
        raise BriefValidationError(f'{name} outside [{lo},{hi}]')
    return x




def _validate_pitched_patch(role, patch):
    try:
        validate_authoring_patch(role,patch)
    except InstrumentEngineValidationError as exc:
        raise BriefValidationError(str(exc)) from exc


def _validate_drum_patch(patch):
    if not isinstance(patch,dict):
        raise BriefValidationError('sound_palette.drums.patch must be an object')
    if patch.get('kind','percussion') != 'percussion':
        raise BriefValidationError('drums patch kind must be percussion')
    graph=patch.get('drum_graph',{})
    if not isinstance(graph,dict):
        raise BriefValidationError('drums.drum_graph must be an object')
    for name in ('kick','snare','hat'):
        if name not in graph or not isinstance(graph[name],dict):
            raise BriefValidationError(f'drums.drum_graph requires {name}')

    k=graph['kick']
    _num(k.get('pitch_start_hz',165),'kick.pitch_start_hz',30,800)
    _num(k.get('pitch_end_hz',48),'kick.pitch_end_hz',20,180)
    _num(k.get('pitch_decay_s',.045),'kick.pitch_decay_s',.002,.5)
    _num(k.get('body_decay_s',.095),'kick.body_decay_s',.01,1.5)
    _num(k.get('sub_decay_s',.14),'kick.sub_decay_s',.01,2.0)
    for key in ('body_gain','sub_gain','click_gain','output_gain'):
        _num(k.get(key,0),f'kick.{key}',0,2)
    _num(k.get('click_hz',2200),'kick.click_hz',100,12000)
    _num(k.get('drive',1.1),'kick.drive',.1,5)

    s=graph['snare']
    for key,lo,hi,default in (
        ('body_hz',60,700,185),('body2_hz',80,1600,335),
        ('noise_low_hz',100,12000,1200),('noise_high_hz',500,20000,9000),
        ('crack_hz',300,12000,2700),('lowpass_hz',500,20000,10500)):
        _num(s.get(key,default),f'snare.{key}',lo,hi)
    if float(s.get('noise_low_hz',1200)) >= float(s.get('noise_high_hz',9000)):
        raise BriefValidationError('snare noise_low_hz must be below noise_high_hz')
    for key in ('body_gain','body2_gain','noise_gain','crack_gain','output_gain'):
        _num(s.get(key,0),f'snare.{key}',0,2)
    for key in ('body_decay_s','noise_decay_s','crack_decay_s'):
        _num(s.get(key,.05),f'snare.{key}',.001,2)
    _num(s.get('drive',1.08),'snare.drive',.1,5)

    h=graph['hat']
    freqs=h.get('metal_freqs',[])
    gains=h.get('metal_gains',[])
    if not isinstance(freqs,list) or not (2 <= len(freqs) <= 8):
        raise BriefValidationError('hat.metal_freqs must contain 2..8 frequencies')
    if not isinstance(gains,list) or len(gains)!=len(freqs):
        raise BriefValidationError('hat.metal_gains must match metal_freqs')
    for i,f in enumerate(freqs): _num(f,f'hat.metal_freqs[{i}]',1000,20000)
    for i,g in enumerate(gains): _num(g,f'hat.metal_gains[{i}]',0,2)
    for key in ('metal_gain','noise_gain','output_gain'):
        _num(h.get(key,0),f'hat.{key}',0,2)
    _num(h.get('decay_s',.03),'hat.decay_s',.002,1)
    hp=_num(h.get('noise_highpass_hz',5200),'hat.noise_highpass_hz',100,19000)
    lp=_num(h.get('noise_lowpass_hz',15000),'hat.noise_lowpass_hz',500,20000)
    if hp >= lp: raise BriefValidationError('hat noise_highpass_hz must be below noise_lowpass_hz')
    _num(h.get('output_highpass_hz',4300),'hat.output_highpass_hz',100,19000)
    _num(h.get('drive',1.04),'hat.drive',.1,5)

    try:
        validate_authoring_patch('drums', patch)
    except InstrumentEngineValidationError as exc:
        raise BriefValidationError(str(exc)) from exc


def _validate_sound_palette(brief, seed_ir):
    palette=brief.sound_palette or {'roles':{}}
    if not isinstance(palette,dict):
        raise BriefValidationError('sound_palette must be an object')
    roles=palette.get('roles',{})
    if not isinstance(roles,dict):
        raise BriefValidationError('sound_palette.roles must be an object')
    unknown=set(roles)-SOUND_ROLES
    if unknown:
        raise BriefValidationError(f'unknown sound palette roles: {sorted(unknown)}')
    available=set(seed_ir.get('arrangement',{}).get('roles',{}))
    missing=set(roles)-available
    if missing:
        raise BriefValidationError(f'sound palette role(s) unavailable in seed arrangement: {sorted(missing)}')
    for role,spec in roles.items():
        if not isinstance(spec,dict):
            raise BriefValidationError(f'sound_palette.{role} must be an object')
        patch=spec.get('patch')
        preset_id=spec.get('preset_id')
        if (patch is None) == (preset_id is None):
            raise BriefValidationError(
                f'sound_palette.{role} requires exactly one of patch or preset_id'
            )
        if preset_id is not None:
            try:
                patch=materialize_preset(
                    str(preset_id),
                    version=spec.get('preset_version'),
                    patch_overrides=spec.get('patch_overrides'),
                    role=role,
                )
            except PresetError as exc:
                raise BriefValidationError(str(exc)) from exc
        elif 'preset_version' in spec or 'patch_overrides' in spec:
            raise BriefValidationError(
                f'sound_palette.{role}: preset_version/patch_overrides require preset_id'
            )
        if role=='drums':
            _validate_drum_patch(patch)
        else:
            _validate_pitched_patch(role,patch)


def _validate_hard_constraints(brief):
    try:
        validate_hard_constraints_dict(brief.hard_constraints)
    except HardConstraintError as exc:
        raise BriefValidationError(str(exc)) from exc

def _validate_roles(brief, section_ids):
    sections=brief.orchestration.get('sections',{})
    for sid,cfg in sections.items():
        if sid not in section_ids:
            raise BriefValidationError(f'orchestration references unknown section: {sid}')
        mode=cfg.get('foreground_mode','none')
        if mode not in VALID_FOREGROUND_MODES - {'legacy'}:
            raise BriefValidationError(f'unsupported foreground_mode: {mode}')
        sparse=cfg.get('sparse_role','lead')
        if mode=='sparse' and sparse not in {'lead','topline'}:
            raise BriefValidationError('sparse_role must be lead or topline')

    forbidden=set(brief.hard_constraints.get('forbidden_roles',[]))
    if 'lead' in forbidden or 'topline' in forbidden:
        for sid,cfg in sections.items():
            mode=cfg.get('foreground_mode','none')
            if 'lead' in forbidden and mode in {'lead','both'}:
                raise BriefValidationError(f'hard constraint forbids lead in section {sid}')
            if 'topline' in forbidden and mode in {'topline','both'}:
                raise BriefValidationError(f'hard constraint forbids topline in section {sid}')
            if mode=='sparse' and cfg.get('sparse_role','lead') in forbidden:
                raise BriefValidationError(f'hard constraint forbids sparse role in section {sid}')


def validate_brief(brief: CompositionBrief, seed_ir: dict) -> None:
    _validate_hard_constraints(brief)
    bpm=float(brief.transport.get('bpm',0))
    bpb=int(brief.transport.get('beats_per_bar',0))
    if not (40 <= bpm <= 220):
        raise BriefValidationError('bpm must be in [40, 220]')
    if not (2 <= bpb <= 12):
        raise BriefValidationError('beats_per_bar must be in [2, 12]')

    root=brief.tonal.get('root')
    scale=brief.tonal.get('scale')
    if root not in NOTE_TO_PC:
        raise BriefValidationError(f'unsupported tonal root: {root}')
    if scale not in SCALES:
        raise BriefValidationError(f'unsupported scale: {scale}')

    progression=list(brief.materials.get('progression',[]))
    motif=list(brief.materials.get('motif',[]))
    motif_rhythm=list(brief.materials.get('motif_rhythm',[]))
    if len(progression)<2 or any(not isinstance(x,int) or x<1 or x>14 for x in progression):
        raise BriefValidationError('progression must contain scale degrees 1..14')
    if len(motif)<3 or any(not isinstance(x,int) for x in motif):
        raise BriefValidationError('motif must contain at least 3 integer scale offsets')
    if len(motif_rhythm)!=len(motif) or any(float(x)<=0 for x in motif_rhythm):
        raise BriefValidationError('motif_rhythm must match motif length and be positive')

    groove=brief.rhythm.get('groove',{})
    steps=int(groove.get('steps_per_bar',0))
    if steps<=0:
        raise BriefValidationError('groove.steps_per_bar must be positive')
    for role in ('kick','snare','hat'):
        cells=list(groove.get('roles',{}).get(role,[]))
        if len(cells)!=steps:
            raise BriefValidationError(f'{role} groove must have {steps} cells')
        if any(float(x)<0 or float(x)>1.5 for x in cells):
            raise BriefValidationError(f'{role} groove cell outside [0,1.5]')

    sections=list(brief.form.get('sections',[]))
    if not sections:
        raise BriefValidationError('brief form requires at least one section')
    ids=[s.get('id') for s in sections]
    if any(not isinstance(sid,str) or not sid for sid in ids):
        raise BriefValidationError('every form section requires a non-empty id')
    if len(set(ids)) != len(ids):
        raise BriefValidationError('form section ids must be unique')
    for sec in sections:
        bars=int(sec.get('bars',0))
        energy=float(sec.get('energy',-1))
        if bars <= 0:
            raise BriefValidationError(f"section {sec.get('id')}: bars must be positive")
        if not (0 <= energy <= 1):
            raise BriefValidationError(f"section {sec.get('id')}: energy must be in [0,1]")
    section_ids=set(ids)

    try:
        validate_brief_rhythm(brief.rhythm, section_ids)
        validate_orchestration_config(brief.orchestration, section_ids, runtime=False)
        validate_brief_harmony(brief.harmony, section_ids)
        validate_development_config(brief.development, section_ids, runtime=False)
        validate_transition_map(brief.transitions, section_ids)
    except ContractValidationError as exc:
        raise BriefValidationError(str(exc)) from exc

    _validate_roles(brief, section_ids)
    _validate_sound_palette(brief, seed_ir)

    colors=brief.harmony.get('colors',[])
    if not colors or any(c not in COLOR_DEGREE_OFFSETS for c in colors):
        raise BriefValidationError(f'harmony colors must be one of {sorted(COLOR_DEGREE_OFFSETS)}')

    dev=brief.development.get('sections',{})
    if set(dev)-section_ids:
        raise BriefValidationError('development references unknown section')
    trans=brief.transitions
    if set(trans)-section_ids:
        raise BriefValidationError('transition references unknown section')

    exact_bpm=brief.hard_constraints.get('bpm')
    if exact_bpm is not None and float(exact_bpm)!=bpm:
        raise BriefValidationError('hard bpm constraint conflicts with transport.bpm')
    exact_root=brief.hard_constraints.get('root')
    exact_scale=brief.hard_constraints.get('scale')
    if exact_root is not None and exact_root != root:
        raise BriefValidationError('hard root constraint conflicts with tonal.root')
    if exact_scale is not None and exact_scale != scale:
        raise BriefValidationError('hard scale constraint conflicts with tonal.scale')


__all__=[
    'CompositionBrief','BriefValidationError','brief_from_dict','brief_to_dict','validate_brief',
    'PITCHED_SOUND_ROLES','SOUND_ROLES','HARD_CONSTRAINT_KEYS','FORBIDDEN_ROLE_NAMES',
    'WAVEFORMS','FILTER_TYPES','WAVESHAPERS'
]
