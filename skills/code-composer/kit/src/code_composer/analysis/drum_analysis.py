import numpy as np
from .timbre_analysis import mono, onset_click_score


def _spectrum(stereo, sr):
    x=mono(stereo)
    if len(x)==0:
        return np.zeros(1),np.zeros(1)
    w=np.hanning(len(x))
    power=np.abs(np.fft.rfft(x*w))**2
    freq=np.fft.rfftfreq(len(x),1.0/sr)
    return freq,power


def band_ratio(stereo, sr, low_hz, high_hz):
    f,p=_spectrum(stereo,sr)
    total=float(np.sum(p)+1e-12)
    mask=(f>=float(low_hz))&(f<float(high_hz))
    return float(np.sum(p[mask])/total)


def spectral_centroid(stereo, sr):
    f,p=_spectrum(stereo,sr)
    return float(np.sum(f*p)/(np.sum(p)+1e-12))


def crest_factor(stereo):
    x=mono(stereo)
    if len(x)==0:
        return 0.0
    rms=float(np.sqrt(np.mean(x*x))+1e-12)
    return float(np.max(np.abs(x))/rms)


def decay_time(stereo, sr, threshold=0.12, frame_ms=5.0):
    x=np.abs(mono(stereo))
    if len(x)==0:
        return 0.0
    frame=max(1,int(sr*frame_ms*0.001))
    kernel=np.ones(frame)/frame
    env=np.convolve(x,kernel,mode='same')
    peak=float(np.max(env)+1e-12)
    idx=np.flatnonzero(env>=peak*float(threshold))
    if not len(idx):
        return 0.0
    return float(idx[-1]/sr)


def analyze_drum_hit(stereo, sr):
    return {
        "low_ratio_20_120":band_ratio(stereo,sr,20,120),
        "body_ratio_120_500":band_ratio(stereo,sr,120,500),
        "presence_ratio_1k_5k":band_ratio(stereo,sr,1000,5000),
        "air_ratio_7k_16k":band_ratio(stereo,sr,7000,min(16000,sr*0.49)),
        "centroid_hz":spectral_centroid(stereo,sr),
        "crest_factor":crest_factor(stereo),
        "onset_click_score":onset_click_score(stereo,sr),
        "decay_time_s":decay_time(stereo,sr),
    }
