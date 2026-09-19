import numpy as np

def spectral_centroid(stereo, sr):
    if len(stereo)==0:
        return 0.0
    mono=0.5*(stereo[:,0]+stereo[:,1])
    window=np.hanning(len(mono))
    spec=np.abs(np.fft.rfft(mono*window))
    freqs=np.fft.rfftfreq(len(mono),1/sr)
    denom=np.sum(spec)
    return float(np.sum(spec*freqs)/denom) if denom>0 else 0.0

def stereo_width(stereo):
    if len(stereo)==0:
        return 0.0
    mid=0.5*(stereo[:,0]+stereo[:,1])
    side=0.5*(stereo[:,0]-stereo[:,1])
    mid_rms=float(np.sqrt(np.mean(mid**2)))
    side_rms=float(np.sqrt(np.mean(side**2)))
    return side_rms/(mid_rms+1e-12)

def waveform_rms(stereo):
    return float(np.sqrt(np.mean(stereo**2))) if len(stereo) else 0.0

def compare_patches(a,b):
    n=min(len(a),len(b))
    if n==0:
        return {"correlation":1.0,"mean_abs_delta":0.0}
    am=0.5*(a[:n,0]+a[:n,1])
    bm=0.5*(b[:n,0]+b[:n,1])
    if np.std(am)<1e-12 or np.std(bm)<1e-12:
        corr=1.0 if np.allclose(am,bm) else 0.0
    else:
        corr=float(np.corrcoef(am,bm)[0,1])
    return {
        "correlation":corr,
        "mean_abs_delta":float(np.mean(np.abs(am-bm)))
    }
