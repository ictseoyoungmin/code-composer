from copy import deepcopy


class PianoDesignError(ValueError):
    pass


FAMILY_OPTIONS={'acoustic','electric'}

# Backward-compatible acoustic category names.
CATEGORY_OPTIONS = {
    'body': {'concert_grand', 'studio_grand', 'upright'},
    'hammer': {'soft_felt', 'medium_felt', 'dense_felt'},
    'stringing': {'concert', 'compact', 'aged'},
    'soundboard': {'open_board', 'balanced_board', 'dry_board'},
    'perspective': {'player', 'audience', 'close'},
}
DEFAULT_CATEGORIES = {
    'body': 'studio_grand',
    'hammer': 'medium_felt',
    'stringing': 'concert',
    'soundboard': 'balanced_board',
    'perspective': 'player',
}

ELECTRIC_CATEGORY_OPTIONS={
    'mechanism': {'tine','reed','digital_fm'},
    'pickup': {'mellow','neutral','bright'},
    'amp': {'direct','clean_combo','warm_combo'},
    'modulation': {'none','tremolo','chorus'},
    'perspective': {'centered','wide','close'},
}
ELECTRIC_DEFAULT_CATEGORIES={
    'mechanism':'tine',
    'pickup':'neutral',
    'amp':'clean_combo',
    'modulation':'tremolo',
    'perspective':'centered',
}


# Absolute numeric controls. Category labels never encode subjective intensity.
ACOUSTIC_CONTROL_SPECS = {
    'max_partials': ('strings.max_partials', 3, 28, int),
    'base_decay_s': ('strings.base_decay_s', 0.15, 12.0, float),
    'decay_keytrack': ('strings.decay_keytrack', 0.0, 2.0, float),
    'partial_decay_power': ('strings.partial_decay_power', 0.0, 2.0, float),
    'spectral_rolloff': ('strings.spectral_rolloff', 0.5, 3.0, float),
    'velocity_brightness': ('strings.velocity_brightness', 0.0, 2.0, float),
    'inharmonicity': ('strings.inharmonicity', 0.0, 0.005, float),
    'detune_cents': ('strings.detune_cents', 0.0, 5.0, float),
    'stereo_width': ('strings.stereo_width', 0.0, 1.0, float),
    'low_strings': ('strings.low_strings', 1, 3, int),
    'mid_strings': ('strings.mid_strings', 1, 3, int),
    'high_strings': ('strings.high_strings', 1, 3, int),
    'hammer_gain': ('hammer.gain', 0.0, 0.8, float),
    'hammer_noise_gain': ('hammer.noise_gain', 0.0, 0.5, float),
    'hammer_decay_s': ('hammer.decay_s', 0.001, 0.2, float),
    'hammer_low_cutoff_hz': ('hammer.low_cutoff_hz', 20.0, 18000.0, float),
    'hammer_soft_high_cutoff_hz': ('hammer.soft_high_cutoff_hz', 100.0, 20000.0, float),
    'hammer_hard_high_cutoff_hz': ('hammer.hard_high_cutoff_hz', 100.0, 20000.0, float),
    'release_s': ('damper.release_s', 0.02, 5.0, float),
    'pedal_release_s': ('damper.pedal_release_s', 0.02, 8.0, float),
    'release_floor_db': ('damper.release_floor_db', -120.0, -36.0, float),
    'damper_contact_spread_s': ('damper.contact_spread_s', 0.0, 0.020, float),
    'damper_string_release_spread': ('damper.string_release_spread', 0.0, 0.25, float),
    'resonance_gain': ('resonance.gain', 0.0, 0.4, float),
    'resonance_pedal_gain': ('resonance.pedal_gain', 0.0, 0.5, float),
    'resonance_decay_s': ('resonance.decay_s', 0.05, 8.0, float),
    'soundboard_gain': ('soundboard.gain', 0.0, 0.25, float),
    'soundboard_pedal_gain': ('soundboard.pedal_gain', 0.0, 0.35, float),
    'soundboard_cross': ('soundboard.cross', 0.0, 1.0, float),
    'bridge_coupling': ('bridge.coupling', 0.0, 1.0, float),
    'bridge_low_cutoff_hz': ('bridge.low_cutoff_hz', 20.0, 2000.0, float),
    'bridge_high_cutoff_hz': ('bridge.high_cutoff_hz', 1000.0, 20000.0, float),
    'modal_gain': ('soundboard.modal_gain', 0.0, 0.4, float),
    'modal_decay_scale': ('soundboard.modal_decay_scale', 0.2, 4.0, float),
    'key_noise_gain': ('mechanics.key_noise_gain', 0.0, 0.25, float),
    'damper_noise_gain': ('mechanics.damper_noise_gain', 0.0, 0.25, float),
    'body_soft_cutoff_hz': ('body_filter.soft_cutoff_hz', 100.0, 19000.0, float),
    'body_hard_cutoff_hz': ('body_filter.hard_cutoff_hz', 200.0, 20000.0, float),
    'output_gain': ('output_gain', 0.0, 2.0, float),
    'strike_phase_jitter_rad': ('strike_identity.phase_jitter_rad', 0.0, 0.8, float),
    'strike_unison_phase_jitter_rad': ('strike_identity.unison_phase_jitter_rad', 0.0, 0.5, float),
    'strike_partial_phase_jitter_rad': ('strike_identity.partial_phase_jitter_rad', 0.0, 0.25, float),
    'strike_hammer_noise_mix': ('strike_identity.hammer_noise_mix', 0.0, 1.0, float),
    'strike_hammer_gain_variation': ('strike_identity.hammer_gain_variation', 0.0, 0.20, float),
    'strike_hammer_decay_variation': ('strike_identity.hammer_decay_variation', 0.0, 0.30, float),
    'unison_partial_mistune_cents': ('strings.unison_decoherence.partial_mistune_cents', 0.0, 0.25, float),
    'unison_inharmonicity_spread': ('strings.unison_decoherence.inharmonicity_spread', 0.0, 0.12, float),
    'unison_decay_spread': ('strings.unison_decoherence.decay_spread', 0.0, 0.20, float),
    'unison_level_spread': ('strings.unison_decoherence.level_spread', 0.0, 0.12, float),
    'unison_decoherence_start_midi': ('strings.unison_decoherence.start_midi', 21, 108, int),
}
# Historical export retained for callers/tests; it means acoustic direct controls.
CONTROL_SPECS=ACOUSTIC_CONTROL_SPECS

ELECTRIC_CONTROL_SPECS={
    'decay_s':('tone.decay_s',0.15,12.0,float),
    'release_s':('tone.release_s',0.02,6.0,float),
    'bell_gain':('tone.bell_gain',0.0,1.5,float),
    'bark_gain':('tone.bark_gain',0.0,1.5,float),
    'velocity_brightness':('tone.velocity_brightness',0.0,3.0,float),
    'inharmonicity':('tone.inharmonicity',0.0,0.02,float),
    'pickup_drive':('pickup.drive',0.1,8.0,float),
    'pickup_cutoff_hz':('pickup.cutoff_hz',200.0,20000.0,float),
    'amp_drive':('amp.drive',0.1,8.0,float),
    'amp_cutoff_hz':('amp.cutoff_hz',200.0,20000.0,float),
    'tremolo_rate_hz':('modulation.rate_hz',0.05,15.0,float),
    'tremolo_depth':('modulation.depth',0.0,1.0,float),
    'chorus_rate_hz':('modulation.chorus_rate_hz',0.05,10.0,float),
    'chorus_depth_cents':('modulation.chorus_depth_cents',0.0,30.0,float),
    'stereo_width':('stereo_width',0.0,1.0,float),
    'key_noise_gain':('mechanics.key_noise_gain',0.0,0.25,float),
    'output_gain':('output_gain',0.0,2.0,float),
}


def _base_acoustic_graph():
    return {
        'strings': {
            'max_partials': 16, 'base_decay_s': 3.2, 'decay_keytrack': 0.55,
            'partial_decay_power': 0.58, 'spectral_rolloff': 1.36,
            'velocity_brightness': 0.72, 'inharmonicity': 0.00016,
            'detune_cents': 0.65, 'release_detune_damping_s': 0.070,
            'stereo_width': 0.72,
            'low_strings': 1, 'mid_strings': 2, 'high_strings': 3,
            'low_split_midi': 43, 'high_split_midi': 61, 'attack_s': 0.0018,
            # Disabled by default.  S28-G opt-in treble presets may add tiny
            # deterministic string/partial asymmetry while preserving 3-string
            # unison and the authored mean detune.
            'unison_decoherence': {
                'partial_mistune_cents': 0.0, 'inharmonicity_spread': 0.0,
                'decay_spread': 0.0, 'level_spread': 0.0, 'start_midi': 61,
            },
        },
        'hammer': {
            'gain': 0.11, 'noise_gain': 0.055, 'decay_s': 0.018, 'attack_s': 0.0005,
            'low_cutoff_hz': 700.0, 'soft_high_cutoff_hz': 3200.0,
            'hard_high_cutoff_hz': 11500.0, 'tonal_gain': 0.035,
            'tonal_harmonic': 7.0, 'seed': 193,
        },
        'damper': {
            'release_s': 0.20, 'pedal_release_s': 1.65,
            'release_floor_db': -72.0,
            'contact_spread_s': 0.0045,
            'string_release_spread': 0.08,
        },
        'resonance': {
            'gain': 0.025, 'pedal_gain': 0.075, 'decay_s': 2.4,
            'no_pedal_gain_scale':0.22, 'no_pedal_decay_scale':0.30,
            'ratios': [1.0, 2.0, 3.0, 4.0], 'weights': [1.0, 0.36, 0.20, 0.10],
        },
        'bridge': {'coupling':0.30,'low_cutoff_hz':55.0,'high_cutoff_hz':12500.0},
        'soundboard': {
            'model':'modal',
            'gain': 0.014, 'pedal_gain': 0.034, 'cross': 0.30,
            'modal_gain':0.050, 'modal_decay_scale':1.0, 'no_pedal_modal_decay_scale':0.10,
            'modes_hz':[92.0,137.0,203.0,296.0,421.0,617.0,895.0,1290.0],
            'mode_weights':[1.0,.82,.72,.60,.48,.36,.26,.17],
            'mode_decays':[1.45,1.32,1.18,1.04,.88,.72,.56,.42],
            # Kept as a very low secondary diffusion layer.
            'taps_ms': [13.1, 21.7, 34.9], 'weights': [1.0, 0.45, 0.20],
        },
        'mechanics':{'key_noise_gain':0.012,'damper_noise_gain':0.010,'seed':271},
        # Disabled by default so every historical piano preset remains byte-exact.
        # New opt-in presets can author bounded deterministic per-strike variation.
        'strike_identity':{
            'phase_jitter_rad':0.0, 'unison_phase_jitter_rad':0.0,
            'partial_phase_jitter_rad':0.0, 'hammer_noise_mix':0.0,
            'hammer_gain_variation':0.0, 'hammer_decay_variation':0.0,
        },
        'body_filter': {'soft_cutoff_hz': 3800.0, 'hard_cutoff_hz': 14500.0},
        'declick_ms': 0.35, 'output_gain': 0.62,
    }


def _base_electric_graph():
    return {
        'tone':{
            'mechanism':'tine','decay_s':2.7,'release_s':0.55,
            'bell_gain':0.34,'bark_gain':0.16,'velocity_brightness':1.0,
            'inharmonicity':0.0018,
        },
        'pickup':{'drive':1.15,'cutoff_hz':8200.0,'highpass_hz':80.0},
        'amp':{'drive':1.08,'cutoff_hz':7600.0,'lowpass_hz':7600.0},
        'modulation':{
            'type':'tremolo','rate_hz':4.6,'depth':0.18,
            'chorus_rate_hz':0.55,'chorus_depth_cents':4.5,
        },
        'mechanics':{'key_noise_gain':0.008,'seed':419},
        'stereo_width':0.55,
        'output_gain':0.64,
    }


def _merge(dst, src):
    for key,value in src.items():
        if isinstance(value,dict) and isinstance(dst.get(key),dict):
            _merge(dst[key],value)
        else:
            dst[key]=deepcopy(value)


ACOUSTIC_CATEGORY_BASELINES={
    'body':{
        'concert_grand':{
            'strings':{'base_decay_s':4.45,'stereo_width':0.90},
            'bridge':{'coupling':0.38,'high_cutoff_hz':14500.0},
            'resonance':{'gain':0.030,'pedal_gain':0.090,'decay_s':3.0},
            'soundboard':{'modal_gain':0.068,'modal_decay_scale':1.18,'cross':0.38,
                          'modes_hz':[88,132,196,287,409,594,862,1245]},
            'mechanics':{'key_noise_gain':0.009,'damper_noise_gain':0.009},
            'body_filter':{'soft_cutoff_hz':4200.0,'hard_cutoff_hz':15800.0},
        },
        'studio_grand':{},
        'upright':{
            'strings':{'base_decay_s':2.55,'stereo_width':0.46,'decay_keytrack':0.70},
            'bridge':{'coupling':0.28,'high_cutoff_hz':10800.0},
            'resonance':{'gain':0.016,'pedal_gain':0.045,'decay_s':1.7},
            'soundboard':{'modal_gain':0.040,'modal_decay_scale':0.72,'cross':0.18,
                          'modes_hz':[104,154,226,332,486,708,1034,1506]},
            'mechanics':{'key_noise_gain':0.024,'damper_noise_gain':0.021},
            'body_filter':{'soft_cutoff_hz':3250.0,'hard_cutoff_hz':11200.0},
        },
    },
    'hammer':{
        'soft_felt':{
            'hammer':{'noise_gain':0.030,'decay_s':0.024,'soft_high_cutoff_hz':2300.0,
                      'hard_high_cutoff_hz':7600.0,'tonal_gain':0.020},
            'body_filter':{'soft_cutoff_hz':2950.0},
        },
        'medium_felt':{},
        'dense_felt':{
            'hammer':{'noise_gain':0.078,'decay_s':0.013,'soft_high_cutoff_hz':3900.0,
                      'hard_high_cutoff_hz':15000.0,'tonal_gain':0.047},
            'body_filter':{'hard_cutoff_hz':17000.0},
        },
    },
    'stringing':{
        'concert':{},
        'compact':{'strings':{'low_strings':1,'mid_strings':2,'high_strings':2,'max_partials':14,
                              'inharmonicity':0.00024,'detune_cents':0.82}},
        'aged':{'strings':{'low_strings':1,'mid_strings':2,'high_strings':3,'max_partials':15,
                           'inharmonicity':0.00036,'detune_cents':1.45,'spectral_rolloff':1.52}},
    },
    'soundboard':{
        'open_board':{'soundboard':{'modal_gain':0.078,'modal_decay_scale':1.22,'cross':0.42},
                      'resonance':{'gain':0.033,'decay_s':3.15}},
        'balanced_board':{},
        'dry_board':{'soundboard':{'modal_gain':0.025,'modal_decay_scale':0.58,'cross':0.12,
                                   'gain':0.004,'pedal_gain':0.010},
                     'resonance':{'gain':0.010,'pedal_gain':0.020,'decay_s':1.35}},
    },
    'perspective':{
        'player':{},
        'audience':{'strings':{'stereo_width':0.60},'soundboard':{'cross':0.46}},
        'close':{'strings':{'stereo_width':0.40},'soundboard':{'modal_gain':0.026,'cross':0.18},
                 'hammer':{'gain':0.135},'mechanics':{'key_noise_gain':0.020}},
    },
}
# Historical name retained.
CATEGORY_BASELINES=ACOUSTIC_CATEGORY_BASELINES

ELECTRIC_CATEGORY_BASELINES={
    'mechanism':{
        'tine':{'tone':{'mechanism':'tine','decay_s':2.8,'bell_gain':0.38,'bark_gain':0.16,
                        'inharmonicity':0.0018}},
        'reed':{'tone':{'mechanism':'reed','decay_s':2.0,'bell_gain':0.12,'bark_gain':0.34,
                        'inharmonicity':0.0005},
                'pickup':{'cutoff_hz':6200.0}},
        'digital_fm':{'tone':{'mechanism':'digital_fm','decay_s':3.2,'bell_gain':0.52,'bark_gain':0.08,
                              'inharmonicity':0.0},
                      'pickup':{'drive':0.92,'cutoff_hz':12000.0}},
    },
    'pickup':{
        'mellow':{'pickup':{'drive':0.92,'cutoff_hz':5200.0}},
        'neutral':{},
        'bright':{'pickup':{'drive':1.28,'cutoff_hz':12500.0}},
    },
    'amp':{
        'direct':{'amp':{'drive':0.85,'cutoff_hz':15000.0}},
        'clean_combo':{},
        'warm_combo':{'amp':{'drive':1.55,'cutoff_hz':5400.0}},
    },
    'modulation':{
        'none':{'modulation':{'type':'none','depth':0.0,'chorus_depth_cents':0.0}},
        'tremolo':{'modulation':{'type':'tremolo','rate_hz':4.6,'depth':0.20}},
        'chorus':{'modulation':{'type':'chorus','chorus_rate_hz':0.55,'chorus_depth_cents':6.5}},
    },
    'perspective':{
        'centered':{},
        'wide':{'stereo_width':0.90},
        'close':{'stereo_width':0.25,'mechanics':{'key_noise_gain':0.016}},
    },
}


def _set_path(graph,path,value):
    tokens=path.split('.')
    cur=graph
    for token in tokens[:-1]:
        cur=cur.setdefault(token,{})
    cur[tokens[-1]]=value


def _family(design):
    family=design.get('family','acoustic')
    if family not in FAMILY_OPTIONS:
        raise PianoDesignError(f'piano family must be one of {sorted(FAMILY_OPTIONS)}')
    return family


def validate_piano_design(design):
    if not isinstance(design,dict):
        raise PianoDesignError('piano_design must be an object')
    unknown_top=set(design)-{'family','categories','controls'}
    if unknown_top:
        raise PianoDesignError(f'unknown piano_design fields: {sorted(unknown_top)}')
    family=_family(design)
    categories=design.get('categories',{})
    controls=design.get('controls',{})
    if not isinstance(categories,dict):
        raise PianoDesignError('piano_design.categories must be an object')
    if not isinstance(controls,dict):
        raise PianoDesignError('piano_design.controls must be an object')

    cat_opts= CATEGORY_OPTIONS if family=='acoustic' else ELECTRIC_CATEGORY_OPTIONS
    control_specs= ACOUSTIC_CONTROL_SPECS if family=='acoustic' else ELECTRIC_CONTROL_SPECS
    unknown_categories=set(categories)-set(cat_opts)
    if unknown_categories:
        raise PianoDesignError(f'unknown {family} piano category fields: {sorted(unknown_categories)}')
    for key,value in categories.items():
        if value not in cat_opts[key]:
            raise PianoDesignError(f'{family} piano category {key} must be one of {sorted(cat_opts[key])}')

    unknown_controls=set(controls)-set(control_specs)
    if unknown_controls:
        raise PianoDesignError(f'unknown {family} piano numeric controls: {sorted(unknown_controls)}')
    for key,value in controls.items():
        path,lo,hi,caster=control_specs[key]
        try:
            numeric=float(value)
        except Exception as exc:
            raise PianoDesignError(f'piano control {key} must be numeric') from exc
        if not (lo <= numeric <= hi):
            raise PianoDesignError(f'piano control {key} outside [{lo}, {hi}]')
        if caster is int and int(numeric)!=numeric:
            raise PianoDesignError(f'piano control {key} must be an integer')
    return True


def resolve_piano_design(patch):
    """Resolve family/category topology first, then absolute numeric controls.

    `family` and `categories` are discrete structural choices authored by the Composer Agent.
    `controls` are direct numeric values and always win when they address the same parameter.
    No subjective word is converted to a number by this module.
    """
    if not isinstance(patch,dict):
        raise PianoDesignError('piano patch must be an object')
    if 'piano_design' not in patch:
        return deepcopy(patch)
    if 'piano_graph' in patch or 'electric_piano_graph' in patch:
        raise PianoDesignError('piano patch cannot mix piano_design with a resolved piano graph')
    if patch.get('kind','piano')!='piano':
        raise PianoDesignError('piano_design requires kind=piano')

    design=deepcopy(patch['piano_design'])
    validate_piano_design(design)
    family=_family(design)
    if family=='acoustic':
        categories=dict(DEFAULT_CATEGORIES)
        categories.update(design.get('categories',{}))
        controls=deepcopy(design.get('controls',{}))
        graph=_base_acoustic_graph()
        for category_family in ('body','hammer','stringing','soundboard','perspective'):
            _merge(graph,ACOUSTIC_CATEGORY_BASELINES[category_family][categories[category_family]])
        for key,value in controls.items():
            path,_,_,caster=ACOUSTIC_CONTROL_SPECS[key]
            _set_path(graph,path,caster(value))
        if graph['hammer']['low_cutoff_hz'] >= graph['hammer']['soft_high_cutoff_hz']:
            raise PianoDesignError('hammer cutoffs must satisfy low < soft_high')
        if graph['hammer']['soft_high_cutoff_hz'] > graph['hammer']['hard_high_cutoff_hz']:
            raise PianoDesignError('hammer cutoffs must satisfy soft_high <= hard_high')
        if graph['damper']['pedal_release_s'] < graph['damper']['release_s']:
            raise PianoDesignError('pedal_release_s must be >= release_s')
        if graph['body_filter']['soft_cutoff_hz'] > graph['body_filter']['hard_cutoff_hz']:
            raise PianoDesignError('body soft cutoff must be <= hard cutoff')
        if graph['bridge']['low_cutoff_hz'] >= graph['bridge']['high_cutoff_hz']:
            raise PianoDesignError('bridge cutoffs must satisfy low < high')
        out=deepcopy(patch); out.pop('piano_design',None)
        out['kind']='piano'; out['piano_engine']='acoustic'; out['piano_graph']=graph
    else:
        categories=dict(ELECTRIC_DEFAULT_CATEGORIES)
        categories.update(design.get('categories',{}))
        controls=deepcopy(design.get('controls',{}))
        graph=_base_electric_graph()
        for category_family in ('mechanism','pickup','amp','modulation','perspective'):
            _merge(graph,ELECTRIC_CATEGORY_BASELINES[category_family][categories[category_family]])
        for key,value in controls.items():
            path,_,_,caster=ELECTRIC_CONTROL_SPECS[key]
            _set_path(graph,path,caster(value))
        out=deepcopy(patch); out.pop('piano_design',None)
        out['kind']='piano'; out['piano_engine']='electric'; out['electric_piano_graph']=graph

    out['piano_design_resolved']={
        'family':family,
        'categories':categories,
        'controls':controls,
        'semantics':'family_categories_then_absolute_numeric_controls',
    }
    return out


__all__=[
    'PianoDesignError','FAMILY_OPTIONS',
    'CATEGORY_OPTIONS','DEFAULT_CATEGORIES','CATEGORY_BASELINES','CONTROL_SPECS',
    'ACOUSTIC_CONTROL_SPECS','ELECTRIC_CATEGORY_OPTIONS','ELECTRIC_DEFAULT_CATEGORIES',
    'ELECTRIC_CONTROL_SPECS','validate_piano_design','resolve_piano_design'
]
