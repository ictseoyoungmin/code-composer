from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError
from ..piano_design import resolve_piano_design, PianoDesignError


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not (lo <= x <= hi):
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


class PianoEngine(InstrumentEngine):
    name = "piano"
    aliases = ("acoustic_piano", "electric_piano")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        from ..piano import render_piano_note
        return render_piano_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def tail_seconds(self, patch):
        from ..piano import piano_tail_seconds
        return float(piano_tail_seconds(patch))

    def post_process_track(self, stereo, sr, patch, events, beat_s):
        from ..piano import apply_piano_soundboard
        return apply_piano_soundboard(stereo, sr, patch, events, beat_s)

    def _resolve(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"instrument {subject}: patch must be object")
        if "piano_design" in patch:
            try:
                return resolve_piano_design(patch)
            except PianoDesignError as exc:
                raise InstrumentEngineValidationError(f"instrument {subject}: {exc}") from exc
        return patch

    def validate_ir_patch(self, subject, patch):
        patch = self._resolve(subject, patch)
        if patch.get("piano_engine") == "electric" or "electric_piano_graph" in patch:
            eg = patch.get("electric_piano_graph", {})
            if not isinstance(eg, dict):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric_piano_graph must be object"
                )
            tone = eg.get("tone", {})
            if tone.get("mechanism", "tine") not in {"tine", "reed", "digital_fm"}:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: unsupported electric piano mechanism"
                )
            if float(tone.get("decay_s", 2.7)) < .15:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano decay_s too small"
                )
            if float(tone.get("release_s", .55)) < .02:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano release_s too small"
                )
            return
        pg = patch.get("piano_graph", {})
        if not isinstance(pg, dict):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: piano_graph must be object"
            )
        strings = pg.get("strings", {})
        if not (3 <= int(strings.get("max_partials", 16)) <= 28):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: piano max_partials out of range"
            )
        damper = pg.get("damper", {})
        if float(damper.get("release_s", .20)) < .02:
            raise InstrumentEngineValidationError(
                f"instrument {subject}: piano release_s too small"
            )
        if float(damper.get("pedal_release_s", 1.65)) < float(damper.get("release_s", .20)):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: piano pedal release must be >= release"
            )

    def validate_runtime_patch(self, subject, patch):
        patch = self._resolve(subject, patch)
        if patch.get("piano_engine") == "electric" or "electric_piano_graph" in patch:
            graph = patch.get("electric_piano_graph")
            if not isinstance(graph, dict):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric_piano_graph must be an object"
                )
            tone = graph.get("tone", {})
            if tone.get("mechanism", "tine") not in {"tine", "reed", "digital_fm"}:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: invalid electric piano mechanism"
                )
            try:
                decay = float(tone.get("decay_s", 2.7))
                release = float(tone.get("release_s", .55))
                width = float(graph.get("stereo_width", .55))
            except Exception as exc:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano numeric parameter invalid"
                ) from exc
            if not (.15 <= decay <= 12):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano decay_s out of range"
                )
            if not (.02 <= release <= 6):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano release_s out of range"
                )
            if not (0 <= width <= 1):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: electric piano stereo_width out of range"
                )
            return
        graph = patch.get("piano_graph")
        if graph is not None and not isinstance(graph, dict):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: piano_graph must be an object"
            )
        self.validate_ir_patch(subject, patch)

    def validate_authoring_patch(self, role, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(
                f"sound_palette.{role}.patch must be an object"
            )
        try:
            patch = resolve_piano_design(patch)
        except PianoDesignError as exc:
            raise InstrumentEngineValidationError(f"{role}: {exc}") from exc
        if patch.get("kind") != "piano":
            raise InstrumentEngineValidationError(f"{role}: piano patch kind must be piano")

        if patch.get("piano_engine") == "electric" or "electric_piano_graph" in patch:
            graph = patch.get("electric_piano_graph")
            if not isinstance(graph, dict):
                raise InstrumentEngineValidationError(
                    f"{role}: electric_piano_graph must be an object"
                )
            tone = graph.get("tone", {})
            if tone.get("mechanism", "tine") not in {"tine", "reed", "digital_fm"}:
                raise InstrumentEngineValidationError(f"{role}: invalid electric piano mechanism")
            _num(tone.get("decay_s", 2.7), f"{role}.electric.decay_s", .15, 12)
            _num(tone.get("release_s", .55), f"{role}.electric.release_s", .02, 6)
            _num(tone.get("bell_gain", .34), f"{role}.electric.bell_gain", 0, 1.5)
            _num(tone.get("bark_gain", .16), f"{role}.electric.bark_gain", 0, 1.5)
            _num(tone.get("velocity_brightness", 1.0), f"{role}.electric.velocity_brightness", 0, 3)
            _num(tone.get("inharmonicity", .0018), f"{role}.electric.inharmonicity", 0, .02)
            pickup = graph.get("pickup", {})
            _num(pickup.get("drive", 1.15), f"{role}.electric.pickup.drive", .1, 8)
            _num(pickup.get("cutoff_hz", 8200), f"{role}.electric.pickup.cutoff_hz", 200, 20000)
            amp = graph.get("amp", {})
            _num(amp.get("drive", 1.08), f"{role}.electric.amp.drive", .1, 8)
            _num(amp.get("cutoff_hz", 7600), f"{role}.electric.amp.cutoff_hz", 200, 20000)
            mod = graph.get("modulation", {})
            if mod.get("type", "none") not in {"none", "tremolo", "chorus"}:
                raise InstrumentEngineValidationError(
                    f"{role}: invalid electric piano modulation type"
                )
            _num(mod.get("rate_hz", 4.6), f"{role}.electric.modulation.rate_hz", .05, 15)
            _num(mod.get("depth", .18), f"{role}.electric.modulation.depth", 0, 1)
            _num(mod.get("chorus_rate_hz", .55), f"{role}.electric.modulation.chorus_rate_hz", .05, 10)
            _num(mod.get("chorus_depth_cents", 4.5), f"{role}.electric.modulation.chorus_depth_cents", 0, 30)
            _num(graph.get("stereo_width", .55), f"{role}.electric.stereo_width", 0, 1)
            _num(graph.get("output_gain", .64), f"{role}.electric.output_gain", 0, 2)
            return

        graph = patch.get("piano_graph")
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(f"{role}: piano_graph must be an object")
        strings = graph.get("strings", {})
        _num(strings.get("max_partials", 16), f"{role}.piano.strings.max_partials", 3, 28)
        _num(strings.get("base_decay_s", 3.2), f"{role}.piano.strings.base_decay_s", .15, 12)
        _num(strings.get("decay_keytrack", .55), f"{role}.piano.strings.decay_keytrack", 0, 2)
        _num(strings.get("partial_decay_power", .58), f"{role}.piano.strings.partial_decay_power", 0, 2)
        _num(strings.get("spectral_rolloff", 1.36), f"{role}.piano.strings.spectral_rolloff", .5, 3)
        _num(strings.get("velocity_brightness", .72), f"{role}.piano.strings.velocity_brightness", 0, 2)
        _num(strings.get("inharmonicity", .00016), f"{role}.piano.strings.inharmonicity", 0, .005)
        _num(strings.get("detune_cents", .65), f"{role}.piano.strings.detune_cents", 0, 5)
        _num(strings.get("stereo_width", .72), f"{role}.piano.strings.stereo_width", 0, 1)
        for key, default in (("low_strings", 1), ("mid_strings", 2), ("high_strings", 3)):
            x = int(_num(strings.get(key, default), f"{role}.piano.strings.{key}", 1, 3))
            if x != float(strings.get(key, default)):
                raise InstrumentEngineValidationError(
                    f"{role}.piano.strings.{key} must be integer"
                )
        hammer = graph.get("hammer", {})
        _num(hammer.get("gain", .11), f"{role}.piano.hammer.gain", 0, .8)
        _num(hammer.get("noise_gain", .055), f"{role}.piano.hammer.noise_gain", 0, .5)
        _num(hammer.get("decay_s", .018), f"{role}.piano.hammer.decay_s", .001, .2)
        lo = _num(hammer.get("low_cutoff_hz", 700), f"{role}.piano.hammer.low_cutoff_hz", 20, 18000)
        soft = _num(hammer.get("soft_high_cutoff_hz", 3200), f"{role}.piano.hammer.soft_high_cutoff_hz", 100, 20000)
        hard = _num(hammer.get("hard_high_cutoff_hz", 11500), f"{role}.piano.hammer.hard_high_cutoff_hz", 100, 20000)
        if not (lo < soft <= hard):
            raise InstrumentEngineValidationError(
                f"{role}: piano hammer cutoffs must satisfy low < soft <= hard"
            )
        damper = graph.get("damper", {})
        rel = _num(damper.get("release_s", .20), f"{role}.piano.damper.release_s", .02, 5)
        pedal = _num(damper.get("pedal_release_s", 1.65), f"{role}.piano.damper.pedal_release_s", .02, 8)
        if pedal < rel:
            raise InstrumentEngineValidationError(
                f"{role}: pedal_release_s must be >= release_s"
            )
        resonance = graph.get("resonance", {})
        _num(resonance.get("gain", .025), f"{role}.piano.resonance.gain", 0, .4)
        _num(resonance.get("pedal_gain", .075), f"{role}.piano.resonance.pedal_gain", 0, .5)
        _num(resonance.get("decay_s", 2.4), f"{role}.piano.resonance.decay_s", .05, 8)
        bridge = graph.get("bridge", {})
        if bridge:
            _num(bridge.get("coupling", .30), f"{role}.piano.bridge.coupling", 0, 1)
            blo = _num(bridge.get("low_cutoff_hz", 55), f"{role}.piano.bridge.low_cutoff_hz", 20, 2000)
            bhi = _num(bridge.get("high_cutoff_hz", 12500), f"{role}.piano.bridge.high_cutoff_hz", 1000, 20000)
            if blo >= bhi:
                raise InstrumentEngineValidationError(
                    f"{role}: piano bridge low cutoff must be below high cutoff"
                )
        soundboard = graph.get("soundboard", {})
        _num(soundboard.get("gain", .018), f"{role}.piano.soundboard.gain", 0, .25)
        _num(soundboard.get("pedal_gain", .045), f"{role}.piano.soundboard.pedal_gain", 0, .35)
        _num(soundboard.get("cross", .32), f"{role}.piano.soundboard.cross", 0, 1)
        if soundboard.get("model") == "modal":
            _num(soundboard.get("modal_gain", .05), f"{role}.piano.soundboard.modal_gain", 0, .4)
            _num(soundboard.get("modal_decay_scale", 1.0), f"{role}.piano.soundboard.modal_decay_scale", .2, 4)
            modes = soundboard.get("modes_hz", [])
            weights = soundboard.get("mode_weights", [])
            decays = soundboard.get("mode_decays", [])
            if not isinstance(modes, list) or not (3 <= len(modes) <= 16):
                raise InstrumentEngineValidationError(
                    f"{role}: modal soundboard requires 3..16 modes"
                )
            if len(weights) != len(modes) or len(decays) != len(modes):
                raise InstrumentEngineValidationError(
                    f"{role}: modal soundboard arrays must have equal lengths"
                )
            for i, v in enumerate(modes):
                _num(v, f"{role}.piano.soundboard.modes_hz[{i}]", 20, 18000)
            for i, v in enumerate(weights):
                _num(v, f"{role}.piano.soundboard.mode_weights[{i}]", 0, 2)
            for i, v in enumerate(decays):
                _num(v, f"{role}.piano.soundboard.mode_decays[{i}]", .03, 8)
        taps = soundboard.get("taps_ms", [11.7, 17.9, 29.3, 41.1])
        weights = soundboard.get("weights", [1, .66, .43, .28])
        if not isinstance(taps, list) or not (1 <= len(taps) <= 8):
            raise InstrumentEngineValidationError(
                f"{role}: piano soundboard taps_ms must contain 1..8 values"
            )
        if not isinstance(weights, list) or len(weights) != len(taps):
            raise InstrumentEngineValidationError(
                f"{role}: piano soundboard weights must match taps_ms"
            )
        for i, v in enumerate(taps):
            _num(v, f"{role}.piano.soundboard.taps_ms[{i}]", 1, 120)
        for i, v in enumerate(weights):
            _num(v, f"{role}.piano.soundboard.weights[{i}]", 0, 2)
        body = graph.get("body_filter", {})
        softc = _num(body.get("soft_cutoff_hz", 3800), f"{role}.piano.body_filter.soft_cutoff_hz", 100, 19000)
        hardc = _num(body.get("hard_cutoff_hz", 14500), f"{role}.piano.body_filter.hard_cutoff_hz", 200, 20000)
        if softc > hardc:
            raise InstrumentEngineValidationError(
                f"{role}: piano soft cutoff must be <= hard cutoff"
            )
        mechanics = graph.get("mechanics", {})
        if mechanics:
            _num(mechanics.get("key_noise_gain", 0), f"{role}.piano.mechanics.key_noise_gain", 0, .25)
            _num(mechanics.get("damper_noise_gain", 0), f"{role}.piano.mechanics.damper_noise_gain", 0, .25)
        _num(graph.get("declick_ms", .35), f"{role}.piano.declick_ms", 0, 20)
        _num(graph.get("output_gain", .62), f"{role}.piano.output_gain", 0, 2)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            track_post_process=True,
            extended_tail=True,
            instrument_expression=("pedal",),
        )
