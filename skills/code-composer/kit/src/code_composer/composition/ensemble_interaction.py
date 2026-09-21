from __future__ import annotations

from copy import deepcopy

from ..agent.performance_ir import PerformanceIR, performance_ir_from_dict


class EnsembleInteractionError(ValueError):
    pass


EPS = 1e-9


def _role_for_track(track: dict) -> str | None:
    return track.get("arrangement_role") or track.get("id")


def _event_interval(event: dict) -> tuple[float, float]:
    start = float(event.get("start_beat", 0.0))
    duration = max(0.0, float(event.get("duration_beats", 0.0)))
    return start, start + duration


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _section_spans(ir: dict) -> dict[str, tuple[float, float]]:
    bpb = float(ir.get("transport", {}).get("beats_per_bar", 4.0))
    out = {}
    cursor = 0.0
    for sec in ir.get("form", []):
        sid = sec["id"]
        start = float(sec.get("start_bar", cursor / bpb)) * bpb
        end = start + float(sec["bars"]) * bpb
        out[sid] = (start, end)
        cursor = end
    return out


def _section_for_event(event: dict, spans: dict[str, tuple[float, float]]) -> str | None:
    sid = event.get("section_id")
    if sid in spans:
        return sid
    start = float(event.get("start_beat", 0.0))
    for section, (a, b) in spans.items():
        if a - EPS <= start < b - EPS:
            return section
    return None


def _active_roles(cfg: dict) -> set[str]:
    return (
        set(cfg.get("primary_roles", []))
        | set(cfg.get("secondary_roles", []))
        | set(cfg.get("decorative_roles", []))
    )


def _num(v, name, lo, hi):
    if isinstance(v, bool):
        raise EnsembleInteractionError(f"{name} must be numeric")
    try:
        x = float(v)
    except Exception as exc:
        raise EnsembleInteractionError(f"{name} must be numeric") from exc
    if x < lo or x > hi:
        raise EnsembleInteractionError(f"{name} must be in [{lo}, {hi}]")
    return x


def validate_ensemble_interaction_contract(
    ir: dict,
    performance_ir: PerformanceIR | dict,
) -> None:
    perf = (
        performance_ir
        if isinstance(performance_ir, PerformanceIR)
        else performance_ir_from_dict(performance_ir)
    )
    known_roles = {_role_for_track(t) for t in ir.get("tracks", [])}
    known_roles.discard(None)

    for sid, cfg in perf.orchestration_sections.items():
        interaction = cfg.get("ensemble_interaction")
        if interaction is None:
            continue
        if not isinstance(interaction, dict):
            raise EnsembleInteractionError(
                f"section {sid}: ensemble_interaction must be an object"
            )
        allowed = {
            "enabled",
            "leader_role",
            "timing_offsets_ms",
            "overlap_velocity_scales",
            "role_velocity_scales",
            "targeted_onset_yields",
        }
        unknown = set(interaction) - allowed
        if unknown:
            raise EnsembleInteractionError(
                f"section {sid}: ensemble_interaction unknown field(s): {sorted(unknown)}"
            )
        enabled = interaction.get("enabled", True)
        if not isinstance(enabled, bool):
            raise EnsembleInteractionError(
                f"section {sid}: ensemble_interaction.enabled must be boolean"
            )
        if not enabled:
            continue

        active = _active_roles(cfg)
        leader = interaction.get("leader_role")
        if not isinstance(leader, str) or not leader:
            raise EnsembleInteractionError(
                f"section {sid}: ensemble_interaction.leader_role must be non-empty string"
            )
        if leader not in active:
            raise EnsembleInteractionError(
                f"section {sid}: ensemble leader {leader} must be an active role"
            )
        if known_roles and leader not in known_roles:
            raise EnsembleInteractionError(
                f"section {sid}: ensemble leader {leader} has no track"
            )

        timing = interaction.get("timing_offsets_ms", {})
        if not isinstance(timing, dict):
            raise EnsembleInteractionError(
                f"section {sid}: timing_offsets_ms must be an object"
            )
        for role, value in timing.items():
            if role not in active:
                raise EnsembleInteractionError(
                    f"section {sid}: timing offset role {role} must be active"
                )
            _num(value, f"section {sid} timing offset {role}", -30.0, 30.0)

        scales = interaction.get("overlap_velocity_scales", {})
        if not isinstance(scales, dict):
            raise EnsembleInteractionError(
                f"section {sid}: overlap_velocity_scales must be an object"
            )
        for role, value in scales.items():
            if role not in active:
                raise EnsembleInteractionError(
                    f"section {sid}: overlap-yield role {role} must be active"
                )
            if role == leader:
                raise EnsembleInteractionError(
                    f"section {sid}: leader role cannot yield to itself"
                )
            _num(value, f"section {sid} overlap velocity scale {role}", 0.5, 1.0)

        role_scales = interaction.get("role_velocity_scales", {})
        if not isinstance(role_scales, dict):
            raise EnsembleInteractionError(
                f"section {sid}: role_velocity_scales must be an object"
            )
        for role, value in role_scales.items():
            if role not in active:
                raise EnsembleInteractionError(
                    f"section {sid}: role velocity scale role {role} must be active"
                )
            _num(value, f"section {sid} role velocity scale {role}", 0.5, 1.0)

        targeted = interaction.get("targeted_onset_yields", [])
        if not isinstance(targeted, list):
            raise EnsembleInteractionError(
                f"section {sid}: targeted_onset_yields must be an array"
            )
        for i, rule in enumerate(targeted):
            prefix = f"section {sid} targeted_onset_yields[{i}]"
            if not isinstance(rule, dict):
                raise EnsembleInteractionError(f"{prefix} must be an object")
            allowed_rule = {
                "leader_role", "leader_event_selector", "window_ms",
                "support_velocity_scales",
            }
            unknown_rule = set(rule) - allowed_rule
            if unknown_rule:
                raise EnsembleInteractionError(
                    f"{prefix} unknown field(s): {sorted(unknown_rule)}"
                )
            rule_leader = rule.get("leader_role")
            if not isinstance(rule_leader, str) or not rule_leader:
                raise EnsembleInteractionError(f"{prefix}.leader_role must be non-empty string")
            if rule_leader not in active:
                raise EnsembleInteractionError(f"{prefix}.leader_role must be active")
            if known_roles and rule_leader not in known_roles:
                raise EnsembleInteractionError(f"{prefix}.leader_role has no track")
            selector = rule.get("leader_event_selector", {})
            if not isinstance(selector, dict):
                raise EnsembleInteractionError(f"{prefix}.leader_event_selector must be object")
            selector_unknown = set(selector) - {"event_type", "drums"}
            if selector_unknown:
                raise EnsembleInteractionError(
                    f"{prefix}.leader_event_selector unknown field(s): {sorted(selector_unknown)}"
                )
            event_type = selector.get("event_type")
            if event_type is not None and (not isinstance(event_type, str) or not event_type):
                raise EnsembleInteractionError(f"{prefix}.leader_event_selector.event_type must be non-empty string")
            drums = selector.get("drums")
            if drums is not None:
                if not isinstance(drums, list) or not drums or any(not isinstance(x, str) or not x for x in drums):
                    raise EnsembleInteractionError(f"{prefix}.leader_event_selector.drums must be non-empty string array")
                if len(drums) != len(set(drums)):
                    raise EnsembleInteractionError(f"{prefix}.leader_event_selector.drums contains duplicates")
                if event_type not in (None, "drum"):
                    raise EnsembleInteractionError(f"{prefix}.leader_event_selector.drums requires event_type drum")
            _num(rule.get("window_ms"), f"{prefix}.window_ms", 10.0, 250.0)
            support = rule.get("support_velocity_scales", {})
            if not isinstance(support, dict) or not support:
                raise EnsembleInteractionError(f"{prefix}.support_velocity_scales must be non-empty object")
            for role, value in support.items():
                if role not in active:
                    raise EnsembleInteractionError(f"{prefix}.support_velocity_scales role {role} must be active")
                if role == rule_leader:
                    raise EnsembleInteractionError(f"{prefix}: leader role cannot yield to itself")
                _num(value, f"{prefix}.support_velocity_scales.{role}", 0.5, 1.0)

    ensemble = perf.realization.get("ensemble")
    if ensemble is None:
        return
    if not isinstance(ensemble, dict):
        raise EnsembleInteractionError("realization.ensemble must be an object")
    allowed = {"enabled", "role_pan_offsets"}
    unknown = set(ensemble) - allowed
    if unknown:
        raise EnsembleInteractionError(
            f"realization.ensemble unknown field(s): {sorted(unknown)}"
        )
    enabled = ensemble.get("enabled", True)
    if not isinstance(enabled, bool):
        raise EnsembleInteractionError("realization.ensemble.enabled must be boolean")
    if not enabled:
        return
    pans = ensemble.get("role_pan_offsets", {})
    if not isinstance(pans, dict):
        raise EnsembleInteractionError(
            "realization.ensemble.role_pan_offsets must be object"
        )
    for role, value in pans.items():
        if known_roles and role not in known_roles:
            raise EnsembleInteractionError(
                f"realization.ensemble.role_pan_offsets references unknown role {role}"
            )
        _num(value, f"realization.ensemble.role_pan_offsets.{role}", -0.5, 0.5)


def _is_control_event(event: dict) -> bool:
    et = event.get("event_type")
    return isinstance(et, str) and et.endswith("_control")


def _selector_matches(event: dict, selector: dict) -> bool:
    if _is_control_event(event):
        return False
    event_type = selector.get("event_type")
    if event_type is not None and event.get("event_type") != event_type:
        return False
    drums = selector.get("drums")
    if drums is not None and event.get("drum") not in set(drums):
        return False
    return True


def _selected_onsets(
    tracks: list[dict], sid: str, spans: dict[str, tuple[float, float]], selector: dict
) -> list[float]:
    out = []
    for track in tracks:
        for event in track.get("events", []):
            if _section_for_event(event, spans) != sid:
                continue
            if _selector_matches(event, selector):
                out.append(float(event.get("start_beat", 0.0)))
    return sorted(out)


def _nearest_onset_scale(start_beat: float, onsets: list[float], window_beats: float, authored_scale: float) -> tuple[float, float | None]:
    if not onsets or window_beats <= EPS:
        return 1.0, None
    nearest = min(abs(start_beat - x) for x in onsets)
    if nearest > window_beats + EPS:
        return 1.0, nearest
    proximity = max(0.0, min(1.0, 1.0 - nearest / window_beats))
    effective = 1.0 - proximity * (1.0 - authored_scale)
    return effective, nearest


def _leader_intervals(track: dict, sid: str, spans: dict[str, tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for event in track.get("events", []):
        if _section_for_event(event, spans) != sid:
            continue
        a, b = _event_interval(event)
        if b > a + EPS:
            out.append((a, b))
    return out


def _overlap_ratio(event: dict, intervals: list[tuple[float, float]]) -> float:
    a0, a1 = _event_interval(event)
    duration = max(a1 - a0, EPS)
    shared = sum(_overlap(a0, a1, b0, b1) for b0, b1 in intervals)
    return max(0.0, min(1.0, shared / duration))


def _apply_pan_offsets(out: dict, perf: PerformanceIR, report: dict) -> None:
    ensemble = perf.realization.get("ensemble", {})
    if not isinstance(ensemble, dict) or not ensemble.get("enabled", True):
        return
    offsets = ensemble.get("role_pan_offsets", {})
    if not offsets:
        return
    graph = out.get("mix", {}).get("graph")
    applied = {}
    for track in out.get("tracks", []):
        role = _role_for_track(track)
        if role not in offsets:
            continue
        offset = float(offsets[role])
        if graph is not None and track.get("id") in graph.get("tracks", {}):
            route = graph["tracks"][track["id"]]
            base = float(route.get("pan", 0.0))
            final = max(-1.0, min(1.0, base + offset))
            route["pan"] = round(final, 6)
        else:
            base = float(track.get("pan", 0.0))
            final = max(-1.0, min(1.0, base + offset))
            track["pan"] = round(final, 6)
        applied[role] = {
            "base_pan": round(base, 6),
            "offset": round(offset, 6),
            "final_pan": round(final, 6),
        }
    if applied:
        report["role_pan_offsets"] = applied


def realize_ensemble_interaction(ir: dict) -> dict:
    if "performance_ir" not in ir:
        return deepcopy(ir)
    if ir.get("ensemble_interaction_resolved"):
        return deepcopy(ir)

    out = deepcopy(ir)
    perf = performance_ir_from_dict(out["performance_ir"])
    validate_ensemble_interaction_contract(out, perf)

    has_section_interaction = any(
        isinstance(cfg.get("ensemble_interaction"), dict)
        and cfg["ensemble_interaction"].get("enabled", True)
        for cfg in perf.orchestration_sections.values()
    )
    ensemble_cfg = perf.realization.get("ensemble", {})
    has_pan_offsets = (
        isinstance(ensemble_cfg, dict)
        and ensemble_cfg.get("enabled", True)
        and bool(ensemble_cfg.get("role_pan_offsets", {}))
    )
    if not has_section_interaction and not has_pan_offsets:
        # Preserve the complete pre-S15 surface when S15 is not authored.
        return out

    spans = _section_spans(out)
    bpm = float(out.get("transport", {}).get("bpm", 120.0))
    beat_ms = 60000.0 / max(bpm, 1e-12)
    role_tracks: dict[str, list[dict]] = {}
    for track in out.get("tracks", []):
        role = _role_for_track(track)
        if role is not None:
            role_tracks.setdefault(role, []).append(track)
    report = {"sections": {}}

    for sid, cfg in perf.orchestration_sections.items():
        interaction = cfg.get("ensemble_interaction")
        if not isinstance(interaction, dict) or not interaction.get("enabled", True):
            continue
        leader = interaction["leader_role"]
        timing = interaction.get("timing_offsets_ms", {})
        scales = interaction.get("overlap_velocity_scales", {})
        sec_start, sec_end = spans[sid]
        sec_rep = {
            "leader_role": leader,
            "leader_event_count": 0,
            "timing_adjusted_events": 0,
            "yielded_events": 0,
            "roles": {},
        }
        role_stats = {}

        # Phase 1: realize explicit inter-player timing offsets first.
        for role, tracks in role_tracks.items():
            offset_ms = float(timing.get(role, 0.0))
            adjusted = 0
            for track in tracks:
                for event in track.get("events", []):
                    if _section_for_event(event, spans) != sid:
                        continue
                    if role == leader:
                        sec_rep["leader_event_count"] += 1
                    if abs(offset_ms) <= EPS:
                        continue
                    old_start = float(event.get("start_beat", 0.0))
                    delta = offset_ms / beat_ms
                    max_start = max(
                        sec_start,
                        sec_end - max(float(event.get("duration_beats", 0.0)), 1e-9),
                    )
                    new_start = max(sec_start, min(max_start, old_start + delta))
                    event["start_beat"] = round(new_start, 9)
                    ensemble_meta = (
                        event.get("ensemble_interaction", {})
                        if isinstance(event.get("ensemble_interaction"), dict)
                        else {}
                    )
                    event["ensemble_interaction"] = {
                        **ensemble_meta,
                        "timing_offset_ms": round(offset_ms, 6),
                        "base_start_beat": round(old_start, 9),
                    }
                    adjusted += 1
            role_stats[role] = {
                "timing_offset_ms": round(offset_ms, 6),
                "timing_adjusted_events": adjusted,
                "overlap_velocity_scale": round(float(scales.get(role, 1.0)), 6),
                "yielded_events": 0,
                "mean_leader_overlap_ratio": 0.0,
            }
            sec_rep["timing_adjusted_events"] += adjusted

        # Phase 2: apply authored section role balance. This is a static
        # performance decision, not a detector-driven compressor. Controls are
        # never treated as sounding events.
        role_velocity_scales = interaction.get("role_velocity_scales", {})
        role_scaled_events = 0
        for role, tracks in role_tracks.items():
            scale = float(role_velocity_scales.get(role, 1.0))
            if scale >= 1.0 - EPS:
                continue
            for track in tracks:
                for event in track.get("events", []):
                    if _section_for_event(event, spans) != sid or _is_control_event(event):
                        continue
                    if "velocity" not in event:
                        continue
                    base_velocity = float(event.get("velocity", 0.8))
                    final = max(0.01, min(1.0, base_velocity * scale))
                    event["velocity"] = round(final, 6)
                    meta = event.get("ensemble_interaction", {}) if isinstance(event.get("ensemble_interaction"), dict) else {}
                    event["ensemble_interaction"] = {
                        **meta,
                        "role_velocity_scale": round(scale, 6),
                        "role_velocity_base": round(base_velocity, 6),
                    }
                    role_scaled_events += 1
        sec_rep["role_scaled_events"] = role_scaled_events

        # Phase 3: targeted attack ownership. Only support events whose own
        # onsets fall inside an authored window around selected leader attacks
        # yield. Already-ringing sustain is not gain-ridden or ducked.
        targeted_applied = 0
        targeted_rules_report = []
        for rule_index, rule in enumerate(interaction.get("targeted_onset_yields", [])):
            rule_leader = rule["leader_role"]
            selector = rule.get("leader_event_selector", {})
            onsets = _selected_onsets(role_tracks.get(rule_leader, []), sid, spans, selector)
            window_ms = float(rule["window_ms"])
            window_beats = window_ms / beat_ms
            per_rule = {
                "rule_index": rule_index,
                "leader_role": rule_leader,
                "leader_event_count": len(onsets),
                "window_ms": round(window_ms, 6),
                "yielded_events": 0,
            }
            for support_role, authored_scale_raw in rule["support_velocity_scales"].items():
                authored_scale = float(authored_scale_raw)
                for track in role_tracks.get(support_role, []):
                    for event in track.get("events", []):
                        if _section_for_event(event, spans) != sid or _is_control_event(event):
                            continue
                        if "velocity" not in event:
                            continue
                        start = float(event.get("start_beat", 0.0))
                        effective, distance_beats = _nearest_onset_scale(
                            start, onsets, window_beats, authored_scale
                        )
                        if effective >= 1.0 - EPS:
                            continue
                        base_velocity = float(event.get("velocity", 0.8))
                        final = max(0.01, min(1.0, base_velocity * effective))
                        event["velocity"] = round(final, 6)
                        meta = event.get("ensemble_interaction", {}) if isinstance(event.get("ensemble_interaction"), dict) else {}
                        event["ensemble_interaction"] = {
                            **meta,
                            "targeted_onset_yield": {
                                "leader_role": rule_leader,
                                "authored_velocity_scale": round(authored_scale, 6),
                                "effective_velocity_scale": round(effective, 6),
                                "distance_ms": round(float(distance_beats or 0.0) * beat_ms, 6),
                                "window_ms": round(window_ms, 6),
                                "base_velocity": round(base_velocity, 6),
                            },
                        }
                        targeted_applied += 1
                        per_rule["yielded_events"] += 1
            targeted_rules_report.append(per_rule)
        sec_rep["targeted_onset_yielded_events"] = targeted_applied
        sec_rep["targeted_onset_rules"] = targeted_rules_report

        # Phase 4: measure overlap against the shifted leader and make support
        # roles yield only for the fraction of each note that actually overlaps.
        leader_intervals = []
        for leader_track in role_tracks.get(leader, []):
            leader_intervals.extend(_leader_intervals(leader_track, sid, spans))
        for role, tracks in role_tracks.items():
            if role == leader:
                continue
            scale = float(scales.get(role, 1.0))
            if scale >= 1.0 - EPS or not leader_intervals:
                continue
            yielded = 0
            overlap_sum = 0.0
            for track in tracks:
                for event in track.get("events", []):
                    if _section_for_event(event, spans) != sid:
                        continue
                    ratio = _overlap_ratio(event, leader_intervals)
                    if ratio <= EPS:
                        continue
                    base_velocity = float(event.get("velocity", 0.8))
                    effective = 1.0 - ratio * (1.0 - scale)
                    final = max(0.01, min(1.0, base_velocity * effective))
                    event["velocity"] = round(final, 6)
                    ensemble_meta = (
                        event.get("ensemble_interaction", {})
                        if isinstance(event.get("ensemble_interaction"), dict)
                        else {}
                    )
                    event["ensemble_interaction"] = {
                        **ensemble_meta,
                        "leader_role": leader,
                        "leader_overlap_ratio": round(ratio, 6),
                        "authored_overlap_velocity_scale": round(scale, 6),
                        "effective_velocity_scale": round(effective, 6),
                        "base_velocity": round(base_velocity, 6),
                    }
                    yielded += 1
                    overlap_sum += ratio
            stats = role_stats.setdefault(
                role,
                {
                    "timing_offset_ms": round(float(timing.get(role, 0.0)), 6),
                    "timing_adjusted_events": 0,
                    "overlap_velocity_scale": round(scale, 6),
                    "yielded_events": 0,
                    "mean_leader_overlap_ratio": 0.0,
                },
            )
            stats["yielded_events"] = yielded
            stats["mean_leader_overlap_ratio"] = round(
                overlap_sum / max(yielded, 1), 6
            )
            sec_rep["yielded_events"] += yielded

        sec_rep["roles"] = {
            role: stats
            for role, stats in role_stats.items()
            if stats["timing_adjusted_events"] or stats["yielded_events"]
        }
        report["sections"][sid] = sec_rep

    _apply_pan_offsets(out, perf, report)
    out["ensemble_interaction_resolved"] = True
    out["ensemble_interaction_report"] = report
    return out


__all__ = [
    "EnsembleInteractionError",
    "validate_ensemble_interaction_contract",
    "realize_ensemble_interaction",
]
