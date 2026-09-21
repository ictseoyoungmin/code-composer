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
from .audio.percussion import render_drum_event, apply_hi_hat_state_transitions, resolve_hi_hat_pedal_openness, render_hi_hat_pedal_control
from .mix.mixer import mix_graph, validate_mix_graph
from .core.constraints import enforce_forbidden_track_events
from .validation_contracts import validate_runtime_extensions


def _stable_text_seed(text):
    """Small process-stable text hash for deterministic render identities."""
    x=2166136261
    for byte in str(text).encode("utf-8"):
        x ^= int(byte)
        x = (x * 16777619) & 0xFFFFFFFF
    return x


def _piano_events_with_authored_attack(events, beat_s):
    """Apply explicit piano hand/chord attack offsets without changing score onsets.

    ``performance.piano_attack_offset_ms`` is authored performance intent, not
    random humanization. Controls are never moved. The canonical IR remains
    unchanged because the transform operates on render-local event copies.
    """
    out=[]
    for event in events or []:
        x=dict(event)
        if "midi" in event and event.get("event_type") not in {"piano_control","drum_control","drum"}:
            perf=event.get("performance") or {}
            offset_ms=float(perf.get("piano_attack_offset_ms",0.0)) if isinstance(perf,dict) else 0.0
            if abs(offset_ms)>1e-12:
                x["start_beat"]=float(event.get("start_beat",0.0)) + (offset_ms/1000.0)/float(beat_s)
        out.append(x)
    return out


def _piano_events_with_strike_identity(events, global_seed, track_id):
    """Attach deterministic per-strike identity without mutating canonical IR.

    Non-note controls do not consume an ordinal, so inserting pedal curves does not
    silently change the physical identity of later piano strikes.  Legacy piano
    graphs ignore these fields unless strike-identity controls are explicitly nonzero.
    """
    out=[]
    ordinal=0
    base=(int(global_seed) + _stable_text_seed(track_id) * 17) & 0xFFFFFFFF
    for event in events or []:
        x=dict(event)
        if "midi" in event and event.get("event_type") not in {"piano_control","drum_control","drum"}:
            perf=dict(event.get("performance") or {})
            perf.setdefault("piano_strike_ordinal", ordinal)
            perf.setdefault(
                "piano_strike_seed",
                int((base + ordinal * 104729 + int(event["midi"]) * 8191) & 0xFFFFFFFF),
            )
            x["performance"]=perf
            ordinal += 1
        out.append(x)
    return out

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
    render_events = track.get("events", [])
    if engine.name == "piano":
        render_events = _piano_events_with_authored_attack(render_events, beat_s)
        render_events = _piano_events_with_strike_identity(
            render_events, ir.get("meta",{}).get("global_seed",0), track.get("id","")
        )
    stateful = engine.render_track(
        render_events, n, sr, patch, beat_s, gain=render_gain, pan=0.0
    )
    if stateful is not None:
        buf = stateful
    else:
        for event_index, ev in enumerate(render_events):
            start = int(ev["start_beat"] * beat_s * sr)
            duration_s = ev["duration_beats"] * beat_s

            if ev.get("event_type") == "drum_control":
                # S27-K: the authored trajectory remains the performance event.
                # New opt-in presets may render the *physical consequence* of a
                # sufficiently fast plate contact/release, without inventing a
                # hidden foot gesture. Earlier presets remain silent here.
                graph=patch.get("drum_graph",{}) if isinstance(patch,dict) else {}
                hh_state=graph.get("hi_hat_state",{}) if isinstance(graph,dict) else {}
                pedal_audio=hh_state.get("pedal_audio",{}) if isinstance(hh_state,dict) else {}
                if not (isinstance(pedal_audio,dict) and pedal_audio.get("enabled",False)):
                    continue
                control_ordinal=sum(1 for prev in track.get("events",[])[:event_index] if prev.get("event_type")=="drum_control")
                control_seed=int(ir["meta"].get("global_seed",0))+700001+control_ordinal*104729
                stereo=render_hi_hat_pedal_control(ev,sr,beat_s,control_seed,patch)
            elif ev.get("event_type") == "drum":
                graph=patch.get("drum_graph",{}) if isinstance(patch,dict) else {}
                hh_state=graph.get("hi_hat_state",{}) if isinstance(graph,dict) else {}
                # S27-J: non-audio control events must not perturb the random
                # identity of later audible hits.  Older presets retain their
                # historical raw event-index seed contract.
                seed_index=event_index
                if isinstance(hh_state,dict) and hh_state.get("model")=="authored_persistent_openness_v3":
                    seed_index=sum(1 for prev in track.get("events",[])[:event_index] if prev.get("event_type")!="drum_control")
                seed = int(ir["meta"].get("global_seed", 0)) + seed_index * 7919
                pedal_open=None
                if isinstance(hh_state,dict) and hh_state.get("model")=="authored_persistent_openness_v3":
                    continuous=hh_state.get("continuous",{}) if isinstance(hh_state.get("continuous",{}),dict) else {}
                    pedal_open=resolve_hi_hat_pedal_openness(
                        track.get("events",[]), ev.get("start_beat",0.0),
                        continuous.get("control","hi_hat_pedal_openness"),
                    )
                stereo = render_drum_event(
                    ev["drum"], duration_s, sr,
                    float(ev.get("velocity", 0.8)),
                    seed=seed,
                    pan=ev.get("pan", 0.0),
                    patch=patch,
                    hi_hat_pedal_openness=pedal_open,
                )
                stereo = apply_hi_hat_state_transitions(
                    stereo, sr, ev["drum"], event_index,
                    track.get("events", []), beat_s, patch,
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

    buf = engine.post_process_track(buf, sr, patch, render_events, beat_s)

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
