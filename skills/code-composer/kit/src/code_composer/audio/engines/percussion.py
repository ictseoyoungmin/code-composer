from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError
from ..drum_kit import integrate_drum_kit


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
        ext = graph.get("cymbal_extension", {}) if isinstance(graph, dict) else {}
        integration = graph.get("kit_integration", {}) if isinstance(graph, dict) else {}
        tom_mech = graph.get("tom_mechanics", {})
        if tom_mech:
            if not isinstance(tom_mech, dict):
                raise InstrumentEngineValidationError("drum_graph.tom_mechanics must be object")
            if "enabled" in tom_mech and not isinstance(tom_mech["enabled"], bool):
                raise InstrumentEngineValidationError("tom_mechanics.enabled must be boolean")
            if tom_mech.get("model", "coupled_two_head_shell_v1") != "coupled_two_head_shell_v1":
                raise InstrumentEngineValidationError("tom_mechanics.model unsupported")
            ratios=tom_mech.get("head_mode_ratios", [1.0,1.59,2.14])
            gains=tom_mech.get("head_mode_gains", [1.0,.48,.31])
            _seq(ratios, "tom_mechanics.head_mode_ratios", 3, 10, .4, 8.0)
            if not isinstance(gains,list) or len(gains)!=len(ratios):
                raise InstrumentEngineValidationError("tom_mechanics.head_mode_gains must match head_mode_ratios")
            for i,g in enumerate(gains): _num(g, f"tom_mechanics.head_mode_gains[{i}]", 0, 2)
            shape=tom_mech.get("bottom_gain_shape", [1.0]*len(ratios))
            if not isinstance(shape,list) or len(shape)!=len(ratios):
                raise InstrumentEngineValidationError("tom_mechanics.bottom_gain_shape must match head_mode_ratios")
            for i,g in enumerate(shape): _num(g, f"tom_mechanics.bottom_gain_shape[{i}]", .1, 2)
            for key,lo,hi,default in (
                ("stick_contact_soft_s",.0002,.01,.00185),("stick_contact_hard_s",.0002,.01,.00078),
                ("stick_contact_low_hz",80,12000,520),("stick_contact_high_hz",400,16000,6200),
                ("drive",.1,5,1.035),("velocity_power",.2,2,.92),("tail_s",.10,2,.72),
            ): _num(tom_mech.get(key,default), f"tom_mechanics.{key}", lo, hi)
            if float(tom_mech.get("stick_contact_low_hz",520)) >= float(tom_mech.get("stick_contact_high_hz",6200)):
                raise InstrumentEngineValidationError("tom_mechanics stick contact low must be below high")
            families=tom_mech.get("families",{})
            required_families=("high","mid","floor")
            if not isinstance(families,dict) or any(name not in families for name in required_families):
                raise InstrumentEngineValidationError("tom_mechanics.families missing high/mid/floor")
            for name in required_families:
                fam=families[name]
                if not isinstance(fam,dict): raise InstrumentEngineValidationError(f"tom_mechanics.families.{name} must be object")
                for key,lo,hi,default in (
                    ("head_base_hz",45,400,130),("head_decay_s",.03,1,.24),("bottom_frequency_scale",.75,1.25,.985),
                    ("bottom_head_delay_s",0,.02,.002),("bottom_transfer",0,1.5,.38),("bottom_decay_s",.03,1,.22),
                    ("cavity_decay_s",.03,1.5,.28),("cavity_lowpass_hz",120,5000,500),("top_gain",0,2,.66),
                    ("bottom_gain",0,2,.24),("cavity_gain",0,2,.12),("shell_gain",0,2,.11),("contact_gain",0,2,.075),
                    ("output_gain",0,2,.62),("tail_s",.10,2,.6),("output_highpass_hz",20,1200,42),("output_lowpass_hz",800,16000,7600),
                ): _num(fam.get(key,default), f"tom_mechanics.families.{name}.{key}", lo, hi)
                freqs=fam.get("shell_mode_freqs",[280,430,650])
                sg=fam.get("shell_mode_gains",[1,.72,.48])
                _seq(freqs, f"tom_mechanics.families.{name}.shell_mode_freqs", 3, 8, 60, 6000)
                if not isinstance(sg,list) or len(sg)!=len(freqs):
                    raise InstrumentEngineValidationError(f"tom_mechanics.families.{name}.shell_mode_gains must match shell_mode_freqs")
                for i,g in enumerate(sg): _num(g, f"tom_mechanics.families.{name}.shell_mode_gains[{i}]", 0, 2)
            states=tom_mech.get("states",{})
            for name in ("center","edge"):
                if not isinstance(states,dict) or name not in states or not isinstance(states[name],dict):
                    raise InstrumentEngineValidationError("tom_mechanics.states missing center/edge")
                st=states[name]
                for key,lo,hi,default in (
                    ("strike_position",0,1,.1),("head_decay_scale",.3,1.5,1),("bottom_transfer_scale",0,1.5,1),
                    ("bottom_decay_scale",.3,1.5,1),("top_gain_scale",0,2,1),("bottom_gain_scale",0,2,1),
                    ("cavity_gain_scale",0,2,1),("shell_gain_scale",0,2,1),("contact_gain_scale",0,2,1),
                    ("output_gain_scale",0,2,1),("velocity_power",.2,2,.92),
                ): _num(st.get(key,default), f"tom_mechanics.states.{name}.{key}", lo, hi)

        hihat = graph.get("hi_hat_mechanics", {}) if isinstance(graph, dict) else {}
        snare_mech = graph.get("snare_mechanics", {}) if isinstance(graph, dict) else {}
        tails = [0.0]
        if isinstance(realism, dict) and realism.get("enabled", False):
            tails.extend([
                float(realism.get("kick_tail_s", 0.36)),
                float(realism.get("snare_tail_s", 0.34)),
                float(realism.get("hat_tail_s", 0.13)),
            ])
        if isinstance(ext, dict) and ext.get("enabled", False):
            tails.extend([
                float(ext.get("ride_tail_s", 1.80)),
                float(ext.get("crash_tail_s", 2.20)),
            ])
        if isinstance(integration, dict) and integration.get("enabled", False):
            tails.append(float(integration.get("tail_s", 1.10)))
        if isinstance(hihat, dict) and hihat.get("enabled", False):
            states=hihat.get("states",{}) if isinstance(hihat.get("states",{}),dict) else {}
            tails.append(float(hihat.get("tail_s", .62)))
            for state in states.values():
                if isinstance(state,dict):
                    tails.append(float(state.get("tail_s",0.0)))
        if isinstance(snare_mech, dict) and snare_mech.get("enabled", False):
            states=snare_mech.get("states",{}) if isinstance(snare_mech.get("states",{}),dict) else {}
            tails.append(float(snare_mech.get("tail_s", .24)))
            for state in states.values():
                if isinstance(state,dict):
                    tails.append(float(state.get("tail_s",0.0)))
        if isinstance(tom_mech, dict) and tom_mech.get("enabled", False):
            families=tom_mech.get("families",{}) if isinstance(tom_mech.get("families",{}),dict) else {}
            tails.append(float(tom_mech.get("tail_s", .72)))
            for family in families.values():
                if isinstance(family,dict):
                    tails.append(float(family.get("tail_s",0.0)))
        return max(tails)

    def post_process_track(self, stereo, sr, patch, events, beat_s):
        graph = patch.get("drum_graph", {}) if isinstance(patch, dict) else {}
        cfg = graph.get("kit_integration", {}) if isinstance(graph, dict) else {}
        if not isinstance(cfg, dict) or not cfg.get("enabled", False):
            return stereo
        integrated, _report = integrate_drum_kit(stereo, sr, events, beat_s, cfg)
        return integrated

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

        for name, defaults in (
            ("ride", {"decay_s":1.55,"output_gain":.42}),
            ("crash", {"low_decay_s":1.90,"mid_decay_s":1.55,"high_decay_s":1.18,"output_gain":.34}),
        ):
            c = graph.get(name, {})
            if c:
                if not isinstance(c, dict):
                    raise InstrumentEngineValidationError(f"{prefix}: drum_graph.{name} must be object")
                _num(c.get("output_gain", defaults["output_gain"]), f"{name}.output_gain", 0, 2)
                _num(c.get("drive", 1.02), f"{name}.drive", .1, 5)
        snare_mech = graph.get("snare_mechanics", {})
        if snare_mech:
            if not isinstance(snare_mech, dict):
                raise InstrumentEngineValidationError("drum_graph.snare_mechanics must be object")
            if "enabled" in snare_mech and not isinstance(snare_mech["enabled"], bool):
                raise InstrumentEngineValidationError("snare_mechanics.enabled must be boolean")
            if snare_mech.get("model", "coupled_head_wire_rim_v1") != "coupled_head_wire_rim_v1":
                raise InstrumentEngineValidationError("snare_mechanics.model unsupported")
            ratios=snare_mech.get("head_mode_ratios", [1.0,1.47,1.93])
            gains=snare_mech.get("head_mode_gains", [1.0,.56,.35])
            _seq(ratios, "snare_mechanics.head_mode_ratios", 3, 10, .4, 8.0)
            if not isinstance(gains,list) or len(gains)!=len(ratios):
                raise InstrumentEngineValidationError("snare_mechanics.head_mode_gains must match head_mode_ratios")
            for i,g in enumerate(gains): _num(g, f"snare_mechanics.head_mode_gains[{i}]", 0, 2)
            shape=snare_mech.get("bottom_gain_shape", [1.0]*len(ratios))
            if not isinstance(shape,list) or len(shape)!=len(ratios):
                raise InstrumentEngineValidationError("snare_mechanics.bottom_gain_shape must match head_mode_ratios")
            for i,g in enumerate(shape): _num(g, f"snare_mechanics.bottom_gain_shape[{i}]", .1, 2)
            _seq(snare_mech.get("rim_mode_freqs", [520,760,1040]), "snare_mechanics.rim_mode_freqs", 3, 10, 100, 10000)
            rg=snare_mech.get("rim_mode_gains", [1.0,.78,.60])
            rf=snare_mech.get("rim_mode_freqs", [520,760,1040])
            if not isinstance(rg,list) or len(rg)!=len(rf):
                raise InstrumentEngineValidationError("snare_mechanics.rim_mode_gains must match rim_mode_freqs")
            for i,g in enumerate(rg): _num(g, f"snare_mechanics.rim_mode_gains[{i}]", 0, 2)
            for key,lo,hi,default in (
                ("head_base_hz",60,700,185),("head_decay_s",.01,.5,.082),
                ("bottom_frequency_scale",.7,1.6,1.18),("bottom_head_delay_s",0,.02,.0018),
                ("bottom_transfer",0,1.5,.42),("bottom_decay_s",.01,.5,.070),
                ("wire_low_hz",100,12000,1100),("wire_high_hz",500,20000,10800),
                ("wire_envelope_hz",10,800,150),("wire_decay_s",.01,.8,.105),
                ("rim_decay_s",.005,.5,.045),("stick_contact_low_hz",100,15000,900),
                ("stick_contact_high_hz",500,20000,9000),("output_highpass_hz",20,1000,75),
                ("output_lowpass_hz",1000,20000,11500),("drive",.1,5,1.035),("tail_s",.05,1,.24),
            ): _num(snare_mech.get(key,default), f"snare_mechanics.{key}", lo, hi)
            if float(snare_mech.get("wire_low_hz",1100)) >= float(snare_mech.get("wire_high_hz",10800)):
                raise InstrumentEngineValidationError("snare_mechanics wire low must be below high")
            states=snare_mech.get("states",{})
            required=("center","ghost","rimshot","cross_stick")
            if not isinstance(states,dict) or any(name not in states for name in required):
                raise InstrumentEngineValidationError("snare_mechanics.states missing required articulation state")
            for name in required:
                st=states[name]
                if not isinstance(st,dict): raise InstrumentEngineValidationError(f"snare_mechanics.states.{name} must be object")
                for key,lo,hi,default in (
                    ("strike_position",0,1,.1),("tail_s",.03,1,.2),("head_excitation",0,2,1),
                    ("head_decay_s",.005,.5,.08),("bottom_transfer",0,1.5,.4),("bottom_decay_s",.005,.5,.07),
                    ("wire_decay_s",.005,.8,.1),("head_gain",0,2,.6),("bottom_gain",0,2,.2),
                    ("wire_gain",0,2,.4),("rim_gain",0,2,.1),("wood_gain",0,2,.1),
                    ("contact_gain",0,2,.1),("output_gain",0,2,.6),("velocity_power",.2,2,1),
                ): _num(st.get(key,default), f"snare_mechanics.states.{name}.{key}", lo, hi)

        hihat = graph.get("hi_hat_mechanics", {})
        if hihat:
            if not isinstance(hihat, dict):
                raise InstrumentEngineValidationError("drum_graph.hi_hat_mechanics must be object")
            if "enabled" in hihat and not isinstance(hihat["enabled"], bool):
                raise InstrumentEngineValidationError("hi_hat_mechanics.enabled must be boolean")
            if hihat.get("model", "two_plate_inelastic_v1") not in {"two_plate_inelastic_v1", "two_plate_modal_contact_v2"}:
                raise InstrumentEngineValidationError("hi_hat_mechanics.model unsupported")
            collision_model=hihat.get("collision_model","broadband_texture_v1")
            if collision_model not in {"broadband_texture_v1","modal_plate_excitation_v2"}:
                raise InstrumentEngineValidationError("hi_hat_mechanics.collision_model unsupported")
            _seq(hihat.get("top_mode_freqs", [3550,4380,5210]), "hi_hat_mechanics.top_mode_freqs", 3, 16, 800, 19000)
            gains=hihat.get("top_mode_gains", [0.4,0.54,0.70])
            freqs=hihat.get("top_mode_freqs", [3550,4380,5210])
            if not isinstance(gains,list) or len(gains)!=len(freqs):
                raise InstrumentEngineValidationError("hi_hat_mechanics.top_mode_gains must match top_mode_freqs")
            for i,g in enumerate(gains): _num(g, f"hi_hat_mechanics.top_mode_gains[{i}]", 0, 2)
            shape=hihat.get("bottom_gain_shape", [1.0]*len(freqs))
            if not isinstance(shape,list) or len(shape)!=len(freqs):
                raise InstrumentEngineValidationError("hi_hat_mechanics.bottom_gain_shape must match top_mode_freqs")
            for i,g in enumerate(shape): _num(g, f"hi_hat_mechanics.bottom_gain_shape[{i}]", .1, 2)
            for key,lo,hi,default in (
                ("bottom_frequency_scale",.80,1.20,.963),("mode_jitter",0,.05,.009),
                ("plate_cloud_size",3,24,9),("plate_cloud_spread",0,.15,.036),
                ("low_order_suppression",0,1,.10),("stick_contact_soft_s",.0002,.01,.00155),
                ("stick_contact_hard_s",.0002,.01,.00062),("pedal_contact_soft_s",.0002,.01,.00145),
                ("pedal_contact_hard_s",.0002,.01,.00062),("contact_low_hz",500,18000,4300),
                ("contact_high_hz",1000,20000,11200),("collision_low_hz",500,18000,3600),
                ("collision_high_hz",1000,20000,11200),("output_highpass_hz",100,18000,2800),
                ("output_lowpass_hz",1000,20000,11400),("drive",.1,5,1.025),("tail_s",.05,2,.62),
                ("collision_contact_ms",.10,4.0,.46),("collision_mode_jitter",0,.05,.015),
                ("collision_cloud_size",3,24,5),("collision_cloud_spread",0,.15,.045),
                ("collision_low_order_suppression",0,1,.46),
            ): _num(hihat.get(key,default), f"hi_hat_mechanics.{key}", lo, hi)
            if collision_model=="modal_plate_excitation_v2":
                _seq(hihat.get("collision_mode_freqs", [4300,5200,6250]), "hi_hat_mechanics.collision_mode_freqs", 3, 16, 800, 19000)
                cg=hihat.get("collision_mode_gains", [0.3,0.46,0.67])
                cf=hihat.get("collision_mode_freqs", [4300,5200,6250])
                if not isinstance(cg,list) or len(cg)!=len(cf):
                    raise InstrumentEngineValidationError("hi_hat_mechanics.collision_mode_gains must match collision_mode_freqs")
                for i,g in enumerate(cg): _num(g, f"hi_hat_mechanics.collision_mode_gains[{i}]", 0, 2)
            if float(hihat.get("contact_low_hz",4300)) >= float(hihat.get("contact_high_hz",11200)):
                raise InstrumentEngineValidationError("hi_hat_mechanics contact low must be below high")
            if float(hihat.get("collision_low_hz",3600)) >= float(hihat.get("collision_high_hz",11200)):
                raise InstrumentEngineValidationError("hi_hat_mechanics collision low must be below high")
            states=hihat.get("states",{})
            required=("tight_closed","closed","half_open","open","pedal_chick","foot_splash")
            if not isinstance(states,dict) or any(name not in states for name in required):
                raise InstrumentEngineValidationError("hi_hat_mechanics.states missing required articulation state")
            for name in required:
                st=states[name]
                if not isinstance(st,dict): raise InstrumentEngineValidationError(f"hi_hat_mechanics.states.{name} must be object")
                for key,lo,hi,default in (
                    ("openness",0,1,.5),("tail_s",.03,2,.2),("plate_decay_s",.01,1,.1),
                    ("bottom_transfer",0,1.5,.6),("bottom_decay_scale",.4,1.5,.9),
                    ("collision_duration_s",0,.8,.05),("collision_density_hz",0,4000,500),
                    ("collision_gain",0,2,.3),("collision_resonance_decay_s",.004,.12,.02),
                    ("top_gain",0,2,.5),("bottom_gain",0,2,.4),
                    ("contact_gain",0,2,.2),("output_gain",0,2,.42),
                ): _num(st.get(key,default), f"hi_hat_mechanics.states.{name}.{key}", lo, hi)

        hi_hat_state = graph.get("hi_hat_state", {})
        if hi_hat_state:
            if not isinstance(hi_hat_state, dict):
                raise InstrumentEngineValidationError("drum_graph.hi_hat_state must be object")
            if "enabled" in hi_hat_state and not isinstance(hi_hat_state["enabled"], bool):
                raise InstrumentEngineValidationError("hi_hat_state.enabled must be boolean")
            model = hi_hat_state.get("model", "authored_closure_damping_v1")
            if model not in {"authored_closure_damping_v1", "authored_continuous_openness_v2", "authored_persistent_openness_v3"}:
                raise InstrumentEngineValidationError("hi_hat_state.model unsupported")
            closure = hi_hat_state.get("closure", {})
            if closure and not isinstance(closure, dict):
                raise InstrumentEngineValidationError("hi_hat_state.closure must be object")
            allowed = {"hat_half_open", "hat_closed", "hat_tight_closed", "hat_pedal"}
            for name, item in (closure.items() if isinstance(closure, dict) else []):
                if name not in allowed:
                    raise InstrumentEngineValidationError(f"hi_hat_state.closure.{name} unsupported")
                if not isinstance(item, dict):
                    raise InstrumentEngineValidationError(f"hi_hat_state.closure.{name} must be object")
                _num(item.get("decay_ms", 12.0), f"hi_hat_state.closure.{name}.decay_ms", .5, 250.0)
                _num(item.get("residual", .02), f"hi_hat_state.closure.{name}.residual", 0.0, 1.0)
            continuous = hi_hat_state.get("continuous", {})
            if continuous and not isinstance(continuous, dict):
                raise InstrumentEngineValidationError("hi_hat_state.continuous must be object")
            if model in {"authored_continuous_openness_v2", "authored_persistent_openness_v3"}:
                if continuous.get("control", "hi_hat_pedal_openness") != "hi_hat_pedal_openness":
                    raise InstrumentEngineValidationError("hi_hat_state.continuous.control unsupported")
                _num(continuous.get("split_hz", 5200.0), "hi_hat_state.continuous.split_hz", 1200.0, 12000.0)
                _num(continuous.get("body_closed_decay_ms", 72.0), "hi_hat_state.continuous.body_closed_decay_ms", 5.0, 500.0)
                _num(continuous.get("wash_closed_decay_ms", 24.0), "hi_hat_state.continuous.wash_closed_decay_ms", 2.0, 300.0)
                _num(continuous.get("contact_power", 1.65), "hi_hat_state.continuous.contact_power", .25, 6.0)
                _num(continuous.get("residual", .003), "hi_hat_state.continuous.residual", 0.0, .25)
            pedal_audio = hi_hat_state.get("pedal_audio", {})
            if pedal_audio:
                if not isinstance(pedal_audio, dict):
                    raise InstrumentEngineValidationError("hi_hat_state.pedal_audio must be object")
                if "enabled" in pedal_audio and not isinstance(pedal_audio["enabled"], bool):
                    raise InstrumentEngineValidationError("hi_hat_state.pedal_audio.enabled must be boolean")
                _num(pedal_audio.get("contact_threshold", .10), "hi_hat_state.pedal_audio.contact_threshold", 0.0, .5)
                _num(pedal_audio.get("release_threshold", .18), "hi_hat_state.pedal_audio.release_threshold", .01, .8)
                _num(pedal_audio.get("splash_closed_openness", .08), "hi_hat_state.pedal_audio.splash_closed_openness", 0.0, .3)
                for key,default in (("min_close_speed_per_s",3.5),("full_close_speed_per_s",16.0),("min_reopen_speed_per_s",3.5),("full_reopen_speed_per_s",14.0)):
                    _num(pedal_audio.get(key,default), f"hi_hat_state.pedal_audio.{key}", .01, 80.0)
                for key,default in (("chick_velocity_min",.36),("chick_velocity_max",.94),("splash_velocity_min",.42),("splash_velocity_max",1.0)):
                    _num(pedal_audio.get(key,default), f"hi_hat_state.pedal_audio.{key}", .01, 1.25)
                for key,default in (("chick_output_gain",1.0),("splash_output_gain",1.0)):
                    _num(pedal_audio.get(key,default), f"hi_hat_state.pedal_audio.{key}", 0.0, 4.0)
                profiles=pedal_audio.get("collision_profiles",{})
                if profiles:
                    if not isinstance(profiles,dict):
                        raise InstrumentEngineValidationError("hi_hat_state.pedal_audio.collision_profiles must be object")
                    for name in ("chick","splash"):
                        item=profiles.get(name,{})
                        if item:
                            if not isinstance(item,dict):
                                raise InstrumentEngineValidationError(f"hi_hat_state.pedal_audio.collision_profiles.{name} must be object")
                            if "enabled" in item and not isinstance(item["enabled"],bool):
                                raise InstrumentEngineValidationError(f"hi_hat_state.pedal_audio.collision_profiles.{name}.enabled must be boolean")
                            _num(item.get("pulse_ms",.55), f"hi_hat_state.pedal_audio.collision_profiles.{name}.pulse_ms", .10, 4.0)
                            _num(item.get("density_scale",1.0), f"hi_hat_state.pedal_audio.collision_profiles.{name}.density_scale", .10, 4.0)
                            _num(item.get("gain_scale",1.0), f"hi_hat_state.pedal_audio.collision_profiles.{name}.gain_scale", 0.0, 2.0)

        integration = graph.get("kit_integration", {})
        if integration:
            if not isinstance(integration, dict):
                raise InstrumentEngineValidationError("drum_graph.kit_integration must be object")
            if "enabled" in integration and not isinstance(integration["enabled"], bool):
                raise InstrumentEngineValidationError("kit_integration.enabled must be boolean")
            for key, lo, hi, default in (
                ("tail_s", .20, 3.0, 1.10),
                ("close_gain", 0.0, 2.0, 1.0),
                ("overhead_gain", 0.0, 1.0, .26),
                ("room_gain", 0.0, 1.0, .20),
                ("output_gain", .1, 2.0, .92),
                ("overhead_highpass_hz", 20, 1200, 115),
                ("overhead_lowpass_hz", 2000, 20000, 14500),
                ("room_highpass_hz", 20, 1200, 72),
                ("room_lowpass_hz", 1500, 20000, 11800),
                ("room_rt60_s", .12, 2.5, .52),
                ("room_hf_damping", 0.0, .97, .56),
                ("room_predelay_ms", 0.0, 80.0, 8.0),
                ("overhead_predelay_ms", 0.0, 20.0, 0.0),
                ("room_send_floor", 0.0, 2.0, .48),
                ("room_send_scale", 0.0, 2.0, .78),
                ("room_velocity_power", .2, 4.0, 1.45),
                ("tom_room_weight", 0.0, 2.0, .45),
                ("parallel_mix", 0.0, .5, .16),
                ("body_parallel_gain", 0.0, .5, .10),
                ("body_highpass_hz", 20.0, 240.0, 45.0),
                ("body_lowpass_hz", 120.0, 1200.0, 260.0),
                ("body_comp_ratio", 1.0, 10.0, 1.8),
                ("ambient_comp_ratio", 1.0, 10.0, 2.4),
                ("bus_ratio", 1.0, 10.0, 2.1),
            ):
                _num(integration.get(key, default), f"kit_integration.{key}", lo, hi)
            if float(integration.get("overhead_highpass_hz",115)) >= float(integration.get("overhead_lowpass_hz",14500)):
                raise InstrumentEngineValidationError("kit_integration overhead highpass must be below lowpass")
            if float(integration.get("room_highpass_hz",72)) >= float(integration.get("room_lowpass_hz",11800)):
                raise InstrumentEngineValidationError("kit_integration room highpass must be below lowpass")
            if float(integration.get("body_highpass_hz",45)) >= float(integration.get("body_lowpass_hz",260)):
                raise InstrumentEngineValidationError("kit_integration body highpass must be below lowpass")
            delays = integration.get("fdn_delays_ms", [31.3,37.9,43.7,53.1])
            _seq(delays, "kit_integration.fdn_delays_ms", 4, 4, 10.0, 120.0)
            articulation_weights = integration.get("articulation_room_weights", {})
            if articulation_weights:
                if not isinstance(articulation_weights, dict):
                    raise InstrumentEngineValidationError("kit_integration.articulation_room_weights must be object")
                for name, value in articulation_weights.items():
                    if not isinstance(name, str) or not name:
                        raise InstrumentEngineValidationError("kit_integration articulation weight names must be non-empty strings")
                    _num(value, f"kit_integration.articulation_room_weights.{name}", 0.0, 2.0)

        ext = graph.get("cymbal_extension", {})
        if ext:
            if not isinstance(ext, dict):
                raise InstrumentEngineValidationError("drum_graph.cymbal_extension must be object")
            if "enabled" in ext and not isinstance(ext["enabled"], bool):
                raise InstrumentEngineValidationError("cymbal_extension.enabled must be boolean")
            if "strike_model" in ext and ext["strike_model"] not in ("", "physical_v1", "physical_v2"):
                raise InstrumentEngineValidationError("cymbal_extension.strike_model unsupported")
            _num(ext.get("ride_tail_s", 1.80), "cymbal_extension.ride_tail_s", .2, 5.0)
            _num(ext.get("crash_tail_s", 2.20), "cymbal_extension.crash_tail_s", .2, 6.0)

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

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            note_rendering=False,
            track_post_process=True,
            extended_tail=True,
            instrument_expression=("velocity", "seeded_strike_variation"),
        )


__all__ = ["PercussionEngine"]
