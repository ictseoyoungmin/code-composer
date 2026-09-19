import json
from pathlib import Path
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.harmonic_analysis import analyze_harmony


def _track(resolved, tid):
    return next(t for t in resolved['tracks'] if t['id']==tid)


def test_harmonic_color_grammar():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/'tests/fixtures/topline_ir.json').read_text())
    baseline=arrange_ir(ir)

    ir['harmonic_grammar']={
        'enabled':True,
        'default':{
            'colors':['seventh','add9','sus2','seventh'],
            'normalize_density':True,
        },
        'sections':{
            ir['form'][0]['id']:{
                'colors':['sus2','add9'],
                'cadence_color':'sus4',
                'passing_enabled':True,
                'passing_degree_offset':1,
                'passing_color':'sus4',
                'passing_beats':0.5,
            }
        }
    }
    a=arrange_ir(ir); b=arrange_ir(ir)
    assert a==b
    q=analyze_harmony(a)
    assert q['unique_colors'] >= 3
    assert q['passing_chords'] >= 1
    assert q['mean_voice_leading_cost'] < 12.0
    # Harmonic color is an upper-structure operation: bass identity stays unchanged.
    assert _track(baseline,'bass')['events'] == _track(a,'bass')['events']
    # Density normalization prevents color extensions from exploding velocity.
    assert max(e['velocity'] for e in _track(a,'pad')['events']) <= 1.0
