import numpy as np


def mono(stereo):
    return 0.5*(stereo[:,0]+stereo[:,1]) if len(stereo) else np.zeros(0)


def onset_click_score(stereo, sr, window_ms=25.0):
    """Peak first-difference in onset window normalized by note RMS."""
    x=mono(stereo)
    if len(x)<2:
        return 0.0
    n=min(len(x),max(2,int(sr*window_ms*0.001)))
    rms=float(np.sqrt(np.mean(x*x))+1e-12)
    return float(np.max(np.abs(np.diff(x[:n])))/rms)


def high_band_ratio(stereo, sr, cutoff_hz=7000.0):
    x=mono(stereo)
    if len(x)==0:
        return 0.0
    w=np.hanning(len(x))
    spec=np.abs(np.fft.rfft(x*w))**2
    f=np.fft.rfftfreq(len(x),1.0/sr)
    total=float(np.sum(spec)+1e-12)
    return float(np.sum(spec[f>=cutoff_hz])/total)


def spectral_flatness(stereo):
    x=mono(stereo)
    if len(x)==0:
        return 0.0
    spec=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2 + 1e-15
    return float(np.exp(np.mean(np.log(spec)))/(np.mean(spec)+1e-15))


def harmonic_concentration(stereo, sr, fundamental_hz, harmonics=4, bandwidth_hz=35.0):
    """Fraction of spectral power close to low harmonics."""
    x=mono(stereo)
    if len(x)==0:
        return 0.0
    spec=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
    f=np.fft.rfftfreq(len(x),1.0/sr)
    total=float(np.sum(spec)+1e-12)
    mask=np.zeros_like(f,dtype=bool)
    for h in range(1,int(harmonics)+1):
        center=fundamental_hz*h
        mask |= np.abs(f-center)<=bandwidth_hz
    return float(np.sum(spec[mask])/total)
