import math
import numpy as np
from scipy.signal import lfilter

def stereo_delay(sig, sr, delay_s=0.24, feedback=0.22, repeats=3, cross=0.55):
    out = sig.copy()
    d = int(delay_s * sr)
    for r in range(1, repeats + 1):
        shift = r * d
        if shift >= len(sig):
            break
        src = sig[:-shift] * (feedback ** r)
        wet = np.stack([
            src[:, 0] * (1-cross) + src[:, 1] * cross,
            src[:, 1] * (1-cross) + src[:, 0] * cross,
        ], axis=1)
        out[shift:] += wet
    return out

def delay_wet(sig, sr, delay_s=0.24, feedback=0.22, repeats=3, cross=0.55):
    return stereo_delay(sig, sr, delay_s, feedback, repeats, cross) - sig

def simple_reverb(sig, sr):
    out = sig.copy()
    taps = [(0.047, .13, .25), (0.083, .11, .35), (0.131, .08, .45), (0.197, .06, .55)]
    for delay_s, gain, cross in taps:
        d = int(delay_s * sr)
        if d >= len(sig):
            continue
        src = sig[:-d]
        wet = np.stack([
            src[:, 0] * (1-cross) + src[:, 1] * cross,
            src[:, 1] * (1-cross) + src[:, 0] * cross,
        ], axis=1)
        out[d:] += wet * gain
    return out

def reverb_wet(sig, sr):
    return simple_reverb(sig, sr) - sig

def one_pole_lowpass(sig, sr, cutoff):
    cutoff = max(20.0, min(float(cutoff), sr * 0.45))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    return np.column_stack([
        lfilter([alpha], [1.0, -(1.0-alpha)], sig[:, 0]),
        lfilter([alpha], [1.0, -(1.0-alpha)], sig[:, 1]),
    ])

def one_pole_highpass(sig, sr, cutoff):
    return sig - one_pole_lowpass(sig, sr, cutoff)

def apply_pan(sig, pan):
    """Stereo balance pan. Center preserves the original stereo image."""
    pan = max(-1.0, min(1.0, float(pan)))
    out = sig.copy()
    if pan > 0:
        out[:, 0] *= math.cos(pan * math.pi / 2)
    elif pan < 0:
        out[:, 1] *= math.cos((-pan) * math.pi / 2)
    return out

def _smooth_envelope(mono_abs, sr, attack_s=0.008, release_s=0.12):
    # Instantaneous transient capture plus deterministic smoothing.
    # This avoids missing very short kick/click transients while retaining
    # a release tail suitable for compression and sidechain ducking.
    a_attack = 1.0 - math.exp(-1.0 / max(1.0, sr * attack_s))
    attack_smooth = lfilter([a_attack], [1.0, -(1.0-a_attack)], mono_abs)
    fast = np.maximum(mono_abs, attack_smooth)

    a_release = 1.0 - math.exp(-1.0 / max(1.0, sr * release_s))
    release_tail = lfilter([a_release], [1.0, -(1.0-a_release)], fast)
    return np.maximum(fast, release_tail)

def compressor(sig, sr, threshold_db=-14.0, ratio=3.0, attack_s=0.008, release_s=0.12, makeup_db=0.0):
    mono_abs = np.max(np.abs(sig), axis=1)
    env = _smooth_envelope(mono_abs, sr, attack_s, release_s)
    eps = 1e-12
    env_db = 20.0 * np.log10(env + eps)
    over = np.maximum(0.0, env_db - float(threshold_db))
    gain_reduction_db = over * (1.0 - 1.0 / max(1.0, float(ratio)))
    gain = 10.0 ** ((-gain_reduction_db + float(makeup_db)) / 20.0)
    return sig * gain[:, None], gain

def duck(sig, sidechain, sr, threshold_db=-28.0, amount_db=7.0, attack_s=0.006, release_s=0.16):
    mono_abs = np.max(np.abs(sidechain), axis=1)
    env = _smooth_envelope(mono_abs, sr, attack_s, release_s)
    threshold = 10.0 ** (float(threshold_db) / 20.0)
    activity = np.clip((env - threshold) / max(threshold * 2.5, 1e-9), 0.0, 1.0)
    min_gain = 10.0 ** (-abs(float(amount_db)) / 20.0)
    gain = 1.0 - activity * (1.0 - min_gain)
    return sig * gain[:, None], gain

def soft_limit(sig, drive=1.4, ceiling=0.93):
    out = np.tanh(sig * drive)
    peak = np.max(np.abs(out))
    if peak > ceiling and peak > 0:
        out = out / peak * ceiling
    return out
