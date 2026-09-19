import numpy as np

def _points(lane):
    pts=sorted(lane["points"],key=lambda p:float(p["beat"]))
    xs=np.asarray([float(p["beat"]) for p in pts],dtype=np.float64)
    ys=np.asarray([float(p["value"]) for p in pts],dtype=np.float64)
    curves=[p.get("curve","linear") for p in pts]
    return xs,ys,curves

def evaluate_lane(lane,beats):
    beats=np.asarray(beats,dtype=np.float64)
    xs,ys,curves=_points(lane)
    if len(xs)==1:
        return np.full_like(beats,ys[0])
    idx=np.searchsorted(xs,beats,side="right")-1
    idx=np.clip(idx,0,len(xs)-2)
    x0=xs[idx]; x1=xs[idx+1]
    y0=ys[idx]; y1=ys[idx+1]
    u=np.clip((beats-x0)/np.maximum(x1-x0,1e-12),0.0,1.0)
    smooth=np.fromiter((curves[i+1]=="smooth" for i in idx),dtype=bool,count=len(idx))
    us=u.copy()
    v=u[smooth]
    us[smooth]=v*v*(3.0-2.0*v)
    out=y0+(y1-y0)*us
    out=np.where(beats<=xs[0],ys[0],out)
    out=np.where(beats>=xs[-1],ys[-1],out)
    return out

def compile_automation(ir,n_samples,sr):
    bpm=float(ir["transport"]["bpm"])
    beat_s=60.0/bpm
    beats=np.arange(n_samples,dtype=np.float64)/(sr*beat_s)
    return {
        lane["id"]:{
            "target":lane["target"],
            "mode":lane.get("mode","multiply"),
            "values":evaluate_lane(lane,beats)
        }
        for lane in (ir.get("automation",[]) or [])
    }

def value_at_beat(ir,lane_id,beat):
    lane=next((x for x in ir.get("automation",[]) if x["id"]==lane_id),None)
    return None if lane is None else float(evaluate_lane(lane,[beat])[0])
