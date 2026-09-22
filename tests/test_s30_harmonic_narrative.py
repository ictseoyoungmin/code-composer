import json
from copy import deepcopy
from pathlib import Path

import pytest

from code_composer.agent.composition_brief import brief_from_dict, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.harmonic_analysis import analyze_harmony
from code_composer.validation_contracts import validate_runtime_extensions, ContractValidationError

ROOT=Path(__file__).resolve().parents[1]


def _seed():
    return json.loads((ROOT/'tests/fixtures/topline_ir.json').read_text())


def _brief():
    return json.loads((ROOT/'tests/fixtures/composition_brief.json').read_text())


def _with_progressions(data):
    data=deepcopy(data)
    data['materials']['progression_variants']={
        'verse_path':{'degrees':[1,6,4,5]},
        'final_path':{'degrees':[4,6,5,1]},
    }
    data['harmony']['sections']['verse']['progression_variant']='verse_path'
    data['harmony']['sections']['final']['progression_variant']='final_path'
    return data


def _section_degrees(track, section_id):
    rows=[]
    for e in track['events']:
        if e.get('section_id')!=section_id or e.get('harmonic_passing'):
            continue
        key=(float(e['start_beat']),int(e.get('harmonic_degree',-1)))
        if not rows or rows[-1]!=key:
            rows.append(key)
    return [degree for _,degree in rows]


def test_brief_materializes_explicit_progression_variants():
    data=_with_progressions(_brief())
    out=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(data)))
    assert out['materials']['progressions']['verse_path']['degrees']==[1,6,4,5]
    assert out['materials']['progressions']['verse_path']['source_progression_id']=='home'
    assert out['harmonic_grammar']['sections']['verse']['progression_variant']=='verse_path'
    assert out['harmonic_grammar']['sections']['final']['progression_variant']=='final_path'


def test_unknown_progression_variant_reference_is_rejected_in_brief():
    data=_brief()
    data['harmony']['sections']['final']['progression_variant']='ghost'
    with pytest.raises(BriefValidationError,match='unknown progression variant'):
        compile_brief(_seed(),brief_from_dict(data))


def test_invalid_progression_variant_degrees_are_rejected():
    data=_brief()
    data['materials']['progression_variants']={'bad':{'degrees':[1,0,5]}}
    data['harmony']['sections']['final']['progression_variant']='bad'
    with pytest.raises(BriefValidationError,match='scale degrees 1..14'):
        compile_brief(_seed(),brief_from_dict(data))


def test_runtime_unknown_progression_variant_is_rejected():
    ir=_seed()
    ir['harmonic_grammar']={
        'enabled':True,
        'default':{'colors':['seventh']},
        'sections':{'verse':{'progression_variant':'ghost'},'final':{}},
    }
    with pytest.raises(ContractValidationError,match='unknown progression'):
        validate_runtime_extensions(ir)


def test_arranger_routes_same_section_progression_to_pad_and_bass():
    data=_with_progressions(_brief())
    planned=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(data)))
    out=arrange_ir(planned)
    pad=next(t for t in out['tracks'] if t['id']=='pad')
    bass=next(t for t in out['tracks'] if t['id']=='bass')

    assert _section_degrees(pad,'verse')==[1,6,4,5]
    assert _section_degrees(pad,'final')==[4,6,5,1]
    assert all(e.get('harmonic_progression_id')=='verse_path' for e in pad['events'] if e.get('section_id')=='verse')
    assert all(e.get('harmonic_progression_id')=='final_path' for e in pad['events'] if e.get('section_id')=='final' and 'midi' in e)
    report=analyze_harmony(out)
    assert report['progression_lineage']['verse']['degree_path']==[1,6,4,5]
    assert report['progression_lineage']['final']['degree_path']==[4,6,5,1]

    # Bass has multiple events per bar, but each bar must share the same degree path.
    for sid,expected in [('verse',[1,6,4,5]),('final',[4,6,5,1])]:
        bars={}
        for e in bass['events']:
            if e.get('section_id')!=sid:
                continue
            bar=int(float(e['start_beat'])//4)
            bars.setdefault(bar,set()).add(int(e['midi']))
            assert e.get('harmonic_progression_id') in {'verse_path','final_path'}
        assert len(bars)==4
        # Exact MIDI depends on tonal root/octave, but each bar is a single authored degree/root.
        assert all(len(v)==1 for v in bars.values())


def test_no_progression_variant_surface_preserves_existing_arrangement_exactly():
    ir=_seed()
    control=arrange_ir(ir)
    treatment=deepcopy(ir)
    treatment['harmonic_grammar']={
        'enabled':True,
        'default':{'colors':['seventh']},
        'sections':{'verse':{'colors':['seventh']},'final':{'colors':['seventh']}},
    }
    # No progression_variant means historical progression indexing and event metadata stay untouched.
    out=arrange_ir(treatment)
    for tid in ('pad','bass','arp'):
        a=next(t for t in control['tracks'] if t['id']==tid)
        b=next(t for t in out['tracks'] if t['id']==tid)
        core=lambda e:(e.get('start_beat'),e.get('duration_beats'),e.get('midi'),e.get('velocity'),e.get('section_id'))
        assert [core(e) for e in a['events']]==[core(e) for e in b['events']]
        assert all('harmonic_progression_id' not in e for e in b['events'])


def test_harmony_analysis_ignores_non_note_piano_controls():
    data=_with_progressions(_brief())
    planned=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(data)))
    out=arrange_ir(planned)
    pad=next(t for t in out['tracks'] if t['id']=='pad')
    pad['events'].append({
        'event_type':'piano_control','control':'sustain_pedal','start_beat':0.0,'duration_beats':4.0,
        'section_id':'verse','points':[{'offset_beats':0.0,'position':0.0},{'offset_beats':4.0,'position':0.0}],
    })
    report=analyze_harmony(out)
    assert report['present'] is True
    assert report['progression_lineage']['verse']['degree_path']==[1,6,4,5]
