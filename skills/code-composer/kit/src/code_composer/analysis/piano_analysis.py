import numpy as np


def spectral_centroid(stereo,sr,window_s=None):
    x=np.asarray(stereo,dtype=np.float64)
    if x.ndim==2:
        x=x.mean(axis=1)
    if window_s is not None:
        x=x[:max(1,min(len(x),int(float(window_s)*sr)))]
    if len(x)<2:
        return 0.0
    win=np.hanning(len(x))
    mag=np.abs(np.fft.rfft(x*win))
    freqs=np.fft.rfftfreq(len(x),1.0/sr)
    den=float(np.sum(mag))+1e-12
    return float(np.sum(freqs*mag)/den)


def stereo_balance(stereo):
    x=np.asarray(stereo,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=2:
        return 0.0
    l=float(np.sqrt(np.mean(x[:,0]**2))+1e-12)
    r=float(np.sqrt(np.mean(x[:,1]**2))+1e-12)
    return (r-l)/(r+l)


def tail_rms(stereo,sr,start_s):
    x=np.asarray(stereo,dtype=np.float64)
    start=min(len(x),max(0,int(float(start_s)*sr)))
    if start>=len(x):
        return 0.0
    return float(np.sqrt(np.mean(x[start:]**2)))


def onset_crest(stereo,sr,window_s=.05):
    x=np.asarray(stereo,dtype=np.float64)
    n=min(len(x),max(1,int(window_s*sr)))
    y=x[:n]
    peak=float(np.max(np.abs(y))) if len(y) else 0.0
    rms=float(np.sqrt(np.mean(y*y))+1e-12) if len(y) else 1e-12
    return peak/rms


def decay_ratio(stereo,sr,onset_window=(.05,.15),late_window=(.9,1.05)):
    x=np.asarray(stereo,dtype=np.float64)
    def _rms(win):
        i=max(0,int(float(win[0])*sr)); j=min(len(x),int(float(win[1])*sr))
        y=x[i:j]
        return float(np.sqrt(np.mean(y*y))) if len(y) else 0.0
    return _rms(late_window)/(_rms(onset_window)+1e-12)


__all__=['spectral_centroid','stereo_balance','tail_rms','onset_crest','decay_ratio']
