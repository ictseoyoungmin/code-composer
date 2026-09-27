from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import sys

import numpy as np
import scipy

from code_composer.percussion import render_drum_event
from code_composer.presets import materialize_preset

OUT = Path(os.environ.get('DRUM_REPRO_OUT', 'dist/drum-byte-repro'))
OUT.mkdir(parents=True, exist_ok=True)
SR = 24000


def digest(x):
    return hashlib.sha256(np.asarray(x, dtype=np.float64).tobytes()).hexdigest()


def save(name, x):
    arr = np.asarray(x, dtype=np.float64)
    np.save(OUT / f'{name}.npy', arr, allow_pickle=False)
    return {
        'shape': list(arr.shape),
        'dtype': str(arr.dtype),
        'sha256': digest(arr),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'rms': float(np.sqrt(np.mean(arr * arr))),
    }


def cpuinfo():
    path = Path('/proc/cpuinfo')
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8', errors='ignore')
    fields = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        k, v = (part.strip() for part in line.split(':', 1))
        if k in {'vendor_id','model name','cpu family','model','stepping','flags'} and k not in fields:
            fields[k] = v
    return fields


def main():
    legacy = {'kind': 'percussion'}
    modeled = materialize_preset('drums.acoustic_kit_modeled', role='drums')
    s19 = materialize_preset('drums.s19_core_cymbal_extension', role='drums')
    arrays = {}
    for kind in ('kick','snare','hat'):
        arrays[f'legacy_{kind}'] = render_drum_event(kind, .1, SR, .8, seed=17, patch=legacy)
        arrays[f'modeled_{kind}'] = render_drum_event(kind, .1, SR, .8, seed=17, patch=modeled)
        arrays[f's19_{kind}'] = render_drum_event(kind, .1, SR, .8, seed=17, patch=s19)
    result = {name: save(name, value) for name, value in arrays.items()}
    meta = {
        'python': sys.version,
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'numpy': np.__version__,
        'scipy': scipy.__version__,
        'cpuinfo': cpuinfo(),
        'numpy_cpu_features': getattr(np.core._multiarray_umath, '__cpu_features__', {}),
        'arrays': result,
    }
    try:
        meta['ldd_python'] = subprocess.check_output(['ldd', sys.executable], text=True, stderr=subprocess.STDOUT)
    except Exception as exc:
        meta['ldd_python'] = repr(exc)
    (OUT / 'metadata.json').write_text(json.dumps(meta, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(meta, sort_keys=True))


if __name__ == '__main__':
    main()
