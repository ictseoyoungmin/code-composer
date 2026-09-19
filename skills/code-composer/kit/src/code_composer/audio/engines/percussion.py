from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not (lo <= x <= hi):
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


def _seq(v, name, min_len, max_len, lo, hi):
    if not isinstance(v, list) or not (min_len <= len(v) <= max_len):
        raise InstrumentEngineValidationError(
            f"{name} must contain {min_len}..{max_len} values"
        )
    for i, item in enumerate(v):
        _num(item, f"{name}[{i}]", lo, hi)
    return v


class PercussionEngine(InstrumentEngine):
    """Validation/tail boundary for deterministic percussion patches.

    Individual drum events continue to be rendered by ``audio.percussion`` so the
    existing Music IR drum-event surface remains unchanged.
    """

    name = "percussion"
    aliases = ("drums", "drum_kit")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        raise InstrumentEngineValidationError(
            "percussion engine renders explicit drum events, not pitched notes"
        )

    def tail_seconds(self, patch: dict) -> float:
        graph = patch.get("drum_graph", {}) if isinstance(patch, dict) else {}
        realism = graph.get("realism_hardening", {}) if isinstance(graph, dict) else {}
        if not isinstance(realism, dict) or not realism.get("enabled", False):
            return 0.0
        base = max(
            float(realism.get("kick_tail_s", 0.36)),
            float(realism.get("snare_tail_s", 0.34)),
            float(realism.get("hat_tail_s", 0.13)),
        )
        articulation = graph.get("articulation_foundation", {})
        if isinstance(articulation, dict) and articulation.get("enabled", False):
            base = max(
                base,
                float(articulation.get("hat_open_tail_s", 1.15)),
                float(articulation.get("ride_bow_tail_s", 1.90)),
                float(articulation.get("ride_bell_tail_s", 1.35)),
                float(articulation.get("crash_tail_s", 2.25)),
                float(articulation.get("tom_tail_s", 0.74)),
            )
        return base

    def validate_ir_patch(self, subject: str, patch: dict) -> None:
        self._validate(subject, patch, authoring=False)

    def validate_authoring_patch(self, role: str, patch: dict) -> None:
        self._validate(role, patch, authoring=True)

    def _validate(self, subject: str, patch: dict, *, authoring: bool) -> None:
        prefix = f"sound_palette.{subject}" if authoring else f"instrument {subject}"
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"{prefix}: patch must be object")
        if patch.get("kind", "percussion") != "percussion":
            raise InstrumentEngineValidationError(f"{prefix}: kind must be percussion")
        graph = patch.get("drum_graph", {})
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(f"{prefix}: drum_graph must be object")

        # Legacy runtime patches may omit role blocks and use renderer defaults.
        if authoring:
            for name in ("kick", "snare", "hat"):
                if name not in graph or not isinstance(graph[name], dict):
                    raise InstrumentEngineValidationError(
                        f"{prefix}: drum_graph requires {name}"
                    )

        k = graph.get("kick", {})
        if k:
            _num(k.get("pitch_start_hz", 165), "kick.pitch_start_hz", 30, 800)
            _num(k.get("pitch_end_hz", 48), "kick.pitch_end_hz", 20, 180)
            _num(k.get("pitch_decay_s", .045), "kick.pitch_decay_s", .002, .5)
            _num(k.get("body_decay_s", .095), "kick.body_decay_s", .01, 1.5)
            _num(k.get("sub_decay_s", .14), "kick.sub_decay_s", .01, 2.0)
            for key in ("body_gain", "sub_gain", "click_gain", "output_gain"):
                _num(k.get(key, 0), f"kick.{key}", 0, 2)
            _num(k.get("click_hz", 2200), "kick.click_hz", 100, 12000)
            _num(k.get("drive", 1.1), "kick.drive", .1, 5)

        s = graph.get("snare", {})
        if s:
            for key, lo, hi, default in (
                ("body_hz", 60, 700, 185), ("body2_hz", 80, 1600, 335),
                ("noise_low_hz", 100, 12000, 1200), ("noise_high_hz", 500, 20000, 9000),
                ("crack_hz", 300, 12000, 2700), ("lowpass_hz", 500, 20000, 10500),
            ):
                _num(s.get(key, default), f"snare.{key}", lo, hi)
            if float(s.get("noise_low_hz", 1200)) >= float(s.get("noise_high_hz", 9000)):
                raise InstrumentEngineValidationError(
                    "snare.noise_low_hz must be below noise_high_hz"
                )
            for key in ("body_gain", "body2_gain", "noise_gain", "crack_gain", "output_gain"):
                _num(s.get(key, 0), f"snare.{key}", 0, 2)
            for key in ("body_decay_s", "noise_decay_s", "crack_decay_s"):
                _num(s.get(key, .05), f"snare.{key}", .001, 2)
            _num(s.get("drive", 1.08), "snare.drive", .1, 5)

        h = graph.get("hat", {})
        if h:
            freqs = h.get("metal_freqs", [])
            gains = h.get("metal_gains", [])
            if freqs:
                _seq(freqs, "hat.metal_freqs", 2, 8, 1000, 20000)
                if not isinstance(gains, list) or len(gains) != len(freqs):
                    raise InstrumentEngineValidationError(
                        "hat.metal_gains must match metal_freqs"
                    )
                for i, g in enumerate(gains):
                    _num(g, f"hat.metal_gains[{i}]", 0, 2)
            for key in ("metal_gain", "noise_gain", "output_gain"):
                _num(h.get(key, 0), f"hat.{key}", 0, 2)
            _num(h.get("decay_s", .03), "hat.decay_s", .002, 1)
            hp = _num(h.get("noise_highpass_hz", 5200), "hat.noise_highpass_hz", 100, 19000)
            lp = _num(h.get("noise_lowpass_hz", 15000), "hat.noise_lowpass_hz", 500, 20000)
            if hp >= lp:
                raise InstrumentEngineValidationError(
                    "hat.noise_highpass_hz must be below noise_lowpass_hz"
                )
            _num(h.get("output_highpass_hz", 4300), "hat.output_highpass_hz", 100, 19000)
            _num(h.get("drive", 1.04), "hat.drive", .1, 5)

        r = graph.get("realism_hardening", {})
        if not r:
            return
        if not isinstance(r, dict):
            raise InstrumentEngineValidationError("drum_graph.realism_hardening must be object")
        if "enabled" in r and not isinstance(r["enabled"], bool):
            raise InstrumentEngineValidationError("realism_hardening.enabled must be boolean")
        for key, lo, hi, default in (
            ("kick_tail_s", .12, 1.2, .36),
            ("snare_tail_s", .10, 1.2, .34),
            ("hat_tail_s", .05, .8, .13),
            ("strike_variation", 0, .25, .05),
            ("velocity_brightness", 0, 1.5, .45),
            ("kick_tension_shift_cents", 0, 240, 65),
            ("kick_tension_decay_s", .005, .25, .035),
            ("kick_beater_noise_gain", 0, .5, .055),
            ("snare_wire_delay_s", 0, .03, .0025),
            ("snare_wire_rattle_hz", 8, 220, 72),
            ("snare_wire_decay_s", .02, 1.0, .18),
            ("snare_wire_gain", 0, 1.5, .38),
            ("hat_mode_jitter", 0, .04, .006),
            ("hat_decay_velocity_scale", 0, 2.0, .55),
        ):
            _num(r.get(key, default), f"realism_hardening.{key}", lo, hi)

        if "kick_mode_ratios" in r:
            _seq(r["kick_mode_ratios"], "realism_hardening.kick_mode_ratios", 3, 8, .5, 8)
        if "kick_mode_gains" in r:
            gains = _seq(r["kick_mode_gains"], "realism_hardening.kick_mode_gains", 3, 8, 0, 2)
            ratios = r.get("kick_mode_ratios", [1.0, 1.594, 2.136, 2.296, 2.653])
            if len(gains) != len(ratios):
                raise InstrumentEngineValidationError(
                    "realism_hardening.kick_mode_gains must match kick_mode_ratios"
                )
        if "snare_mode_ratios" in r:
            _seq(r["snare_mode_ratios"], "realism_hardening.snare_mode_ratios", 3, 8, .5, 8)
        if "snare_mode_gains" in r:
            gains = _seq(r["snare_mode_gains"], "realism_hardening.snare_mode_gains", 3, 8, 0, 2)
            ratios = r.get("snare_mode_ratios", [1.0, 1.47, 1.93, 2.54])
            if len(gains) != len(ratios):
                raise InstrumentEngineValidationError(
                    "realism_hardening.snare_mode_gains must match snare_mode_ratios"
                )

        core = graph.get("acoustic_core_hardening", {})
        if core:
            if not isinstance(core, dict):
                raise InstrumentEngineValidationError("drum_graph.acoustic_core_hardening must be object")
            if "enabled" in core and not isinstance(core["enabled"], bool):
                raise InstrumentEngineValidationError("acoustic_core_hardening.enabled must be boolean")
            for key, lo, hi, default in (
                ("kick_head_pair_split", .002, .12, .038),
                ("kick_resonant_head_gain", 0, 1.2, .34),
                ("kick_shell_gain", 0, .5, .055),
                ("kick_cavity_hz", 25, 180, 63),
                ("kick_cavity_gain", 0, .6, .16),
                ("kick_contact_gain", 0, .4, .075),
                ("snare_head_pair_split", .002, .12, .030),
                ("snare_resonant_head_gain", 0, 1.2, .42),
                ("snare_shell_gain", 0, .5, .11),
                ("snare_cavity_hz", 40, 400, 116),
                ("snare_cavity_gain", 0, .5, .075),
                ("snare_wire_driver_hz", 20, 500, 115),
                ("snare_wire_delay_s", 0, .03, .0018),
                ("snare_wire_decay_s", .02, 1.0, .24),
                ("snare_wire_coupling_gain", 0, 1.5, .44),
                ("tom_head_pair_split", .002, .12, .028),
                ("tom_resonant_head_gain", 0, 1.2, .36),
                ("tom_shell_gain", 0, .5, .095),
                ("tom_cavity_gain", 0, .5, .095),
                ("cymbal_mode_count", 12, 64, 34),
                ("cymbal_pair_spread", .0005, .03, .0058),
                ("cymbal_velocity_brightness", 0, 1.5, .62),
                ("cymbal_noise_decay_ratio", .1, 1.5, .54),
                ("cymbal_modal_gain", 0, 1.5, .78),
                ("cymbal_noise_gain", 0, .8, .16),
            ):
                _num(core.get(key, default), f"acoustic_core_hardening.{key}", lo, hi)
            for key, default in (("tom_high_cavity_hz",205),("tom_mid_cavity_hz",148),("tom_floor_cavity_hz",92)):
                _num(core.get(key, default), f"acoustic_core_hardening.{key}", 35, 500)
            if core.get("enabled", False):
                art = graph.get("articulation_foundation", {})
                if not isinstance(art, dict) or not art.get("enabled", False):
                    raise InstrumentEngineValidationError(
                        "acoustic_core_hardening requires articulation_foundation.enabled"
                    )

        polish = graph.get("voicing_polish", {})
        if polish:
            if not isinstance(polish, dict):
                raise InstrumentEngineValidationError("drum_graph.voicing_polish must be object")
            if "enabled" in polish and not isinstance(polish["enabled"], bool):
                raise InstrumentEngineValidationError("voicing_polish.enabled must be boolean")
            for key, lo, hi, default in (
                ("kick_contact_lowpass_hz", 800, 10000, 3900),
                ("kick_contact_gain_scale", .2, 1.5, .82),
                ("kick_body_gain_scale", .5, 1.5, 1.04),
                ("snare_wire_lowpass_hz", 3000, 14000, 9200),
                ("snare_impact_lowpass_hz", 3000, 14000, 8600),
                ("snare_body_gain_scale", .5, 1.6, 1.06),
                ("snare_wire_gain_scale", .2, 1.5, .84),
                ("snare_impact_gain_scale", .2, 1.5, .82),
                ("tom_impact_lowpass_hz", 1800, 12000, 6200),
                ("tom_impact_gain_scale", .2, 1.5, .80),
                ("tom_body_gain_scale", .5, 1.5, 1.03),
                ("cymbal_contact_lowpass_hz", 3000, 14000, 9600),
                ("cymbal_modal_gain_scale", .3, 1.5, .90),
                ("cymbal_noise_gain_scale", .3, 1.8, 1.10),
                ("cymbal_contact_gain_scale", .2, 1.5, .72),
                ("cymbal_hf_damping_hz", 4000, 14000, 9000),
                ("cymbal_hf_decay_ratio", .08, 1.0, .34),
                ("cymbal_attack_glue_ms", .05, 5.0, .70),
                ("cymbal_initial_gain", .3, 1.0, .82),
            ):
                _num(polish.get(key, default), f"voicing_polish.{key}", lo, hi)
            if polish.get("enabled", False):
                core_cfg = graph.get("acoustic_core_hardening", {})
                if not isinstance(core_cfg, dict) or not core_cfg.get("enabled", False):
                    raise InstrumentEngineValidationError(
                        "voicing_polish requires acoustic_core_hardening.enabled"
                    )

        presence = graph.get("cymbal_presence_hardening", {})
        if presence:
            if not isinstance(presence, dict):
                raise InstrumentEngineValidationError("drum_graph.cymbal_presence_hardening must be object")
            if "enabled" in presence and not isinstance(presence["enabled"], bool):
                raise InstrumentEngineValidationError("cymbal_presence_hardening.enabled must be boolean")
            for key, lo, hi, default in (
                ("modal_body_gain_scale", .5, 2.0, 1.28),
                ("wash_gain_scale", .05, 1.5, .55),
                ("contact_gain_scale", .4, 2.0, 1.22),
                ("wash_low_hz", 500, 5000, 1800),
                ("wash_mid_hz", 1800, 8000, 4800),
                ("wash_high_hz", 5000, 14000, 9800),
                ("wash_low_band_mix", 0, 1.5, .68),
                ("wash_high_band_mix", 0, 1.5, .32),
                ("wash_envelope_hz", 20, 800, 170),
                ("wash_modal_correlation", 0, 1, .82),
                ("wash_attack_ms", .1, 30, 5.5),
                ("presence_low_hz", 500, 6000, 1800),
                ("presence_high_hz", 3000, 14000, 7600),
                ("presence_decay_s", .01, .8, .115),
                ("presence_gain", 0, 1.5, .42),
                ("hat_output_gain_scale", .5, 3.2, 1.12),
                ("ride_output_gain_scale", .5, 3.2, 1.20),
                ("crash_output_gain_scale", .5, 3.2, 1.28),
            ):
                _num(presence.get(key, default), f"cymbal_presence_hardening.{key}", lo, hi)
            if presence.get("enabled", False):
                polish_cfg = graph.get("voicing_polish", {})
                if not isinstance(polish_cfg, dict) or not polish_cfg.get("enabled", False):
                    raise InstrumentEngineValidationError(
                        "cymbal_presence_hardening requires voicing_polish.enabled"
                    )

        perf = graph.get("performance_timbre", {})
        if perf:
            if not isinstance(perf, dict):
                raise InstrumentEngineValidationError("drum_graph.performance_timbre must be object")
            if "enabled" in perf and not isinstance(perf["enabled"], bool):
                raise InstrumentEngineValidationError("performance_timbre.enabled must be boolean")
            for key, lo, hi, default in (
                ("force_neutral", 0.0, 1.0, .5),
                ("force_brightness", 0.0, 1.5, .72),
                ("force_attack", 0.0, .8, .18),
                ("membrane_edge_brightness", 0.0, 1.2, .46),
                ("cymbal_edge_darkening", 0.0, .8, .24),
                ("cymbal_edge_tail_boost", 0.0, .8, .30),
                ("kick_edge_brightness", 0.0, .8, .16),
            ):
                _num(perf.get(key, default), f"performance_timbre.{key}", lo, hi)
            if "rms_preserve" in perf and not isinstance(perf["rms_preserve"], bool):
                raise InstrumentEngineValidationError("performance_timbre.rms_preserve must be boolean")
            if perf.get("enabled", False):
                polish_cfg = graph.get("voicing_polish", {})
                if not isinstance(polish_cfg, dict) or not polish_cfg.get("enabled", False):
                    raise InstrumentEngineValidationError(
                        "performance_timbre requires voicing_polish.enabled"
                    )

        a = graph.get("articulation_foundation", {})
        if a:
            if not isinstance(a, dict):
                raise InstrumentEngineValidationError("drum_graph.articulation_foundation must be object")
            if "enabled" in a and not isinstance(a["enabled"], bool):
                raise InstrumentEngineValidationError("articulation_foundation.enabled must be boolean")
            if a.get("enabled", False):
                for name in ("ride", "crash", "tom_high", "tom_mid", "tom_floor"):
                    if name not in graph or not isinstance(graph[name], dict):
                        raise InstrumentEngineValidationError(
                            f"{prefix}: articulation foundation requires drum_graph.{name}"
                        )
            for key, lo, hi, default in (
                ("snare_ghost_tail_s", .05, .8, .24),
                ("snare_rimshot_tail_s", .05, .8, .24),
                ("snare_cross_stick_tail_s", .04, .5, .16),
                ("hat_half_open_tail_s", .10, 1.5, .52),
                ("hat_open_tail_s", .20, 2.5, 1.15),
                ("hat_pedal_tail_s", .04, .5, .13),
                ("hat_choke_tail_s", .03, .4, .09),
                ("ride_bow_tail_s", .30, 4.0, 1.90),
                ("ride_bell_tail_s", .20, 3.0, 1.35),
                ("crash_tail_s", .40, 5.0, 2.25),
                ("cymbal_choke_tail_s", .03, .5, .12),
                ("tom_tail_s", .10, 2.0, .74),
            ):
                _num(a.get(key, default), f"articulation_foundation.{key}", lo, hi)
            for key, default in (
                ("snare_ghost_gain", .62), ("snare_rimshot_gain", .90),
                ("snare_cross_stick_gain", .72), ("hat_half_open_gain", .36),
                ("hat_open_gain", .34), ("hat_pedal_gain", .27),
                ("hat_choke_gain", .22), ("cymbal_choke_gain", .24),
                ("tom_edge_gain", .82),
            ):
                _num(a.get(key, default), f"articulation_foundation.{key}", 0, 2)
            _num(a.get("hat_half_open_decay_s", .22), "articulation_foundation.hat_half_open_decay_s", .02, 1.5)
            _num(a.get("hat_open_decay_s", .62), "articulation_foundation.hat_open_decay_s", .05, 2.5)

        for name in ("ride", "crash"):
            c = graph.get(name, {})
            if not c:
                continue
            freq_keys = ("bow_freqs", "bell_freqs") if name == "ride" else ("freqs",)
            for fk in freq_keys:
                if fk in c:
                    vals = _seq(c[fk], f"{name}.{fk}", 3, 10, 200, 20000)
                    gk = fk.replace("freqs", "gains")
                    gains = c.get(gk, [])
                    if not isinstance(gains, list) or len(gains) != len(vals):
                        raise InstrumentEngineValidationError(f"{name}.{gk} must match {fk}")
                    for i, g in enumerate(gains):
                        _num(g, f"{name}.{gk}[{i}]", 0, 2)
            for key in ("bow_decay_s", "bell_decay_s", "decay_s"):
                if key in c:
                    _num(c[key], f"{name}.{key}", .02, 5.0)
            for key in ("bow_noise_gain", "bow_tonal_gain", "bow_output_gain",
                        "bell_noise_gain", "bell_tonal_gain", "bell_output_gain",
                        "noise_gain", "tonal_gain", "output_gain"):
                if key in c:
                    _num(c[key], f"{name}.{key}", 0, 2)

        for name, default_hz in (("tom_high", 180), ("tom_mid", 132), ("tom_floor", 88)):
            t = graph.get(name, {})
            if not t:
                continue
            _num(t.get("base_hz", default_hz), f"{name}.base_hz", 40, 400)
            ratios = _seq(t.get("mode_ratios", [1,1.59,2.14]), f"{name}.mode_ratios", 3, 8, .5, 8)
            for key in ("center_mode_gains", "edge_mode_gains"):
                gains = _seq(t.get(key, [1,.4,.2]), f"{name}.{key}", 3, 8, 0, 2)
                if len(gains) != len(ratios):
                    raise InstrumentEngineValidationError(f"{name}.{key} must match mode_ratios")
            _num(t.get("decay_s", .5), f"{name}.decay_s", .05, 2.0)
            _num(t.get("tension_shift_cents", 38), f"{name}.tension_shift_cents", 0, 180)
            _num(t.get("tension_decay_s", .055), f"{name}.tension_decay_s", .005, .4)
            _num(t.get("lowpass_hz", 7600), f"{name}.lowpass_hz", 500, 20000)
            _num(t.get("drive", 1.05), f"{name}.drive", .1, 5)
            _num(t.get("output_gain", .46), f"{name}.output_gain", 0, 2)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            note_rendering=False,
            extended_tail=True,
            instrument_expression=("velocity", "seeded_strike_variation", "explicit_articulation", "strike_force", "strike_position"),
        )


__all__ = ["PercussionEngine"]
