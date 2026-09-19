def analyze_sound_palette(ir: dict) -> dict:
    roles=ir.get('arrangement',{}).get('roles',{})
    instruments=ir.get('instruments',{})
    rows={}
    for role,cfg in roles.items():
        iid=cfg.get('instrument')
        patch=instruments.get(iid,{})
        if role=='drums' or patch.get('kind')=='percussion':
            dg=patch.get('drum_graph',{})
            rows[role]={
                'instrument_id':iid,
                'kind':'percussion',
                'kick_pitch_end_hz':dg.get('kick',{}).get('pitch_end_hz'),
                'snare_noise_band':[dg.get('snare',{}).get('noise_low_hz'),dg.get('snare',{}).get('noise_high_hz')],
                'hat_decay_s':dg.get('hat',{}).get('decay_s'),
            }
            continue
        graph=patch.get('graph',patch) if isinstance(patch,dict) else {}
        rows[role]={
            'instrument_id':iid,
            'kind':'pitched',
            'waveforms':[o.get('waveform','sine') for o in graph.get('oscillators',[])],
            'oscillator_count':len(graph.get('oscillators',[])),
            'unison_voices':graph.get('unison',{}).get('voices',1),
            'stereo_width':graph.get('unison',{}).get('stereo_width',0.0),
            'attack_s':graph.get('envelope',{}).get('attack'),
            'release_s':graph.get('envelope',{}).get('release'),
            'filter_type':graph.get('filter',{}).get('type','none'),
            'filter_cutoff':graph.get('filter',{}).get('cutoff'),
            'output_gain':graph.get('output_gain',1.0),
        }
    return {
        'palette_source': 'agent_authored' if ir.get('sound_palette_resolved',{}).get('roles') else 'seed',
        'roles': rows,
    }

__all__=['analyze_sound_palette']
