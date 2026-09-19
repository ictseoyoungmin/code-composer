import math
import numpy as np
from ..core.theory import midi_to_hz

def adsr(n: int, sr: int, attack: float, decay: float, sustain: float, release: float):
    na = min(int(attack * sr), n)
    nd = min(int(decay * sr), max(0, n - na))
    nr = min(int(release * sr), max(0, n - na - nd))
    ns = max(0, n - na - nd - nr)

    env = np.zeros(n, dtype=np.float64)
    i = 0
    if na:
        env[i:i+na] = np.linspace(0, 1, na, endpoint=False)
        i += na
    if nd:
        env[i:i+nd] = np.linspace(1, sustain, nd, endpoint=False)
        i += nd
    if ns:
        env[i:i+ns] = sustain
        i += ns
    if nr:
        env[i:i+nr] = np.linspace(sustain, 0, nr)
    return env

def equal_power_pan(sig: np.ndarray, pan: float):
    pan = max(-1.0, min(1.0, pan))
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    return np.stack([sig * left, sig * right], axis=1)

def synth_note(midi: int, duration_s: float, sr: int, patch: dict):
    n = max(1, int(duration_s * sr))
    t = np.arange(n) / sr
    f = midi_to_hz(midi)
    kind = patch.get("kind", "sine")

    if kind == "lead":
        sig = (
            np.sin(2*np.pi*f*t)
            + 0.25*np.sin(2*np.pi*2*f*t + 0.2)
            + 0.10*np.sin(2*np.pi*3*f*t + 0.4)
        )
    elif kind == "pad":
        sig = (
            np.sin(2*np.pi*f*t)
            + 0.50*np.sin(2*np.pi*f*0.997*t)
            + 0.40*np.sin(2*np.pi*f*1.003*t)
        )
    elif kind == "bass":
        sig = np.sin(2*np.pi*f*t) + 0.18*np.sin(2*np.pi*2*f*t)
    elif kind == "pluck":
        sig = (
            np.sin(2*np.pi*f*t)
            + 0.30*np.sin(2*np.pi*2*f*t)
            + 0.10*np.sin(2*np.pi*4*f*t)
        )
    else:
        sig = np.sin(2*np.pi*f*t)

    env_cfg = patch.get("adsr", {})
    env = adsr(
        n, sr,
        env_cfg.get("attack", 0.01),
        env_cfg.get("decay", 0.08),
        env_cfg.get("sustain", 0.65),
        env_cfg.get("release", min(0.2, duration_s * 0.25)),
    )
    return sig * env
