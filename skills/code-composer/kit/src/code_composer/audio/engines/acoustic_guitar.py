from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError


def _num(value, name, lo, hi):
    try:
        x = float(value)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not lo <= x <= hi:
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


def _integer(value, name, lo, hi):
    if isinstance(value, bool):
        raise InstrumentEngineValidationError(f"{name} must be integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and value.is_integer():
        out = int(value)
    else:
        raise InstrumentEngineValidationError(f"{name} must be integer")
    if not lo <= out <= hi:
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return out


class AcousticGuitarEngine(InstrumentEngine):
    """Acoustic-guitar engine boundary.

    AG01 adds an opt-in single-string steel-string physical path. AG02+ still owns
    per-note string/fret/right-hand/action semantics.
    """

    name = "acoustic_guitar"
    aliases = ("steel_string_guitar", "acoustic-guitar")
    mechanics_realizer = "acoustic_guitar"

    @staticmethod
    def _supports_fingering(patch):
        graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
        return (
            graph.get("physical_model") == "ag01_modal_bridge_body_v2"
            and graph.get("string_source_model") == "triangular_pluck_bridge_force_v2"
        )

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        from ..acoustic_guitar import render_acoustic_guitar_note
        return render_acoustic_guitar_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def render_action(
        self, action, duration_s, sr, patch, *, parameters, seed=0
    ):
        from ..acoustic_guitar import render_acoustic_guitar_action
        return render_acoustic_guitar_action(
            action,
            duration_s,
            sr,
            patch,
            parameters=parameters,
            seed=seed,
        )

    def validate_action_event(self, subject, event):
        from ..acoustic_guitar.percussion import ACTIONS, LOCATIONS

        action = event.get("action")
        if action not in set(ACTIONS):
            raise InstrumentEngineValidationError(
                f"{subject}: unsupported AG07 acoustic-guitar action {action!r}"
            )
        parameters = event.get("parameters")
        if not isinstance(parameters, dict):
            raise InstrumentEngineValidationError(
                f"{subject}.parameters must be object"
            )

        allowed = {
            "strength", "location", "tail_s",
            "direction", "traversal_ms", "string_count",
        }
        unknown = set(parameters) - allowed
        if unknown:
            raise InstrumentEngineValidationError(
                f"{subject}: unsupported AG07 action parameter(s): {sorted(unknown)}"
            )
        if "strength" in parameters:
            _num(parameters["strength"], f"{subject}.parameters.strength", 0.0, 1.0)
        if "tail_s" in parameters:
            _num(parameters["tail_s"], f"{subject}.parameters.tail_s", 0.18, 0.65)
        if "location" in parameters and parameters["location"] not in set(LOCATIONS):
            raise InstrumentEngineValidationError(
                f"{subject}.parameters.location unsupported"
            )

        if action in {"muted_strum", "dead_strum"}:
            if parameters.get("direction", "down") not in {"down", "up"}:
                raise InstrumentEngineValidationError(
                    f"{subject}.parameters.direction must be down or up"
                )
            _num(
                parameters.get("traversal_ms", 32.0),
                f"{subject}.parameters.traversal_ms",
                6.0,
                180.0,
            )
            _integer(
                parameters.get("string_count", 6),
                f"{subject}.parameters.string_count",
                2,
                6,
            )
        else:
            forbidden = {"direction", "traversal_ms", "string_count"} & set(parameters)
            if forbidden:
                raise InstrumentEngineValidationError(
                    f"{subject}: action {action!r} does not accept {sorted(forbidden)}"
                )

    def tail_seconds(self, patch):
        graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
        return max(0.0, float(graph.get("natural_tail_s", 0.45)))

    def validate_note_performance_for_patch(self, subject, payload, patch):
        if not self._supports_fingering(patch):
            return super().validate_note_performance_for_patch(subject, payload, patch)
        if not isinstance(payload, dict) or not payload:
            raise InstrumentEngineValidationError(
                f"{subject}: acoustic-guitar instrument_performance must contain string and/or fret"
            )
        unknown = set(payload) - {"string", "fret", "right_hand", "left_hand", "arpeggio", "strum"}
        if unknown:
            raise InstrumentEngineValidationError(
                f"{subject}: unsupported acoustic-guitar instrument_performance field(s): {sorted(unknown)}"
            )
        if "string" in payload:
            _integer(payload["string"], f"{subject}.instrument_performance.string", 1, 6)
        if "fret" in payload:
            _integer(payload["fret"], f"{subject}.instrument_performance.fret", 0, 20)

        if "right_hand" in payload:
            right_hand = payload["right_hand"]
            if not isinstance(right_hand, dict) or not right_hand:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.right_hand must be a non-empty object"
                )
            unknown_right = set(right_hand) - {
                "method",
                "pluck_position",
                "attack_angle_deg",
                "strength",
            }
            if unknown_right:
                raise InstrumentEngineValidationError(
                    f"{subject}: unsupported AG03 right_hand field(s): {sorted(unknown_right)}"
                )
            if "method" in right_hand and right_hand["method"] not in {
                "finger", "thumb", "nail", "pick"
            }:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.right_hand.method "
                    "must be one of ['finger', 'thumb', 'nail', 'pick']"
                )
            if "pluck_position" in right_hand:
                _num(
                    right_hand["pluck_position"],
                    f"{subject}.instrument_performance.right_hand.pluck_position",
                    0.03,
                    0.49,
                )
            if "attack_angle_deg" in right_hand:
                _num(
                    right_hand["attack_angle_deg"],
                    f"{subject}.instrument_performance.right_hand.attack_angle_deg",
                    0.0,
                    90.0,
                )
            if "strength" in right_hand:
                _num(
                    right_hand["strength"],
                    f"{subject}.instrument_performance.right_hand.strength",
                    0.0,
                    1.0,
                )

        if "left_hand" in payload:
            left_hand = payload["left_hand"]
            if not isinstance(left_hand, dict) or not left_hand:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.left_hand must be a non-empty object"
                )
            unknown_left = set(left_hand) - {
                "technique", "amount", "transition_ms", "harmonic_order"
            }
            if unknown_left:
                raise InstrumentEngineValidationError(
                    f"{subject}: unsupported AG04 left_hand field(s): {sorted(unknown_left)}"
                )
            if left_hand.get("technique") not in {
                "palm_mute", "fretting_mute", "dead_note",
                "slide", "hammer_on", "pull_off", "natural_harmonic"
            }:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.left_hand.technique unsupported"
                )
            if "amount" in left_hand:
                _num(
                    left_hand["amount"],
                    f"{subject}.instrument_performance.left_hand.amount",
                    0.0, 1.0,
                )
            if "transition_ms" in left_hand:
                _num(
                    left_hand["transition_ms"],
                    f"{subject}.instrument_performance.left_hand.transition_ms",
                    4.0, 240.0,
                )
            if "harmonic_order" in left_hand:
                _integer(
                    left_hand["harmonic_order"],
                    f"{subject}.instrument_performance.left_hand.harmonic_order",
                    2, 5,
                )

        if "arpeggio" in payload:
            arpeggio = payload["arpeggio"]
            if not isinstance(arpeggio, dict) or not arpeggio:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.arpeggio must be a non-empty object"
                )
            unknown_arp = set(arpeggio) - {
                "gesture_id", "player", "voice", "sequence_index"
            }
            if unknown_arp:
                raise InstrumentEngineValidationError(
                    f"{subject}: unsupported AG05 arpeggio field(s): {sorted(unknown_arp)}"
                )
            gesture_id = arpeggio.get("gesture_id")
            if not isinstance(gesture_id, str) or not gesture_id.strip():
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.arpeggio.gesture_id must be non-empty string"
                )
            if arpeggio.get("player") not in {
                "thumb", "index", "middle", "ring", "pick"
            }:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.arpeggio.player unsupported"
                )
            if arpeggio.get("voice") not in {"bass", "inner", "treble"}:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.arpeggio.voice unsupported"
                )
            _integer(
                arpeggio.get("sequence_index"),
                f"{subject}.instrument_performance.arpeggio.sequence_index",
                0,
                127,
            )

        if "strum" in payload:
            if "arpeggio" in payload:
                raise InstrumentEngineValidationError(
                    f"{subject}: AG05 arpeggio and AG06 strum cannot coexist on one note"
                )
            strum = payload["strum"]
            if not isinstance(strum, dict) or not strum:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.strum must be a non-empty object"
                )
            unknown_strum = set(strum) - {
                "stroke_id", "direction", "traversal_ms", "entry_strength",
                "acceleration", "pick_depth", "attack_angle_deg",
                "follow_through", "accent_position", "accent_amount",
                "from_string", "to_string", "state",
            }
            if unknown_strum:
                raise InstrumentEngineValidationError(
                    f"{subject}: unsupported AG06 strum field(s): {sorted(unknown_strum)}"
                )
            stroke_id = strum.get("stroke_id")
            if not isinstance(stroke_id, str) or not stroke_id.strip():
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.strum.stroke_id must be non-empty string"
                )
            if strum.get("direction") not in {"down", "up"}:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.strum.direction unsupported"
                )
            _num(
                strum.get("traversal_ms", 34.0),
                f"{subject}.instrument_performance.strum.traversal_ms",
                6.0, 180.0,
            )
            _num(
                strum.get("entry_strength", 0.62),
                f"{subject}.instrument_performance.strum.entry_strength",
                0.15, 1.0,
            )
            _num(
                strum.get("acceleration", 0.0),
                f"{subject}.instrument_performance.strum.acceleration",
                -1.0, 1.0,
            )
            _num(
                strum.get("pick_depth", 0.55),
                f"{subject}.instrument_performance.strum.pick_depth",
                0.0, 1.0,
            )
            _num(
                strum.get("attack_angle_deg", 45.0),
                f"{subject}.instrument_performance.strum.attack_angle_deg",
                0.0, 90.0,
            )
            _num(
                strum.get("follow_through", 0.70),
                f"{subject}.instrument_performance.strum.follow_through",
                0.0, 1.0,
            )
            _num(
                strum.get("accent_position", 0.50),
                f"{subject}.instrument_performance.strum.accent_position",
                0.0, 1.0,
            )
            _num(
                strum.get("accent_amount", 0.0),
                f"{subject}.instrument_performance.strum.accent_amount",
                0.0, 0.75,
            )
            _integer(
                strum.get("from_string"),
                f"{subject}.instrument_performance.strum.from_string",
                1, 6,
            )
            _integer(
                strum.get("to_string"),
                f"{subject}.instrument_performance.strum.to_string",
                1, 6,
            )
            if strum.get("state", "sounding") not in {"sounding", "muted"}:
                raise InstrumentEngineValidationError(
                    f"{subject}.instrument_performance.strum.state unsupported"
                )

    def _validate(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"{subject}: patch must be object")
        if patch.get("kind") not in {"acoustic_guitar", None}:
            raise InstrumentEngineValidationError(
                f"{subject}: acoustic-guitar patch kind must be acoustic_guitar"
            )
        graph = patch.get("acoustic_guitar_graph")
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(
                f"{subject}: acoustic_guitar_graph must be an object"
            )

        model = graph.get("physical_model")
        if model not in {None, "ag01_modal_bridge_body_v1", "ag01_modal_bridge_body_v2"}:
            raise InstrumentEngineValidationError(
                f"{subject}.acoustic_guitar.physical_model unsupported: {model!r}"
            )

        for key, lo, hi in (
            ("max_partials", 1, 48),
            ("pluck_position", 0.03, 0.49),
            ("partial_rolloff", 0.45, 3.0),
            ("bridge_force_rolloff", 0.80, 2.0),
            ("string_inharmonicity", 0.0, 0.003),
            ("base_decay_s", 0.05, 8.0),
            ("frequency_damping", 0.0, 2.0),
            ("damping_power", 0.2, 3.0),
            ("decay_keytrack", -0.05, 0.08),
            ("fret_contact", 0.0, 1.0),
            ("natural_tail_s", 0.0, 4.0),
            ("post_gate_decay_s", 0.015, 3.0),
            ("attack_s", 0.0003, 0.2),
            ("pluck_noise_gain", 0.0, 0.25),
            ("pluck_noise_decay_s", 0.002, 0.2),
            ("string_release_ramp_s", 0.0001, 0.02),
            ("excitation_noise_gain", 0.0, 0.25),
            ("excitation_highpass_hz", 20.0, 12000.0),
            ("excitation_lowpass_hz", 50.0, 18000.0),
            ("excitation_decay_s", 0.002, 0.2),
            ("release_click_gain", 0.0, 0.20),
            ("bridge_highpass_hz", 10.0, 1000.0),
            ("bridge_lowpass_hz", 200.0, 18000.0),
            ("body_modal_mix", 0.0, 3.0),
            ("body_mode_shift", 0.80, 1.20),
            ("body_mode_damping", 0.55, 2.0),
            ("direct_bridge_mix", 0.0, 2.0),
            ("air_mode_hz", 60.0, 180.0),
            ("air_mode_q", 0.5, 5.0),
            ("air_mode_mix", 0.0, 1.0),
            ("radiation_lowpass_hz", 500.0, 18000.0),
            ("radiation_keytrack", 0.0, 2.0),
            ("stereo_width", 0.0, 0.20),
            ("side_highpass_hz", 100.0, 8000.0),
            ("body_drive", 0.05, 5.0),
            ("end_fade_s", 0.002, 0.2),
            ("output_gain", 0.0, 2.0),
        ):
            if key in graph:
                value = _num(
                    graph[key], f"{subject}.acoustic_guitar.{key}", lo, hi
                )
                if key == "max_partials" and int(value) != value:
                    raise InstrumentEngineValidationError(
                        f"{subject}.acoustic_guitar.max_partials must be integer"
                    )

        source_model = graph.get("string_source_model")
        if source_model not in {None, "ag01_legacy_modal_v1", "triangular_pluck_bridge_force_v2"}:
            raise InstrumentEngineValidationError(
                f"{subject}.acoustic_guitar.string_source_model unsupported: {source_model!r}"
            )

        if "seed" in graph and not isinstance(graph["seed"], int):
            raise InstrumentEngineValidationError(
                f"{subject}.acoustic_guitar.seed must be integer"
            )
        if (
            "excitation_highpass_hz" in graph
            and "excitation_lowpass_hz" in graph
            and float(graph["excitation_highpass_hz"])
            >= float(graph["excitation_lowpass_hz"])
        ):
            raise InstrumentEngineValidationError(
                f"{subject}.acoustic_guitar excitation highpass must be below lowpass"
            )
        if (
            "bridge_highpass_hz" in graph
            and "bridge_lowpass_hz" in graph
            and float(graph["bridge_highpass_hz"])
            >= float(graph["bridge_lowpass_hz"])
        ):
            raise InstrumentEngineValidationError(
                f"{subject}.acoustic_guitar bridge highpass must be below lowpass"
            )

    def validate_ir_patch(self, subject, patch):
        self._validate(subject, patch)

    def validate_runtime_patch(self, subject, patch):
        self._validate(subject, patch)

    def validate_authoring_patch(self, role, patch):
        self._validate(role, patch)

    def capabilities(self):
        return EngineCapabilities(name=self.name, extended_tail=True)

    def capabilities_for_patch(self, patch):
        enabled = self._supports_fingering(patch)
        return EngineCapabilities(
            name=self.name,
            extended_tail=True,
            instrument_performance=enabled,
            instrument_actions=enabled,
            mechanics_realization=enabled,
        )


__all__ = ["AcousticGuitarEngine"]
