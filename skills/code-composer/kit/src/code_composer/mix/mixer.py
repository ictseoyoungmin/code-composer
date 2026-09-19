from copy import deepcopy
import numpy as np

from .automation import compile_automation
from ..audio.dsp import (
    apply_pan, delay_wet, reverb_wet,
    one_pole_lowpass, one_pole_highpass,
    compressor, duck, soft_limit,
)

class MixGraphError(ValueError):
    pass

def _rms(x):
    return float(np.sqrt(np.mean(x**2))) if len(x) else 0.0

def _peak(x):
    return float(np.max(np.abs(x))) if len(x) else 0.0

def validate_mix_graph(graph, track_ids):
    if not isinstance(graph, dict):
        raise MixGraphError("mix.graph must be an object")

    tracks = graph.get("tracks", {})
    buses = graph.get("buses", {})
    master = graph.get("master", {})

    if not buses:
        raise MixGraphError("mix.graph.buses must be non-empty")

    for tid in track_ids:
        if tid not in tracks:
            raise MixGraphError(f"mix graph missing track route: {tid}")
        output = tracks[tid].get("output")
        if output not in buses and output != "master":
            raise MixGraphError(f"track {tid}: unknown output bus {output}")
        for send_id in tracks[tid].get("sends", {}):
            if send_id not in buses:
                raise MixGraphError(f"track {tid}: unknown send bus {send_id}")

    for bid, bus in buses.items():
        output = bus.get("output", "master")
        if output != "master":
            raise MixGraphError(
                f"v0.7 supports bus output to master only; bus {bid} -> {output}"
            )
        if bus.get("kind", "group") not in {"group", "return"}:
            raise MixGraphError(f"bus {bid}: kind must be group or return")

    for sc in graph.get("sidechains", []):
        if sc.get("source") not in buses:
            raise MixGraphError(f"sidechain source bus missing: {sc.get('source')}")
        if sc.get("target") not in buses:
            raise MixGraphError(f"sidechain target bus missing: {sc.get('target')}")

    if "fx" in master and not isinstance(master["fx"], list):
        raise MixGraphError("mix.graph.master.fx must be a list")

def _apply_fx_chain(sig, sr, chain, wet_only_returns=False):
    out = sig
    fx_report = []
    for fx in chain or []:
        ftype = fx.get("type")
        before_peak = _peak(out)
        before_rms = _rms(out)

        if ftype == "delay":
            wet = delay_wet(
                out, sr,
                fx.get("time", 0.24),
                fx.get("feedback", 0.22),
                fx.get("repeats", 3),
                fx.get("cross", 0.55),
            )
            mix = float(fx.get("mix", 1.0 if wet_only_returns else 0.25))
            out = wet * mix if wet_only_returns else out + wet * mix

        elif ftype == "reverb":
            wet = reverb_wet(out, sr)
            mix = float(fx.get("mix", 1.0 if wet_only_returns else 0.22))
            out = wet * mix if wet_only_returns else out + wet * mix

        elif ftype == "lowpass":
            out = one_pole_lowpass(out, sr, fx.get("cutoff", 8000))

        elif ftype == "highpass":
            out = one_pole_highpass(out, sr, fx.get("cutoff", 80))

        elif ftype == "compressor":
            out, gain = compressor(
                out, sr,
                fx.get("threshold_db", -14),
                fx.get("ratio", 3.0),
                fx.get("attack_s", 0.008),
                fx.get("release_s", 0.12),
                fx.get("makeup_db", 0.0),
            )
            fx_report.append({
                "type": ftype,
                "mean_gain": float(np.mean(gain)),
                "min_gain": float(np.min(gain)),
                "before_peak": before_peak,
                "after_peak": _peak(out),
            })
            continue

        elif ftype == "limiter":
            out = soft_limit(
                out,
                drive=fx.get("drive", 1.15),
                ceiling=fx.get("ceiling", 0.93),
            )

        else:
            raise MixGraphError(f"unsupported mix FX type: {ftype}")

        fx_report.append({
            "type": ftype,
            "before_peak": before_peak,
            "after_peak": _peak(out),
            "before_rms": before_rms,
            "after_rms": _rms(out),
        })

    return out, fx_report

def mix_graph(track_buffers, sr, graph, ir=None):
    """
    Execute a deterministic routing graph.

    Inputs are dry stereo track buffers, already aligned on one timeline.
    The mixer makes no composition or arrangement decisions.
    """
    validate_mix_graph(graph, set(track_buffers))

    buses = graph["buses"]
    track_routes = graph["tracks"]
    n = max((len(x) for x in track_buffers.values()), default=1)
    automation=compile_automation(ir,n,sr) if ir is not None else {}
    def _auto(target):
        for lane in automation.values():
            if lane["target"]==target:
                return lane["values"]
        return None

    bus_inputs = {bid: np.zeros((n, 2), dtype=np.float64) for bid in buses}
    direct_master = np.zeros((n, 2), dtype=np.float64)
    track_report = {}

    # Track routing + sends.
    for tid, dry in track_buffers.items():
        route = track_routes[tid]
        sig = dry * float(route.get("gain", 1.0))
        auto=_auto(f"track.{tid}.gain")
        if auto is not None: sig=sig*auto[:,None]
        sig = apply_pan(sig, route.get("pan", 0.0))

        output = route.get("output", "master")
        if output == "master":
            direct_master += sig
        else:
            bus_inputs[output] += sig

        sends = route.get("sends", {})
        for send_bus, send_gain in sends.items():
            bus_inputs[send_bus] += sig * float(send_gain)

        track_report[tid] = {
            "dry_peak": _peak(dry),
            "post_route_peak": _peak(sig),
            "post_route_rms": _rms(sig),
            "output": output,
            "sends": deepcopy(sends),
        }

    # Sidechain source is intentionally the pre-FX bus signal so bus order
    # cannot change the result.
    sidechain_sources = {bid: buf.copy() for bid, buf in bus_inputs.items()}

    processed_buses = {}
    bus_report = {}

    for bid, cfg in buses.items():
        kind = cfg.get("kind", "group")
        sig = bus_inputs[bid] * float(cfg.get("gain", 1.0))
        auto=_auto(f"bus.{bid}.gain")
        if auto is not None: sig=sig*auto[:,None]

        duck_reports = []
        for sc in graph.get("sidechains", []):
            if sc.get("target") != bid:
                continue
            source = sidechain_sources[sc["source"]]
            if sc.get("type", "duck") != "duck":
                raise MixGraphError(f"unsupported sidechain type: {sc.get('type')}")
            sig, gain = duck(
                sig, source, sr,
                sc.get("threshold_db", -28),
                sc.get("amount_db", 7),
                sc.get("attack_s", 0.006),
                sc.get("release_s", 0.16),
            )
            duck_reports.append({
                "source": sc["source"],
                "mean_gain": float(np.mean(gain)),
                "min_gain": float(np.min(gain)),
            })

        sig, fx_report = _apply_fx_chain(
            sig, sr, cfg.get("fx", []), wet_only_returns=(kind == "return")
        )
        processed_buses[bid] = sig
        bus_report[bid] = {
            "kind": kind,
            "input_peak": _peak(bus_inputs[bid]),
            "input_rms": _rms(bus_inputs[bid]),
            "output_peak": _peak(sig),
            "output_rms": _rms(sig),
            "ducking": duck_reports,
            "fx": fx_report,
        }

    master = direct_master.copy()
    for bid, sig in processed_buses.items():
        if buses[bid].get("output", "master") == "master":
            master += sig

    pre_master_peak = _peak(master)
    pre_master_rms = _rms(master)

    master_cfg = graph.get("master", {})
    master *= float(master_cfg.get("gain", 1.0))
    auto=_auto("master.gain")
    if auto is not None: master=master*auto[:,None]
    master, master_fx_report = _apply_fx_chain(
        master, sr, master_cfg.get("fx", []), wet_only_returns=False
    )

    report = {
        "tracks": track_report,
        "buses": bus_report,
        "master": {
            "pre_fx_peak": pre_master_peak,
            "pre_fx_rms": pre_master_rms,
            "output_peak": _peak(master),
            "output_rms": _rms(master),
            "headroom_db": float(
                20.0 * np.log10(1.0 / max(_peak(master), 1e-12))
            ),
            "clipped_sample_ratio": float(np.mean(np.abs(master) >= 1.0)),
            "fx": master_fx_report,
        },
    }
    return master, report
