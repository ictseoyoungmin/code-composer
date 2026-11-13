"""One-time transport: reproduce locally verified bytes, then remove this helper."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path.cwd();KIT=ROOT/'skills/code-composer/kit';SRC=KIT/'src/code_composer'

def replace(path,old,new):
    text=path.read_text()
    assert text.count(old)==1,(str(path),'unexpected base')
    path.write_text(text.replace(old,new,1))

helper='''def _hammer_unison_phase(midi, string_count, string_index, alignment=0.0):
    """Optionally share the initial hammer phase of three treble strings.

    Fixed phase spacing seeds a differential mode before detuning evolves.
    Preserve the mean phase while tapering that spacing over C4..C6. Authored
    per-strike jitter is applied separately and is not discarded. Zero is the
    exact existing path; one selects the shared-phase audition model.
    """
    alignment=float(alignment)
    if not math.isfinite(alignment) or not 0.0 <= alignment <= 1.0:
        raise ValueError("piano hammer phase alignment must be finite in [0, 1]")
    if alignment==0.0 or string_count!=3 or midi<=60:
        return 0.53*string_index
    blend=alignment*float(_smoothstep01((float(midi)-60.0)/24.0))
    center=(string_count-1)/2.0
    return 0.53*(string_index+blend*(center-string_index))


'''
replace(SRC/'audio/piano.py','def _treble_coupling_rate(',helper+'def _treble_coupling_rate(')
replace(SRC/'audio/piano.py','0.53*si + strike_global_phase',"_hammer_unison_phase(midi,string_count,si,strings.get('hammer_phase_alignment',0.0)) + strike_global_phase")
replace(SRC/'audio/piano_design.py',"    'unison_partial_mistune_cents':","    'unison_hammer_phase_alignment': ('strings.hammer_phase_alignment', 0.0, 1.0, float),\n    'unison_partial_mistune_cents':")
replace(SRC/'execution/preview.py','cr05-renderer-epoch-3','cr05-renderer-epoch-4')
replace(ROOT/'tests/test_piano_decay_cache_epoch.py','"cr05-renderer-epoch-2"]','"cr05-renderer-epoch-2", "cr05-renderer-epoch-3"]')
replace(ROOT/'tests/test_factory_presets.py','    assert 4 <= len(presets) <= 38','    # PR81 adds one explicit piano audition voice; no musical material.\n    assert 4 <= len(presets) <= 39')
# Correct a transport transcription before compiling or staging the developer tool.
replace(ROOT/'tools/render_piano_focus_audition.py',"'raw_rms':float(np.sqrt(np.mean(audio*audio)))}}","'raw_rms':float(np.sqrt(np.mean(audio*audio)))}")
sys.path.insert(0,str(KIT/'src'))
from code_composer.audio.piano_design import ACOUSTIC_CONTROL_SPECS
from code_composer.presets import list_presets
for path in (KIT/'schemas/piano_design.schema.json',SRC/'reference/schemas/piano_design.schema.json'):
    data=json.loads(path.read_text());props=data['oneOf'][0]['properties']['controls']['properties']
    props['unison_hammer_phase_alignment']={'type':'number','minimum':0,'maximum':1}
    for key,(_,lo,hi,cast) in ACOUSTIC_CONTROL_SPECS.items():
        if key not in props:props[key]={'type':'integer' if cast is int else 'number','minimum':lo,'maximum':hi}
    path.write_text(json.dumps(data,indent=2)+'\n')
path=KIT/'presets/CATALOG.json';data=json.loads(path.read_text());data['presets']=list_presets()
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
path=ROOT/'docs/maintenance/POST_V116_INTENTIONAL_SOURCE_CHANGES.json';data=json.loads(path.read_text())
for name,reason in [('audio/piano.py','PR81 third audition adds an explicit bounded hammer phase alignment control with exact zero-default compatibility. The focused preset uses shared treble excitation; existing presets are not revoiced. Authored note and pedal events are unchanged.'),('audio/piano_design.py','PR81 third audition exposes unison_hammer_phase_alignment as an absolute numeric acoustic control in [0,1], absent/zero preserving the prior engine path.')]:
    entry=data['files']['src/code_composer/'+name];entry['sha256']=hashlib.sha256((SRC/name).read_bytes()).hexdigest();entry['reason']+=' '+reason
for name in ('schemas/piano_design.schema.json','src/code_composer/reference/schemas/piano_design.schema.json'):
    data['files'][name]={'sha256':hashlib.sha256((KIT/name).read_bytes()).hexdigest(),'reason':'PR81 third audition exposes bounded unison_hammer_phase_alignment and repairs schema drift for 14 existing runtime strike/unison/release controls. Bounds match ACOUSTIC_CONTROL_SPECS exactly; unknown properties remain rejected. No new musical inference or event fields.'}
path.write_text(json.dumps(data,indent=2)+'\n')
expected={
 'docs/maintenance/POST_V116_INTENTIONAL_SOURCE_CHANGES.json':'22ea3496f314a4465f16c7dd192284f7e8c474329c9e58cc54761505f81dc047',
 'skills/code-composer/kit/presets/CATALOG.json':'e5d7ab98dabe3fcfd6440892c5c169ba2bdf884d16d77c88cdbfaa087d57f6e0',
 'skills/code-composer/kit/schemas/piano_design.schema.json':'e0ec9b3e8f948503cedadd10713874dcd71a9129d93b1f159553e856e5831fce',
 'skills/code-composer/kit/src/code_composer/reference/schemas/piano_design.schema.json':'e0ec9b3e8f948503cedadd10713874dcd71a9129d93b1f159553e856e5831fce',
 'skills/code-composer/kit/src/code_composer/audio/piano.py':'f775a0860637f16d98df468e53e423c9937b5666a63b01719113949a46be60ad',
 'skills/code-composer/kit/src/code_composer/audio/piano_design.py':'58e72a93bdfc5488008a52c08b55fc4b87aca56471831637a8af2d3b96eb32d9',
 'skills/code-composer/kit/src/code_composer/execution/preview.py':'b3cd2e30e4a4cc7d65bc3cd20e120538d64773c513ddc18f974df7cb4b8b3aad',
 'tests/test_factory_presets.py':'07738c712f0e245edbbf38b7fbe66e2d3a71356dc0032739c68c737cd3210f60',
 'tests/test_piano_decay_cache_epoch.py':'56289145a17e6135c1cf0be1df7e331508b5e11b655aa1b01cae111e2b49b21a',
 'tests/test_piano_focus_voice.py':'e8dacdd8517e07f532cdd14fe96c39df7d5e6abbb27d3e25803a6b2f846ac7d6',
 'tools/render_piano_focus_audition.py':'95b211ce2f329a65953c451d1e5fa9755b7b247021aff58230314682411f4d39',
 'docs/maintenance/PIANO_FOCUSED_AUDITION_PR81.md':'f5a812ad99bb5f46a593d7ac0c37dacff8306abe82cacd81aa1629d70ae34926',
 'skills/code-composer/kit/src/code_composer/reference/presets/piano__concert_grand_focused__1.0.0.json':'412b9991169a1e13b7f129164be42dee4dff26653bb6f5de15fabfe6974d9739',
}
for name,digest in expected.items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,('transport mismatch',name)
subprocess.run(['git','add','--',*expected],check=True)
print('All 13 edited/new files match the locally tested SHA256 values.')
