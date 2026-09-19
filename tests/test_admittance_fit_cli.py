import json
from pathlib import Path
import subprocess, sys
import numpy as np
from scipy.io import wavfile

from code_composer.audio.bridge_admittance_fit import impulse_response_from_profile


def test_admittance_fit_cli_emits_valid_profile(tmp_path):
    sr=48000
    p={"format":"code-composer-bridge-admittance-era/v1","method":"era","reference_sample_rate_hz":sr,"order":4,
       "poles":[],"residues":[],"direct":0.0,"output_scale":1.0,"stabilized_poles":0,"hankel_rows":48,"hankel_cols":48,"source":{}}
    for f,r,a in [(300,.997,.1),(2400,.985,.04)]:
        z=r*np.exp(1j*2*np.pi*f/sr); p["poles"] += [[z.real,z.imag],[z.real,-z.imag]]; p["residues"] += [[a/2,0],[a/2,0]]
    y=impulse_response_from_profile(p,4096).astype(np.float32)
    wav=tmp_path/"bridge_ir.wav"; out=tmp_path/"profile.json"
    wavfile.write(wav,sr,y)
    cmd=[sys.executable,"-m","code_composer.app.admittance_fit_cli",str(wav),str(out),"--order","4","--source-id","synthetic-test"]
    cp=subprocess.run(cmd,check=True,capture_output=True,text=True)
    d=json.loads(out.read_text())
    assert d["order"]==4 and d["source"]["source_id"]=="synthetic-test"
    assert json.loads(cp.stdout)["output"]==str(out)


def test_admittance_fit_cli_main_direct(tmp_path, capsys):
    from code_composer.app.admittance_fit_cli import main
    sr=48000
    p={"format":"code-composer-bridge-admittance-era/v1","method":"era","reference_sample_rate_hz":sr,"order":4,
       "poles":[],"residues":[],"direct":0.0,"output_scale":1.0}
    for f,r,a in [(320,.997,.1),(2200,.985,.04)]:
        z=r*np.exp(1j*2*np.pi*f/sr); p["poles"] += [[z.real,z.imag],[z.real,-z.imag]]; p["residues"] += [[a/2,0],[a/2,0]]
    wav=tmp_path/'bridge.wav'; out=tmp_path/'fit.json'
    wavfile.write(wav,sr,impulse_response_from_profile(p,4096).astype(np.float32))
    assert main([str(wav),str(out),'--order','4','--source-id','direct-test'])==0
    msg=json.loads(capsys.readouterr().out)
    assert msg['order']==4 and Path(msg['output'])==out
