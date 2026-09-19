import math

import numpy as np
import pytest
from scipy.signal import get_window, stft

from code_composer.audio.piano import render_piano_note, apply_piano_soundboard
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.core.theory import midi_to_hz


SR = 12000
NOTE_S = 0.45
TRACK_S = 2.0

PRESETS = {
    "concert_grand": {
        "body": "concert_grand", "hammer": "medium_felt", "stringing": "concert",
        "soundboard": "open_board", "perspective": "player",
    },
    "studio_grand": {
        "body": "studio_grand", "hammer": "medium_felt", "stringing": "concert",
        "soundboard": "balanced_board", "perspective": "player",
    },
    "upright": {
        "body": "upright", "hammer": "dense_felt", "stringing": "compact",
        "soundboard": "dry_board", "perspective": "close",
    },
}

CASES = {
    "single": [55],
    "dyad": [55, 62],
    "triad": [55, 59, 62],
}


def _patch(name):
    return resolve_piano_design({
        "kind": "piano",
        "piano_design": {"family": "acoustic", "categories": PRESETS[name], "controls": {}},
    })


def _render_no_pedal_track(name, midis):
    patch = _patch(name)
    x = np.zeros((int(TRACK_S * SR), 2), dtype=np.float64)
    events = []
    for midi in midis:
        note = render_piano_note(
            midi, NOTE_S, SR, patch, velocity=.72, performance={"pedal": False}
        )
        x[:len(note)] += note
        events.append({
            "midi": midi, "start_beat": 0.0, "duration_beats": NOTE_S,
            "velocity": .72, "performance": {"pedal": False},
        })
    return apply_piano_soundboard(x, SR, patch, events, beat_s=1.0)


def _is_played_harmonic(freq, midis):
    for midi in midis:
        f0 = midi_to_hz(midi)
        for k in range(1, 10):
            target = f0 * k
            if target >= SR * .45:
                break
            cents = abs(1200.0 * math.log2(max(freq, 1e-9) / target))
            if cents < 40.0:
                return True
    return False


def _persistent_off_harmonic_peak_db(stereo, midis):
    mono = .5 * (stereo[:, 0] + stereo[:, 1])
    off = int(NOTE_S * SR)
    pre = mono[int((NOTE_S - .12) * SR):off]
    tail = mono[off + int(.18 * SR):off + int(.80 * SR)]

    f, _, z = stft(tail, SR, nperseg=1024, noverlap=768, boundary=None)
    persistent = np.median(np.abs(z), axis=1)
    _, _, pre_z = stft(
        pre, SR, nperseg=min(1024, len(pre)),
        noverlap=min(768, max(0, len(pre) - 1)), boundary=None,
    )
    reference = float(np.max(np.abs(pre_z))) + 1e-30
    candidates = [
        i for i, freq in enumerate(f)
        if 70.0 <= freq <= 2500.0 and not _is_played_harmonic(float(freq), midis)
    ]
    peak = max(float(persistent[i]) for i in candidates)
    return 20.0 * math.log10((peak + 1e-30) / reference)


def _release_rms_envelope(stereo):
    mono = .5 * (stereo[:, 0] + stereo[:, 1])
    off = int(NOTE_S * SR)
    tail = mono[off + int(.08 * SR):off + int(.70 * SR)]
    win = int(.04 * SR)
    hop = int(.02 * SR)
    return [
        float(np.sqrt(np.mean(tail[i:i + win] ** 2) + 1e-30))
        for i in range(0, max(0, len(tail) - win + 1), hop)
    ]


@pytest.mark.parametrize("preset", list(PRESETS))
@pytest.mark.parametrize("case", list(CASES))
def test_no_pedal_tail_has_no_persistent_unplayed_pitched_peak(preset, case):
    midis = CASES[case]
    stereo = _render_no_pedal_track(preset, midis)
    peak_db = _persistent_off_harmonic_peak_db(stereo, midis)
    # The most vulnerable historical case (concert grand, dyad/triad) sat near -42 dB
    # and exposed the fixed soundboard mode as a separate note.  Keep persistent
    # off-harmonic content safely below the audible body-tail foreground.
    assert peak_db < -50.0, (preset, case, peak_db)


@pytest.mark.parametrize("preset", list(PRESETS))
@pytest.mark.parametrize("case", list(CASES))
def test_no_pedal_release_envelope_does_not_reswell(preset, case):
    env = _release_rms_envelope(_render_no_pedal_track(preset, CASES[case]))
    assert env
    # No repeated 12% upward excursions: release must monotonically behave like a
    # damper-controlled decay rather than a chorus/wah envelope becoming foreground.
    upward = sum(b > a * 1.12 for a, b in zip(env, env[1:]))
    assert upward == 0, (preset, case, env)


def test_no_pedal_per_note_resonance_does_not_synthesize_old_one_point_five_ratio():
    patch = _patch("concert_grand")
    midi = 60
    mono = render_piano_note(
        midi, .55, SR, patch, velocity=.72, performance={"pedal": False}
    ).mean(axis=1)
    seg = mono[int(.565 * SR):int(.73 * SR)]
    nfft = 4096
    mag = np.abs(np.fft.rfft(seg * get_window("hann", len(seg)), n=nfft))
    freqs = np.fft.rfftfreq(nfft, 1.0 / SR)
    f0 = midi_to_hz(midi)
    fundamental = mag[np.argmin(np.abs(freqs - f0))] + 1e-30
    old_ratio = mag[np.argmin(np.abs(freqs - 1.5 * f0))] + 1e-30
    ratio_db = 20.0 * math.log10(old_ratio / fundamental)
    assert ratio_db < -70.0, ratio_db


def test_pedal_still_preserves_shared_body_resonance():
    patch = _patch("concert_grand")
    midis = CASES["triad"]

    def render(pedal):
        x = np.zeros((int(2.3 * SR), 2), dtype=np.float64)
        events = []
        for midi in midis:
            note = render_piano_note(
                midi, NOTE_S, SR, patch, velocity=.72, performance={"pedal": pedal}
            )
            x[:len(note)] += note
            events.append({
                "midi": midi, "start_beat": 0.0, "duration_beats": NOTE_S,
                "velocity": .72, "performance": {"pedal": pedal},
            })
        return apply_piano_soundboard(x, SR, patch, events, beat_s=1.0)

    dry = render(False)
    wet = render(True)
    a, b = int(.9 * SR), int(1.3 * SR)
    dry_rms = float(np.sqrt(np.mean(dry[a:b] ** 2) + 1e-30))
    wet_rms = float(np.sqrt(np.mean(wet[a:b] ** 2) + 1e-30))
    assert wet_rms > dry_rms * 20.0
