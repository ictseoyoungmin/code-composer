import wave
import numpy as np

from .core.ir import validate_ir
from .composition.resolve import resolve_ir
from .composition.arrange import arrange_ir
from .composition.performance import realize_performance_ir, validate_ir_performance_contract
from .audio.synth import equal_power_pan
from .audio.instrument import synth_patch_note
from .audio.engines import engine_for_patch
from .audio.dsp import stereo_delay, simple_reverb, soft_limit, apply_pan
from .audio.percussion import render_drum_event
from .mix.mixer import mix_graph, validate_mix_graph
from .core.constraints import enforce_forbidden_track_events
from .validation_contracts import validate_runtime_extensions

def _timeline_size(ir, sr, beat_s):
    tail_s = float(ir["mix"].get("tail_seconds", 1.0))
    # Each instrument engine owns any tail beyond symbolic note-off.
    for patch in ir.get("instruments",{}).values():
        tail_s=max(tail_s,float(engine_for_patch(patch).tail_seconds(patch)))
    last_beat = 0.0
    for track in ir["tracks"]:
        for ev in track.get("events", []):
            last_beat = max(last_beat, ev["start_beat"] + ev["duration_beats"])
    return max(1, int((last_beat * beat_s + tail_s) * sr))

def _render_dry_track(ir, track, n, sr, beat_s, graph_mode=False):
    patch = ir["instruments"][track["instrument"]]
    buf = np.zeros((n, 2), dtype=np.float64)

    # S18: track gain is a fader, not a performance control. Instrument
    # velocity/excitation must therefore be rendered independently from the
    # track-level level control in both legacy and graph-mode projects.
    #
    # Graph-mode gain remains owned by mix_graph(). Legacy track gain is
    # applied once, after instrument rendering/post-processing and legacy
    # insert FX, so changing only track.gain is a deterministic linear-amplitude
    # change and cannot alter instrument timbre.
    legacy_gain = 1.0 if graph_mode else float(track.get("gain", 1.0))
    legacy_pan = 0.0 if graph_mode else float(track.get("pan", 0.0))
    render_gain = 1.0

    # S19: track pan is a mixer-level stereo-image control, not an
    # instrument/event pan fallback. Render the instrument at its authored
    # intrinsic stereo image first; explicit event pan remains event-local.
    # Legacy track pan is applied once after instrument post-processing and
    # legacy insert FX with the same stereo-balance operator used by graph
    # routing. This avoids collapsing stereo instruments to mono merely because
    # a track or S15 role pan offset is non-zero.
    engine = engine_for_patch(patch)
    stateful = engine.render_track(
        track.get("events", []), n, sr, patch, beat_s, gain=render_gain, pan=0.0
    )
    if stateful is not None:
        buf = stateful
    else:
        for event_index, ev in enumerate(track.get("events", [])):
            start = int(ev["start_beat"] * beat_s * sr)
            duration_s = ev["duration_beats"] * beat_s

            if ev.get("event_type") == "drum":
                seed = int(ir["meta"].get("global_seed", 0)) + event_index * 7919
                stereo = render_drum_event(
                    ev["drum"], duration_s, sr,
                    float(ev.get("velocity", 0.8)),
                    seed=seed,
                    pan=ev.get("pan", 0.0),
                    patch=patch,
                    articulation=ev.get("articulation"),
                    strike_force=ev.get("strike_force"),
                    strike_position=ev.get("strike_position"),
                )
            else:
                amp = float(ev.get("velocity", 0.8))
                stereo = synth_patch_note(
                    ev["midi"], duration_s, sr, patch, velocity=amp,
                    performance=ev.get("performance")
                )
                event_pan = float(ev.get("pan", 0.0))
                if abs(event_pan) > 1e-9:
                    mono = 0.5 * (stereo[:, 0] + stereo[:, 1])
                    stereo = equal_power_pan(mono, event_pan)

            end = min(len(buf), start + len(stereo))
            if end > start:
                buf[start:end] += stereo[:end-start]

    buf = engine.post_process_track(buf, sr, patch, track.get("events", []), beat_s)

    # Legacy-only track insert FX.
    if not graph_mode:
        fx = track.get("fx", {})
        if fx.get("delay"):
            cfg = fx["delay"]
            buf = stereo_delay(
                buf, sr,
                cfg.get("time", 0.24),
                cfg.get("feedback", 0.22),
                cfg.get("repeats", 3),
                cfg.get("cross", 0.55),
            )
        if fx.get("reverb"):
            buf = simple_reverb(buf, sr)
        buf = apply_pan(buf, legacy_pan)
        buf *= legacy_gain

    return buf

def render(ir: dict, out_path: str):
    validate_ir(ir)
    validate_runtime_extensions(ir)
    validate_ir_performance_contract(ir)
    graph0 = ir.get("mix", {}).get("graph")
    if graph0 is not None:
        validate_mix_graph(graph0, {t.get("id") for t in ir["tracks"]})
    if ir.get("arrangement") and not ir.get("arrangement_resolved"):
        ir = arrange_ir(ir)
    ir = resolve_ir(ir)
    if ir.get("performance_ir") and not ir.get("performance_resolved"):
        ir = realize_performance_ir(ir)
    ir["tracks"] = enforce_forbidden_track_events(ir.get("tracks", []), ir)

    sr = int(ir["meta"].get("sample_rate", 44100))
    bpm = float(ir["transport"]["bpm"])
    beat_s = 60.0 / bpm
    n = _timeline_size(ir, sr, beat_s)

    graph = ir.get("mix", {}).get("graph")
    graph_mode = bool(graph)

    dry_tracks = {}
    for track in ir["tracks"]:
        dry_tracks[track["id"]] = _render_dry_track(
            ir, track, n, sr, beat_s, graph_mode=graph_mode
        )

    if graph_mode:
        master, mix_report = mix_graph(dry_tracks, sr, graph, ir=ir)
        ir["mix_resolved"] = mix_report
    else:
        master = np.zeros((n, 2), dtype=np.float64)
        for buf in dry_tracks.values():
            master += buf
        master = soft_limit(
            master,
            drive=ir["mix"].get("drive", 1.4),
            ceiling=ir["mix"].get("ceiling", 0.93),
        )

    pcm = (np.clip(master, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

    return master, sr, ir
