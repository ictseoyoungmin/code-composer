import json
from hashlib import sha256
from pathlib import Path
import zipfile

import pytest

from code_composer.exchange.package import (
    DivergedExchangeError,
    DirtyWorkspaceError,
    ExchangePackageError,
    ScopeLockViolation,
    export_exchange_package,
    import_exchange_package,
    inspect_exchange_package,
)

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples/basic/demo_ir.json"
B = ROOT / "examples/v1.16/final_closure/B_rhythm_centered/music_ir_after.json"
STAMP = "2026-09-17T08:00:00Z"


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _export(source, out, *, author="A", message="root", **kwargs):
    return export_exchange_package(source, out, author=author, message=message, created_at=STAMP, **kwargs)


def test_root_ccx_is_self_contained_valid_and_restorable(tmp_path):
    package = tmp_path / "song.ccx"
    result = _export(
        DEMO,
        package,
        requested_changes=["tighten pre-hook transition"],
        locked_scopes=["track:lead", "transport"],
        notes=["reference WAV is the sound authority"],
    )
    assert package.exists()
    inspected = inspect_exchange_package(package)
    assert inspected["valid"] is True
    assert inspected["revision_id"] == result["manifest"]["revision_id"]
    assert inspected["parent_revision_id"] is None
    assert inspected["handoff_status"] == "working"

    workspace = tmp_path / "person_b"
    imported = import_exchange_package(package, workspace)
    assert imported["revision_id"] == inspected["revision_id"]
    assert imported["locked_scopes"] == ["track:lead", "transport"]
    assert (workspace / "composition/music_ir.json").read_bytes()
    assert (workspace / "composition/resolved_ir.json").read_bytes()
    assert (workspace / "audio/reference_mix.wav").read_bytes()[:4] == b"RIFF"
    assert (workspace / ".code-composer/exchange_state.json").exists()
    assert (workspace / ".code-composer/base_music_ir.json").exists()


def test_two_people_can_fast_forward_revision_chain(tmp_path):
    r1 = tmp_path / "r1.ccx"
    _export(DEMO, r1, author="A", message="initial")
    a = tmp_path / "A"
    b = tmp_path / "B"
    import_exchange_package(r1, a)
    import_exchange_package(r1, b)

    # B changes an unlocked musical field and checkpoints a child revision.
    music_path = b / "composition/music_ir.json"
    music = _json(music_path)
    music["tracks"][0]["events"][0]["velocity"] = 0.61
    music_path.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r2 = tmp_path / "r2.ccx"
    child = export_exchange_package(
        b, r2, author="B", message="lead nuance", status="review",
        requested_changes=["A: review the chorus balance"], created_at="2026-09-17T08:01:00Z",
    )
    assert child["manifest"]["parent_revision_id"] == inspect_exchange_package(r1)["revision_id"]
    assert child["workspace_checkpointed"] is True

    # A is still at r1, so r2 is a legal fast-forward.
    received = import_exchange_package(r2, a)
    assert received["revision_id"] == child["manifest"]["revision_id"]
    assert _json(a / "composition/music_ir.json")["tracks"][0]["events"][0]["velocity"] == 0.61
    history = _json(a / "provenance/revisions.json")["revisions"]
    assert len(history) == 2
    assert history[1]["parent_revision_id"] == history[0]["revision_id"]


def test_scope_lock_blocks_child_checkpoint_if_locked_state_changes(tmp_path):
    r1 = tmp_path / "locked.ccx"
    _export(B, r1, locked_scopes=["track:bass", "section:drive", "tonal"])
    workspace = tmp_path / "worker"
    import_exchange_package(r1, workspace)

    music_path = workspace / "composition/music_ir.json"
    music = _json(music_path)
    bass = next(t for t in music["tracks"] if t["id"] == "bass")
    bass["events"][0]["velocity"] = min(0.99, float(bass["events"][0]["velocity"]) + 0.01)
    music_path.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ScopeLockViolation, match="track:bass"):
        export_exchange_package(workspace, tmp_path / "bad.ccx", author="B", created_at=STAMP)


def test_unlocked_change_is_allowed_while_lock_is_carried_as_parent_constraint(tmp_path):
    r1 = tmp_path / "locked.ccx"
    _export(B, r1, locked_scopes=["track:bass"])
    workspace = tmp_path / "worker"
    import_exchange_package(r1, workspace)
    music_path = workspace / "composition/music_ir.json"
    music = _json(music_path)
    lead = next(t for t in music["tracks"] if t["id"] == "lead")
    lead["events"][0]["velocity"] = max(0.01, float(lead["events"][0]["velocity"]) - 0.01)
    music_path.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = export_exchange_package(workspace, tmp_path / "ok.ccx", author="B", created_at=STAMP)
    assert result["manifest"]["parent_revision_id"] == inspect_exchange_package(r1)["revision_id"]


def test_diverged_handoff_is_rejected_instead_of_overwriting(tmp_path):
    base = tmp_path / "base.ccx"
    _export(DEMO, base)
    a = tmp_path / "A"
    b = tmp_path / "B"
    import_exchange_package(base, a)
    import_exchange_package(base, b)

    # A and B both checkpoint children of the same parent.
    for ws, vel in ((a, 0.55), (b, 0.65)):
        music_path = ws / "composition/music_ir.json"
        music = _json(music_path)
        music["tracks"][0]["events"][0]["velocity"] = vel
        music_path.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    a2 = tmp_path / "a2.ccx"
    b2 = tmp_path / "b2.ccx"
    export_exchange_package(a, a2, author="A", message="branch A", created_at="2026-09-17T08:02:00Z")
    export_exchange_package(b, b2, author="B", message="branch B", created_at="2026-09-17T08:03:00Z")

    with pytest.raises(DivergedExchangeError, match="DIVERGED HANDOFF"):
        import_exchange_package(b2, a)


def test_dirty_workspace_must_be_checkpointed_before_receiving(tmp_path):
    r1 = tmp_path / "r1.ccx"
    _export(DEMO, r1)
    a = tmp_path / "A"
    b = tmp_path / "B"
    import_exchange_package(r1, a)
    import_exchange_package(r1, b)

    music_path = b / "composition/music_ir.json"
    music = _json(music_path)
    music["tracks"][0]["events"][0]["velocity"] = 0.58
    music_path.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r2 = tmp_path / "r2.ccx"
    export_exchange_package(b, r2, author="B", created_at="2026-09-17T08:04:00Z")

    local = _json(a / "composition/music_ir.json")
    local["tracks"][0]["events"][0]["velocity"] = 0.57
    (a / "composition/music_ir.json").write_text(json.dumps(local, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(DirtyWorkspaceError, match="uncheckpointed changes"):
        import_exchange_package(r2, a)


def test_package_hash_tampering_is_detected(tmp_path):
    good = tmp_path / "good.ccx"
    _export(DEMO, good)
    bad = tmp_path / "bad.ccx"
    with zipfile.ZipFile(good, "r") as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "handoff/handoff.json":
                data = data.replace(b'"working"', b'"review"')
            dst.writestr(info.filename, data)
    with pytest.raises(ExchangePackageError, match="hash mismatch"):
        inspect_exchange_package(bad)


def test_archive_rejects_unknown_or_path_traversal_members(tmp_path):
    good = tmp_path / "good.ccx"
    _export(DEMO, good)
    for member in ("unexpected.txt", "../escape.txt"):
        bad = tmp_path / ("bad_" + member.replace("/", "_") + ".ccx")
        with zipfile.ZipFile(good, "r") as src, zipfile.ZipFile(bad, "w") as dst:
            for info in src.infolist():
                dst.writestr(info.filename, src.read(info.filename))
            dst.writestr(member, b"x")
        with pytest.raises(ExchangePackageError):
            inspect_exchange_package(bad)


def test_optional_plan_and_brief_survive_roundtrip(tmp_path):
    package = tmp_path / "with_context.ccx"
    _export(
        DEMO, package,
        plan=ROOT / "examples/v1.16/final_closure/A_lyrical_piano/plan_after.json",
        brief=ROOT / "examples/basic/composition_brief.json",
    )
    ws = tmp_path / "ws"
    import_exchange_package(package, ws)
    assert (ws / "composition/plan.json").exists()
    assert (ws / "composition/brief.json").exists()
    child = tmp_path / "child.ccx"
    export_exchange_package(ws, child, author="B", created_at="2026-09-17T08:05:00Z")
    with zipfile.ZipFile(child, "r") as zf:
        assert "composition/plan.json" in zf.namelist()
        assert "composition/brief.json" in zf.namelist()


def test_fixed_provenance_produces_byte_deterministic_root_package(tmp_path):
    one = tmp_path / "one.ccx"
    two = tmp_path / "two.ccx"
    _export(DEMO, one, author="A", message="same")
    _export(DEMO, two, author="A", message="same")
    assert one.read_bytes() == two.read_bytes()
    assert sha256(one.read_bytes()).hexdigest() == sha256(two.read_bytes()).hexdigest()


def test_import_refuses_non_exchange_nonempty_directory(tmp_path):
    package = tmp_path / "song.ccx"
    _export(DEMO, package)
    target = tmp_path / "ordinary"
    target.mkdir()
    (target / "keep.txt").write_text("do not overwrite")
    with pytest.raises(ExchangePackageError, match="non-empty"):
        import_exchange_package(package, target)
    assert (target / "keep.txt").read_text() == "do not overwrite"


def test_exchange_cli_export_inspect_import(tmp_path, capsys):
    from code_composer.app.exchange_cli import main

    package = tmp_path / "cli.ccx"
    assert main(["export", str(DEMO), str(package), "--author", "A", "--timestamp", STAMP, "--request", "review drums"]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["revision_id"]
    assert package.exists()

    assert main(["inspect", str(package)]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["valid"] is True

    workspace = tmp_path / "workspace"
    assert main(["import", str(package), str(workspace)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["requested_changes"] == ["review drums"]

def test_revision_identity_is_recomputed_even_if_payload_hashes_are_rewritten(tmp_path):
    good = tmp_path / "good.ccx"
    _export(DEMO, good)
    with zipfile.ZipFile(good, "r") as src:
        payloads = {info.filename: src.read(info.filename) for info in src.infolist() if not info.is_dir()}
    revisions = json.loads(payloads["provenance/revisions.json"].decode("utf-8"))
    revisions["revisions"][-1]["author"] = "Mallory"
    payloads["provenance/revisions.json"] = (json.dumps(revisions, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    manifest = json.loads(payloads["manifest.json"].decode("utf-8"))
    manifest["hashes"]["provenance/revisions.json"] = sha256(payloads["provenance/revisions.json"]).hexdigest()
    payloads["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    bad = tmp_path / "bad_identity.ccx"
    with zipfile.ZipFile(bad, "w") as dst:
        for name, data in payloads.items():
            dst.writestr(name, data)
    with pytest.raises(ExchangePackageError, match="revision identity mismatch"):
        inspect_exchange_package(bad)


def test_explicit_parent_package_supports_standalone_child_export(tmp_path):
    parent = tmp_path / "parent.ccx"
    _export(DEMO, parent, author="A", message="root")
    music = _json(DEMO)
    music["tracks"][0]["events"][0]["velocity"] = 0.63
    child_ir = tmp_path / "child.json"
    child_ir.write_text(json.dumps(music, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    child = tmp_path / "child.ccx"
    result = export_exchange_package(
        child_ir, child, author="B", message="standalone child",
        parent_package=parent, created_at="2026-09-17T08:06:00Z",
    )
    parent_info = inspect_exchange_package(parent)
    assert result["manifest"]["parent_revision_id"] == parent_info["revision_id"]
    ws = tmp_path / "ws"
    import_exchange_package(parent, ws)
    import_exchange_package(child, ws)
    assert _json(ws / "composition/music_ir.json")["tracks"][0]["events"][0]["velocity"] == 0.63


def test_same_revision_reimport_is_idempotent_when_workspace_is_clean(tmp_path):
    package = tmp_path / "same.ccx"
    _export(DEMO, package)
    ws = tmp_path / "ws"
    first = import_exchange_package(package, ws)
    second = import_exchange_package(package, ws)
    assert first["revision_id"] == second["revision_id"]
