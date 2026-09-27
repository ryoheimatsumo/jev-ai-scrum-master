import json
import os
import sqlite3
from pathlib import Path

import pytest

from jev_sm.cli import main
from jev_sm.common import DomainError
from jev_sm.store import Store
from jev_sm.workspace import Workspace


def test_doctor_reports_uncreated_explicit_state_without_writing(core, capsys, tmp_path):
    selected = tmp_path / "persistent-state"
    assert main(["--repo", str(core.workspace.root), "--state-dir", str(selected), "doctor"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == {"path": str(selected / core.workspace.id), "source": "explicit",
                                "exists": False, "access": "unverified", "writability": "unverified"}
    assert not selected.exists()


def test_doctor_reports_unknown_state_existence_on_permission_error(core, monkeypatch, capsys, tmp_path):
    selected = tmp_path / "unreadable-state"
    state_path = (selected / core.workspace.id).resolve()
    original = Path.exists

    def denied(path):
        if Path(path) == state_path:
            raise PermissionError("denied")
        return original(path)

    monkeypatch.setattr(Path, "exists", denied)
    assert main(["--repo", str(core.workspace.root), "--state-dir", str(selected), "doctor"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"]["exists"] is None
    assert result["state"]["access"] == "unavailable"
    assert result["state"]["writability"] == "unverified"


def test_init_preview_does_not_create_state(core, capsys, tmp_path):
    core.workspace.config_path.unlink()
    selected = tmp_path / "preview-state"
    assert main(["--repo", str(core.workspace.root), "--state-dir", str(selected), "init"]) == 0
    assert json.loads(capsys.readouterr().out)["written"] is False
    assert not selected.exists()


def test_operational_default_state_mkdir_failure_is_structured(core, monkeypatch, capsys):
    selected = Workspace(core.workspace.root, create_state=False).state_dir
    original = Path.mkdir

    def denied(path, *args, **kwargs):
        if Path(path) == selected:
            raise PermissionError("denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", denied)
    assert main(["--repo", str(core.workspace.root), "prepare", "a task"]) == 4
    error = json.loads(capsys.readouterr().err)["error"]
    assert error["code"] == "STATE_UNAVAILABLE" and str(selected) in error["message"]


def test_operational_explicit_state_mkdir_failure_has_no_fallback(core, monkeypatch, capsys, tmp_path):
    selected = (tmp_path / "denied").resolve()
    state_path = selected / core.workspace.id
    original = Path.mkdir

    def denied(path, *args, **kwargs):
        if Path(path) == state_path:
            raise PermissionError("denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", denied)
    assert main(["--repo", str(core.workspace.root), "--state-dir", str(selected),
                 "prepare", "a task"]) == 4
    error = json.loads(capsys.readouterr().err)["error"]
    assert error["code"] == "STATE_UNAVAILABLE" and str(state_path) in error["message"]


def test_store_database_open_failure_is_state_unavailable(monkeypatch, tmp_path):
    path = tmp_path / "state.sqlite3"
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: (_ for _ in ()).throw(
        sqlite3.OperationalError("readonly")))
    with pytest.raises(DomainError) as caught:
        Store(path)
    assert caught.value.code == "STATE_UNAVAILABLE" and str(path) in caught.value.message


def test_store_active_database_failure_is_state_unavailable(monkeypatch, tmp_path):
    store = Store(tmp_path / "state.sqlite3")

    class DeniedConnection:
        row_factory = None

        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("readonly")

        def close(self):
            pass

    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: DeniedConnection())
    with pytest.raises(DomainError) as caught:
        store.all_tasks()
    assert caught.value.code == "STATE_UNAVAILABLE"
    assert str(store.path) in caught.value.message


def test_state_root_inside_repository_is_rejected_before_creation(core):
    with pytest.raises(DomainError) as caught:
        Workspace(core.workspace.root, core.workspace.root / "state", create_state=False)
    assert caught.value.code == "UNSAFE_STATE_PATH"
    assert not (core.workspace.root / "state").exists()


def test_symlinked_state_root_inside_repository_is_rejected(core):
    link = core.workspace.root / "state-link"
    os.symlink(core.workspace.root, link)
    try:
        with pytest.raises(DomainError) as caught:
            Workspace(core.workspace.root, link, create_state=False)
        assert caught.value.code == "UNSAFE_STATE_PATH"
    finally:
        link.unlink()
