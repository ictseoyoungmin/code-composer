from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_s28f_is_an_audit_only_slice_and_keeps_explicit_mix_authority():
    text=(ROOT/'tools/s28f_piano_phrase_safe_ducking_audit.py').read_text(encoding='utf-8')
    assert 'from code_composer.audio.dsp import duck' in text
    assert "'no_duck':None" in text
    assert "'current_1p8dB_8ms_150ms'" in text
    assert 'The Composer/mix plan remains explicit.' in text
