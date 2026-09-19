import numpy as np

def analyze_audio(stereo: np.ndarray, sr: int) -> dict:
    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    rms = float(np.sqrt(np.mean(stereo ** 2))) if len(stereo) else 0.0
    left_rms = float(np.sqrt(np.mean(stereo[:,0] ** 2))) if len(stereo) else 0.0
    right_rms = float(np.sqrt(np.mean(stereo[:,1] ** 2))) if len(stereo) else 0.0
    silence_ratio = float(np.mean(np.max(np.abs(stereo), axis=1) < 1e-4)) if len(stereo) else 1.0

    return {
        "duration_seconds": len(stereo) / sr,
        "peak": peak,
        "rms": rms,
        "crest_factor": peak / rms if rms > 0 else 0.0,
        "left_rms": left_rms,
        "right_rms": right_rms,
        "stereo_rms_delta": abs(left_rms - right_rms),
        "silence_ratio": silence_ratio,
    }
