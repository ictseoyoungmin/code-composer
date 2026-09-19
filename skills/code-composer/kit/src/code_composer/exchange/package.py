from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any
import zipfile

from .. import __version__
from ..core.ir import validate_ir
from ..pipeline.service import render_to_files
from ..validation_contracts import validate_runtime_extensions

EXCHANGE_FORMAT = "code-composer-exchange/v1"
HANDOFF_FORMAT = "code-composer-handoff/v1"
REVISION_FORMAT = "code-composer-revisions/v1"
WORKSPACE_STATE_FORMAT = "code-composer-exchange-workspace/v1"

_REQUIRED = {
    "manifest.json",
    "composition/music_ir.json",
    "composition/resolved_ir.json",
    "provenance/revisions.json",
    "handoff/handoff.json",
    "audio/reference_mix.wav",
}
_OPTIONAL = {"composition/plan.json", "composition/brief.json"}
_ALLOWED = _REQUIRED | _OPTIONAL
_STATE_DIR = ".code-composer"
_STATE_FILE = f"{_STATE_DIR}/exchange_state.json"
_BASE_IR_FILE = f"{_STATE_DIR}/base_music_ir.json"


class ExchangeError(ValueError):
    pass


class ExchangePackageError(ExchangeError):
    pass


class DivergedExchangeError(ExchangeError):
    pass


class DirtyWorkspaceError(ExchangeError):
    pass


class ScopeLockViolation(ExchangeError):
    pass


def _json_bytes(value: Any, *, pretty: bool = True) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical_hash(value: Any) -> str:
    return _digest(_json_bytes(value, pretty=False))


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExchangePackageError(f"cannot read JSON: {path}") from exc


def _validate_music_ir(ir: dict[str, Any]) -> None:
    validate_ir(ir)
    validate_runtime_extensions(ir)


def _scope_view(ir: dict[str, Any], scope: str) -> Any:
    if scope in {"transport", "tonal", "form", "mix", "arrangement", "performance_ir"}:
        return deepcopy(ir.get(scope))
    if ":" not in scope:
        raise ExchangePackageError(
            f"unsupported scope lock {scope!r}; use transport/tonal/form/mix/arrangement/performance_ir or track:/instrument:/section:"
        )
    kind, name = scope.split(":", 1)
    if not name:
        raise ExchangePackageError(f"empty scope target in {scope!r}")
    if kind == "track":
        for track in ir.get("tracks", []):
            if str(track.get("id")) == name:
                return deepcopy(track)
        raise ExchangePackageError(f"scope lock target does not exist: {scope}")
    if kind == "instrument":
        instruments = ir.get("instruments", {})
        if name not in instruments:
            raise ExchangePackageError(f"scope lock target does not exist: {scope}")
        return deepcopy(instruments[name])
    if kind == "section":
        form = [s for s in ir.get("form", []) if str(s.get("id")) == name]
        events = []
        for track in ir.get("tracks", []):
            selected = [e for e in track.get("events", []) if str(e.get("section_id")) == name]
            if selected:
                events.append({"track_id": track.get("id"), "events": selected})
        if not form and not events:
            raise ExchangePackageError(f"scope lock target does not exist: {scope}")
        return {"form": deepcopy(form), "track_events": deepcopy(events)}
    raise ExchangePackageError(f"unsupported scope lock kind: {kind!r}")


def _validate_locked_scopes(ir: dict[str, Any], scopes: list[str]) -> None:
    seen: set[str] = set()
    for raw in scopes:
        scope = str(raw)
        if scope in seen:
            raise ExchangePackageError(f"duplicate scope lock: {scope}")
        seen.add(scope)
        _scope_view(ir, scope)


def _enforce_parent_locks(parent_ir: dict[str, Any], child_ir: dict[str, Any], parent_handoff: dict[str, Any]) -> None:
    changed = []
    for scope in parent_handoff.get("locked_scopes", []):
        before = _scope_view(parent_ir, str(scope))
        after = _scope_view(child_ir, str(scope))
        if _canonical_hash(before) != _canonical_hash(after):
            changed.append(str(scope))
    if changed:
        raise ScopeLockViolation("locked scopes changed: " + ", ".join(changed))


def _normalize_handoff(
    ir: dict[str, Any],
    *,
    status: str,
    requested_changes: list[str] | None,
    locked_scopes: list[str] | None,
    notes: list[str] | None,
) -> dict[str, Any]:
    allowed_status = {"working", "review", "approved_internal"}
    if status not in allowed_status:
        raise ExchangePackageError(f"handoff status must be one of {sorted(allowed_status)}")
    locks = [str(x) for x in (locked_scopes or [])]
    _validate_locked_scopes(ir, locks)
    return {
        "format": HANDOFF_FORMAT,
        "status": status,
        "requested_changes": [str(x) for x in (requested_changes or [])],
        "locked_scopes": locks,
        "notes": [str(x) for x in (notes or [])],
    }


def _zip_member_names(zf: zipfile.ZipFile) -> list[str]:
    names = []
    for info in zf.infolist():
        name = info.filename
        path = PurePosixPath(name)
        if info.is_dir():
            continue
        if path.is_absolute() or ".." in path.parts or str(path) != name:
            raise ExchangePackageError(f"unsafe archive member: {name!r}")
        names.append(name)
    if len(names) != len(set(names)):
        raise ExchangePackageError("duplicate archive members are not allowed")
    unknown = set(names) - _ALLOWED
    missing = _REQUIRED - set(names)
    if unknown:
        raise ExchangePackageError(f"unknown exchange package members: {sorted(unknown)}")
    if missing:
        raise ExchangePackageError(f"missing exchange package members: {sorted(missing)}")
    return names


def _read_package(path: str | Path) -> dict[str, Any]:
    package_path = Path(path)
    if not package_path.is_file():
        raise ExchangePackageError(f"exchange package does not exist: {package_path}")
    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            names = _zip_member_names(zf)
            payloads = {name: zf.read(name) for name in names}
    except zipfile.BadZipFile as exc:
        raise ExchangePackageError(f"invalid .ccx ZIP container: {package_path}") from exc

    try:
        manifest = json.loads(payloads["manifest.json"].decode("utf-8"))
        music_ir = json.loads(payloads["composition/music_ir.json"].decode("utf-8"))
        resolved_ir = json.loads(payloads["composition/resolved_ir.json"].decode("utf-8"))
        revisions = json.loads(payloads["provenance/revisions.json"].decode("utf-8"))
        handoff = json.loads(payloads["handoff/handoff.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExchangePackageError("exchange package contains invalid JSON") from exc

    if manifest.get("format") != EXCHANGE_FORMAT:
        raise ExchangePackageError(f"unsupported exchange format: {manifest.get('format')!r}")
    if handoff.get("format") != HANDOFF_FORMAT:
        raise ExchangePackageError("invalid handoff format")
    if handoff.get("status") not in {"working", "review", "approved_internal"}:
        raise ExchangePackageError("invalid handoff status")
    for key in ("requested_changes", "locked_scopes", "notes"):
        if not isinstance(handoff.get(key), list) or not all(isinstance(item, str) for item in handoff[key]):
            raise ExchangePackageError(f"handoff.{key} must be a list of strings")
    if revisions.get("format") != REVISION_FORMAT:
        raise ExchangePackageError("invalid revision history format")

    for optional_name in _OPTIONAL & set(payloads):
        try:
            json.loads(payloads[optional_name].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExchangePackageError(f"invalid JSON in {optional_name}") from exc

    expected_hashes = manifest.get("hashes")
    if not isinstance(expected_hashes, dict):
        raise ExchangePackageError("manifest.hashes must be an object")
    expected_payload_names = set(names) - {"manifest.json"}
    if set(expected_hashes) != expected_payload_names:
        raise ExchangePackageError("manifest hashes do not cover the exact package payload")
    for name in sorted(expected_payload_names):
        actual = _digest(payloads[name])
        if expected_hashes[name] != actual:
            raise ExchangePackageError(f"hash mismatch for {name}")

    _validate_music_ir(music_ir)
    validate_ir(resolved_ir)
    _validate_locked_scopes(music_ir, list(handoff.get("locked_scopes", [])))

    history = revisions.get("revisions")
    if not isinstance(history, list) or not history:
        raise ExchangePackageError("revision history must contain at least one revision")
    seen: set[str] = set()
    previous = None
    for index, record in enumerate(history):
        rid = record.get("revision_id")
        if not isinstance(rid, str) or not rid:
            raise ExchangePackageError(f"revision {index} has no revision_id")
        if rid in seen:
            raise ExchangePackageError(f"duplicate revision_id: {rid}")
        seen.add(rid)
        if record.get("parent_revision_id") != previous:
            raise ExchangePackageError(f"broken revision chain at {rid}")
        author = record.get("author")
        message = record.get("message")
        state_hashes = record.get("state_hashes")
        optional_hashes = record.get("optional_hashes")
        if not isinstance(author, str) or not author.strip():
            raise ExchangePackageError(f"revision {rid} has invalid author")
        if not isinstance(message, str) or not isinstance(state_hashes, dict) or not isinstance(optional_hashes, dict):
            raise ExchangePackageError(f"revision {rid} has invalid provenance fields")
        expected_rid = _revision_id(
            parent_revision_id=previous,
            author=author,
            message=message,
            state_hashes=state_hashes,
            optional_hashes=optional_hashes,
        )
        if rid != expected_rid:
            raise ExchangePackageError(f"revision identity mismatch at {rid}")
        previous = rid
    if manifest.get("revision_id") != history[-1].get("revision_id"):
        raise ExchangePackageError("manifest revision does not match revision history head")
    if manifest.get("parent_revision_id") != history[-1].get("parent_revision_id"):
        raise ExchangePackageError("manifest parent does not match revision history head")

    current_state = history[-1].get("state_hashes", {})
    for key, member in {
        "music_ir_sha256": "composition/music_ir.json",
        "resolved_ir_sha256": "composition/resolved_ir.json",
        "reference_mix_sha256": "audio/reference_mix.wav",
        "handoff_sha256": "handoff/handoff.json",
    }.items():
        if current_state.get(key) != expected_hashes.get(member):
            raise ExchangePackageError(f"head revision {key} does not match package payload")

    return {
        "path": package_path,
        "manifest": manifest,
        "music_ir": music_ir,
        "resolved_ir": resolved_ir,
        "revisions": revisions,
        "handoff": handoff,
        "payloads": payloads,
    }


def inspect_exchange_package(path: str | Path) -> dict[str, Any]:
    package = _read_package(path)
    manifest = deepcopy(package["manifest"])
    manifest["package_path"] = str(Path(path))
    manifest["package_sha256"] = _digest(Path(path).read_bytes())
    manifest["valid"] = True
    return manifest


def _source_paths(source: Path, plan: Path | None, brief: Path | None) -> tuple[Path, Path | None, Path | None, Path | None]:
    workspace = None
    if source.is_dir():
        workspace = source
        music = source / "composition/music_ir.json"
        if not music.is_file():
            fallback = source / "music_ir.json"
            if fallback.is_file():
                music = fallback
            else:
                raise ExchangePackageError("workspace has no composition/music_ir.json")
        if plan is None and (source / "composition/plan.json").is_file():
            plan = source / "composition/plan.json"
        if brief is None and (source / "composition/brief.json").is_file():
            brief = source / "composition/brief.json"
        return music, plan, brief, workspace
    if not source.is_file():
        raise ExchangePackageError(f"source does not exist: {source}")
    return source, plan, brief, workspace


def _workspace_parent(workspace: Path) -> dict[str, Any] | None:
    state_path = workspace / _STATE_FILE
    manifest_path = workspace / "manifest.json"
    revisions_path = workspace / "provenance/revisions.json"
    handoff_path = workspace / "handoff/handoff.json"
    base_ir_path = workspace / _BASE_IR_FILE
    if not state_path.exists():
        return None
    for path in (manifest_path, revisions_path, handoff_path, base_ir_path):
        if not path.is_file():
            raise ExchangePackageError(f"exchange workspace state is incomplete: missing {path.relative_to(workspace)}")
    state = _read_json(state_path)
    manifest = _read_json(manifest_path)
    revisions = _read_json(revisions_path)
    handoff = _read_json(handoff_path)
    base_ir = _read_json(base_ir_path)
    if state.get("format") != WORKSPACE_STATE_FORMAT:
        raise ExchangePackageError("unsupported workspace state format")
    if state.get("head_revision_id") != manifest.get("revision_id"):
        raise ExchangePackageError("workspace state head does not match manifest")
    return {"manifest": manifest, "revisions": revisions, "handoff": handoff, "music_ir": base_ir}


def _parent_context(parent_package: Path | None, workspace: Path | None) -> dict[str, Any] | None:
    if parent_package is not None:
        package = _read_package(parent_package)
        return {k: package[k] for k in ("manifest", "revisions", "handoff", "music_ir")}
    if workspace is not None:
        return _workspace_parent(workspace)
    return None


def _revision_id(
    *, parent_revision_id: str | None, author: str, message: str,
    state_hashes: dict[str, str], optional_hashes: dict[str, str],
) -> str:
    # Revision identity is content-addressed from durable provenance fields.
    # created_at is intentionally excluded so deterministic fixtures can carry
    # a display timestamp without making identity dependent on wall-clock time.
    identity = {
        "parent_revision_id": parent_revision_id,
        "author": author,
        "message": message,
        "state_hashes": state_hashes,
        "optional_hashes": optional_hashes,
    }
    return _canonical_hash(identity)


def _zip_write(path: Path, payloads: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payloads[name])


def _sync_workspace(workspace: Path, package_path: Path) -> None:
    package = _read_package(package_path)
    # Managed payload files + manifest are checkpoint state. Hidden base state is
    # intentionally outside the archive and supports lock/dirtiness validation.
    for name, data in package["payloads"].items():
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (workspace / "manifest.json").write_bytes(_json_bytes(package["manifest"]))
    state_dir = workspace / _STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "format": WORKSPACE_STATE_FORMAT,
        "head_revision_id": package["manifest"]["revision_id"],
        "parent_revision_id": package["manifest"].get("parent_revision_id"),
        "managed_hashes": package["manifest"]["hashes"],
        "manifest_sha256": _digest((workspace / "manifest.json").read_bytes()),
        "package_sha256": _digest(package_path.read_bytes()),
    }
    (workspace / _STATE_FILE).write_bytes(_json_bytes(state))
    (workspace / _BASE_IR_FILE).write_bytes(_json_bytes(package["music_ir"]))


def export_exchange_package(
    source: str | Path,
    out_path: str | Path,
    *,
    author: str,
    message: str = "",
    status: str = "working",
    requested_changes: list[str] | None = None,
    locked_scopes: list[str] | None = None,
    notes: list[str] | None = None,
    plan: str | Path | None = None,
    brief: str | Path | None = None,
    parent_package: str | Path | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    source = Path(source)
    out_path = Path(out_path)
    author = str(author).strip()
    if not author:
        raise ExchangePackageError("author must not be empty")
    plan_path = Path(plan) if plan is not None else None
    brief_path = Path(brief) if brief is not None else None
    music_path, plan_path, brief_path, workspace = _source_paths(source, plan_path, brief_path)
    music_ir = _read_json(music_path)
    _validate_music_ir(music_ir)

    parent = _parent_context(Path(parent_package) if parent_package is not None else None, workspace)
    parent_revision_id = None
    history: list[dict[str, Any]] = []
    if parent is not None:
        parent_revision_id = parent["manifest"].get("revision_id")
        history = deepcopy(parent["revisions"].get("revisions", []))
        _enforce_parent_locks(parent["music_ir"], music_ir, parent["handoff"])

    handoff = _normalize_handoff(
        music_ir,
        status=status,
        requested_changes=requested_changes,
        locked_scopes=locked_scopes,
        notes=notes,
    )

    with tempfile.TemporaryDirectory(prefix="code-composer-exchange-") as tmp:
        tmp = Path(tmp)
        wav_path = tmp / "reference_mix.wav"
        resolved_path = tmp / "resolved_ir.json"
        render = render_to_files(music_ir, wav_path, resolved_path, None)
        resolved_ir = render["resolved"]

        payloads: dict[str, bytes] = {
            "composition/music_ir.json": _json_bytes(music_ir),
            "composition/resolved_ir.json": _json_bytes(resolved_ir),
            "audio/reference_mix.wav": wav_path.read_bytes(),
            "handoff/handoff.json": _json_bytes(handoff),
        }
        if plan_path is not None:
            if not plan_path.is_file():
                raise ExchangePackageError(f"plan does not exist: {plan_path}")
            payloads["composition/plan.json"] = _json_bytes(_read_json(plan_path))
        if brief_path is not None:
            if not brief_path.is_file():
                raise ExchangePackageError(f"brief does not exist: {brief_path}")
            payloads["composition/brief.json"] = _json_bytes(_read_json(brief_path))

        state_hashes = {
            "music_ir_sha256": _digest(payloads["composition/music_ir.json"]),
            "resolved_ir_sha256": _digest(payloads["composition/resolved_ir.json"]),
            "reference_mix_sha256": _digest(payloads["audio/reference_mix.wav"]),
            "handoff_sha256": _digest(payloads["handoff/handoff.json"]),
        }
        optional_hashes = {
            name: _digest(data)
            for name, data in payloads.items()
            if name in _OPTIONAL
        }
        revision_id = _revision_id(
            parent_revision_id=parent_revision_id,
            author=author,
            message=str(message),
            state_hashes=state_hashes,
            optional_hashes=optional_hashes,
        )
        record = {
            "revision_id": revision_id,
            "parent_revision_id": parent_revision_id,
            "author": author,
            "created_at": created_at or _now_utc(),
            "message": str(message),
            "state_hashes": state_hashes,
            "optional_hashes": optional_hashes,
        }
        history.append(record)
        revisions = {"format": REVISION_FORMAT, "revisions": history}
        payloads["provenance/revisions.json"] = _json_bytes(revisions)
        hashes = {name: _digest(data) for name, data in payloads.items()}
        manifest = {
            "format": EXCHANGE_FORMAT,
            "code_composer_version": __version__,
            "revision_id": revision_id,
            "parent_revision_id": parent_revision_id,
            "created_at": record["created_at"],
            "author": author,
            "message": str(message),
            "handoff_status": handoff["status"],
            "files": {
                "music_ir": "composition/music_ir.json",
                "resolved_ir": "composition/resolved_ir.json",
                "reference_mix": "audio/reference_mix.wav",
                "revisions": "provenance/revisions.json",
                "handoff": "handoff/handoff.json",
                **({"plan": "composition/plan.json"} if "composition/plan.json" in payloads else {}),
                **({"brief": "composition/brief.json"} if "composition/brief.json" in payloads else {}),
            },
            "hashes": hashes,
        }
        archive_payloads = {"manifest.json": _json_bytes(manifest), **payloads}
        _zip_write(out_path, archive_payloads)

    # Full self-validation before a package is considered exported.
    validated = _read_package(out_path)
    if workspace is not None:
        _sync_workspace(workspace, out_path)
    return {
        "package_path": str(out_path),
        "package_sha256": _digest(out_path.read_bytes()),
        "manifest": validated["manifest"],
        "handoff": validated["handoff"],
        "workspace_checkpointed": workspace is not None,
    }


def _workspace_dirty(workspace: Path, state: dict[str, Any]) -> list[str]:
    dirty = []
    for name, expected in state.get("managed_hashes", {}).items():
        path = workspace / name
        if not path.is_file() or _digest(path.read_bytes()) != expected:
            dirty.append(name)
    manifest_path = workspace / "manifest.json"
    if not manifest_path.is_file() or _digest(manifest_path.read_bytes()) != state.get("manifest_sha256"):
        dirty.append("manifest.json")
    return sorted(set(dirty))


def import_exchange_package(package_path: str | Path, workspace: str | Path) -> dict[str, Any]:
    package = _read_package(package_path)
    workspace = Path(workspace)
    state_path = workspace / _STATE_FILE

    if workspace.exists() and any(workspace.iterdir()) and not state_path.is_file():
        raise ExchangePackageError("refusing to import into a non-empty directory that is not an exchange workspace")

    current_state = _read_json(state_path) if state_path.is_file() else None
    if current_state is not None:
        if current_state.get("format") != WORKSPACE_STATE_FORMAT:
            raise ExchangePackageError("unsupported workspace state format")
        dirty = _workspace_dirty(workspace, current_state)
        if dirty:
            raise DirtyWorkspaceError("workspace has uncheckpointed changes: " + ", ".join(dirty))
        current_head = current_state.get("head_revision_id")
        incoming_head = package["manifest"]["revision_id"]
        incoming_parent = package["manifest"].get("parent_revision_id")
        if incoming_head != current_head and incoming_parent != current_head:
            raise DivergedExchangeError(
                f"DIVERGED HANDOFF: workspace head={current_head}, incoming parent={incoming_parent}, incoming head={incoming_head}"
            )

    workspace.mkdir(parents=True, exist_ok=True)
    _sync_workspace(workspace, Path(package_path))
    return {
        "workspace": str(workspace),
        "revision_id": package["manifest"]["revision_id"],
        "parent_revision_id": package["manifest"].get("parent_revision_id"),
        "status": package["handoff"]["status"],
        "requested_changes": deepcopy(package["handoff"].get("requested_changes", [])),
        "locked_scopes": deepcopy(package["handoff"].get("locked_scopes", [])),
    }
