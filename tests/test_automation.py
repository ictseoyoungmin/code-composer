import json
from pathlib import Path
import numpy as np

from code_composer.mix.automation import evaluate_lane
from code_composer.mix.mixer import mix_graph

def run():
    lane={"id":"x","target":"master.gain","points":[{"beat":0,"value":1.0},{"beat":2,"value":0.5,"curve":"smooth"},{"beat":4,"value":1.0,"curve":"smooth"}]}
    vals=evaluate_lane(lane,np.array([0.0,1.0,2.0,3.0,4.0]))
    assert vals[0]==1.0 and abs(vals[2]-0.5)<1e-12 and vals[-1]==1.0

    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/mix_ir.json").read_text(encoding="utf-8"))
    sr=4000; n=sr
    t=np.arange(n)/sr
    tone=np.sin(2*np.pi*220*t)*0.08
    pulse=np.zeros(n); pulse[::400]=0.5
    tracks={
      "lead":np.stack([tone,tone],1),"pad":np.stack([tone,tone],1),"arp":np.stack([tone,tone],1),
      "bass":np.stack([tone,tone],1),"drums":np.stack([pulse,pulse],1)}
    base,_=mix_graph(tracks,sr,ir["mix"]["graph"],ir=ir)
    for target in ("track.lead.gain","bus.music.gain","master.gain"):
        cand=json.loads(json.dumps(ir))
        cand["automation"]=[{"id":"a","target":target,"mode":"multiply","points":[{"beat":0,"value":0.5},{"beat":100,"value":0.5}]}]
        out,_=mix_graph(tracks,sr,cand["mix"]["graph"],ir=cand)
        assert np.sqrt(np.mean(out*out)) < np.sqrt(np.mean(base*base))


def test_regression():
    run()
