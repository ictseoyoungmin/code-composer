import numpy as np

EPS = 1e-12

def _rms(x):
    return float(np.sqrt(np.mean(x**2))) if len(x) else 0.0

def _peak(x):
    return float(np.max(np.abs(x))) if len(x) else 0.0

def _stereo_width(x):
    if len(x) == 0:
        return 0.0
    mid = 0.5 * (x[:,0] + x[:,1])
    side = 0.5 * (x[:,0] - x[:,1])
    return _rms(side) / (_rms(mid) + EPS)

def _mono(x):
    return 0.5 * (x[:,0] + x[:,1])

def _spectral_features(x, sr):
    if len(x) < 8:
        return {
            "centroid_hz": 0.0,
            "low_ratio": 0.0,
            "mid_ratio": 0.0,
            "high_ratio": 0.0,
        }

    mono = _mono(x)
    # Cap FFT size for speed but sample across the section.
    nfft = min(65536, len(mono))
    if len(mono) > nfft:
        idx = np.linspace(0, len(mono)-1, nfft).astype(int)
        mono = mono[idx]

    win = np.hanning(len(mono))
    spec = np.abs(np.fft.rfft(mono * win))
    power = spec**2
    freqs = np.fft.rfftfreq(len(mono), 1/sr)
    total = float(np.sum(power)) + EPS

    centroid = float(np.sum(freqs * power) / total)
    low = float(np.sum(power[freqs < 250])) / total
    mid = float(np.sum(power[(freqs >= 250) & (freqs < 2500)])) / total
    high = float(np.sum(power[freqs >= 2500])) / total

    return {
        "centroid_hz": centroid,
        "low_ratio": low,
        "mid_ratio": mid,
        "high_ratio": high,
    }

def _transient_density(x, sr):
    if len(x) < 8:
        return 0.0
    mono = np.abs(_mono(x))
    frame = max(1, int(sr * 0.010))
    hop = frame
    n = len(mono) // hop
    if n < 3:
        return 0.0
    env = np.array([
        np.mean(mono[i*hop:(i+1)*hop]) for i in range(n)
    ])
    diff = np.diff(env, prepend=env[0])
    threshold = max(np.mean(diff) + 1.75*np.std(diff), 1e-6)
    onsets = int(np.sum(diff > threshold))
    duration = len(x) / sr
    return onsets / max(duration, EPS)

def _silence_ratio(x, threshold=1e-4):
    if len(x) == 0:
        return 1.0
    return float(np.mean(np.max(np.abs(x), axis=1) < threshold))

def _transition_metrics(audio, boundary_sample, sr, window_s=0.08):
    w=max(1,int(sr*window_s))
    before=audio[max(0,boundary_sample-w):boundary_sample]
    after=audio[boundary_sample:min(len(audio),boundary_sample+w)]
    if len(before)==0 or len(after)==0:
        return {"discontinuity":0.0,"before_rms":0.0,"after_rms":0.0,"direction":"flat"}
    rb=_rms(before); ra=_rms(after)
    d=abs(ra-rb)/max(ra+rb,EPS)
    direction="up" if ra>rb*1.02 else "down" if rb>ra*1.02 else "flat"
    return {"discontinuity":d,"before_rms":rb,"after_rms":ra,"direction":direction}

def _pearson(xs, ys):
    if len(xs) < 2:
        return 1.0
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    if np.std(x) < EPS or np.std(y) < EPS:
        return 1.0 if np.allclose(x, y) else 0.0
    return float(np.corrcoef(x, y)[0,1])

def analyze_sections(audio, sr, ir):
    bpm = float(ir["transport"]["bpm"])
    beats_per_bar = float(ir["transport"]["beats_per_bar"])
    bar_s = beats_per_bar * 60.0 / bpm

    sections = {}
    measured_rms = []
    expected = []
    boundaries = []

    for i, sec in enumerate(ir["form"]):
        start_s = sec["start_bar"] * bar_s
        end_s = (sec["start_bar"] + sec["bars"]) * bar_s
        start = int(start_s * sr)
        end = min(len(audio), int(end_s * sr))
        chunk = audio[start:end]

        spec = _spectral_features(chunk, sr)
        rms = _rms(chunk)
        peak = _peak(chunk)
        width = _stereo_width(chunk)
        transient = _transient_density(chunk, sr)
        silence = _silence_ratio(chunk)

        expected_energy = float(sec.get("energy", 1.0))
        sections[sec["id"]] = {
            "start_seconds": start_s,
            "end_seconds": end_s,
            "expected_energy": expected_energy,
            "rms": rms,
            "peak": peak,
            "crest_factor": peak / max(rms, EPS),
            "stereo_width": width,
            "silence_ratio": silence,
            "transient_density_hz": transient,
            **spec,
        }
        expected.append(expected_energy)
        measured_rms.append(rms)
        if i > 0:
            boundaries.append((sec["id"], start))

    # Normalize RMS for shape comparison against expected energy.
    max_rms = max(measured_rms) if measured_rms else 1.0
    max_expected = max(expected) if expected else 1.0
    measured_norm = [x / max(max_rms, EPS) for x in measured_rms]
    expected_norm = [x / max(max_expected, EPS) for x in expected]

    for sec_id, mn, en in zip(sections, measured_norm, expected_norm):
        sections[sec_id]["measured_energy_norm"] = mn
        sections[sec_id]["expected_energy_norm"] = en
        sections[sec_id]["energy_error"] = mn - en

    transitions = {}
    for sec_id, sample in boundaries:
        transitions[sec_id] = _transition_metrics(audio, sample, sr)

    whole_peak = _peak(audio)
    whole_rms = _rms(audio)
    report = {
        "global": {
            "duration_seconds": len(audio)/sr,
            "peak": whole_peak,
            "rms": whole_rms,
            "headroom_db": float(20*np.log10(1.0/max(whole_peak, EPS))),
            "clipped_sample_ratio": float(np.mean(np.abs(audio) >= 1.0)),
            "silence_ratio": _silence_ratio(audio),
            "stereo_width": _stereo_width(audio),
        },
        "sections": sections,
        "transitions": transitions,
        "energy_correlation": _pearson(expected_norm, measured_norm),
    }
    report["issues"] = diagnose(report)
    return report

def diagnose(report):
    issues = []
    sections = report["sections"]

    for sid, s in sections.items():
        err = s["energy_error"]
        if err < -0.16:
            issues.append({
                "code": "SECTION_TOO_WEAK",
                "section": sid,
                "severity": "high" if err < -0.26 else "medium",
                "observed": round(s["measured_energy_norm"],4),
                "expected": round(s["expected_energy_norm"],4),
                "message": f"{sid} measured energy is below intent."
            })
        elif err > 0.20:
            issues.append({
                "code": "SECTION_TOO_STRONG",
                "section": sid,
                "severity": "medium",
                "observed": round(s["measured_energy_norm"],4),
                "expected": round(s["expected_energy_norm"],4),
                "message": f"{sid} measured energy exceeds intent."
            })

        if s["silence_ratio"] > 0.18 and s["expected_energy_norm"] > 0.5:
            issues.append({
                "code": "UNEXPECTED_SPARSITY",
                "section": sid,
                "severity": "medium",
                "observed": round(s["silence_ratio"],4),
                "message": f"{sid} contains more silence than expected for its energy role."
            })

        if s["high_ratio"] > 0.48:
            issues.append({
                "code": "BRIGHTNESS_EXCESS",
                "section": sid,
                "severity": "low",
                "observed": round(s["high_ratio"],4),
                "message": f"{sid} is dominated by high-frequency energy."
            })

        if s["low_ratio"] > 0.72:
            issues.append({
                "code": "LOW_END_DOMINANCE",
                "section": sid,
                "severity": "low",
                "observed": round(s["low_ratio"],4),
                "message": f"{sid} is dominated by low-frequency energy."
            })

    for sid, t in report["transitions"].items():
        if t["discontinuity"] > 0.58:
            issues.append({
                "code": "ABRUPT_TRANSITION",
                "section": sid,
                "severity": "medium",
                "observed": round(t["discontinuity"],4),
                "message": f"Transition into {sid} has a large short-term energy jump."
            })

    g = report["global"]
    if g["clipped_sample_ratio"] > 0:
        issues.append({
            "code": "CLIPPING",
            "severity": "high",
            "observed": g["clipped_sample_ratio"],
            "message": "Rendered output contains clipped samples."
        })
    if g["headroom_db"] < 0.4:
        issues.append({
            "code": "LOW_HEADROOM",
            "severity": "medium",
            "observed": round(g["headroom_db"],4),
            "message": "Master output has very little headroom."
        })
    if report["energy_correlation"] < 0.55:
        issues.append({
            "code": "ENERGY_CURVE_MISMATCH",
            "severity": "high" if report["energy_correlation"] < 0.25 else "medium",
            "observed": round(report["energy_correlation"],4),
            "message": "Measured section energy poorly matches the intended energy curve."
        })

    return issues
