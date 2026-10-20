from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from jev_sm.common import DomainError
from jev_sm.models import Settings
from jev_sm.workspace import Workspace


def _git(root: Path, *args: str, protocol: bool = False) -> None:
    command = ["git", "-C", str(root)]
    if protocol:
        command.extend(["-c", "protocol.file.allow=always"])
    subprocess.run(command + list(args), check=True, capture_output=True)


def _commit(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-m", message)


def _repo(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-b", "main")


def _workspace(tmp_path: Path, *, settings: Settings | None = None,
               nested: bool = False, files: dict[str, str] | None = None):
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    _repo(source)
    for name, content in (files or {"module.py": "VALUE = 1\n"}).items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    if nested:
        nested_source = tmp_path / "nested-source"
        _repo(nested_source)
        (nested_source / "nested.py").write_text("NESTED = 1\n")
        _commit(nested_source, "nested")
        _git(source, "submodule", "add", str(nested_source), "nested", protocol=True)
    _commit(source, "source")
    _repo(repo)
    (repo / "app.py").write_text("APP = 1\n")
    _commit(repo, "root")
    _git(repo, "submodule", "add", str(source), "module", protocol=True)
    _commit(repo, "submodule")
    (repo / ".jev-sm").mkdir()
    config = settings or Settings()
    (repo / ".jev-sm" / "config.yaml").write_text(yaml.safe_dump(config.model_dump(mode="json")))
    return repo, Workspace(repo, tmp_path / "state")


@pytest.mark.parametrize("state", ["missing", "empty"])
def test_uninitialized_gitlink_presence_is_preserved_in_snapshot(tmp_path, state):
    repo, workspace = _workspace(tmp_path)
    _git(repo, "submodule", "deinit", "-f", "--", "module")
    if state == "missing":
        (repo / "module").rmdir()
    manifest = workspace.manifest()
    assert manifest["module"]["initialized"] is False
    assert manifest["module"]["present"] is (state == "empty")
    snap = workspace.snapshot("presence-" + state)
    assert (Path(snap["path"]) / "module").exists() is (state == "empty")


def test_uninitialized_nested_gitlink_marker_is_retained(tmp_path):
    repo, workspace = _workspace(tmp_path, nested=True)
    _git(repo / "module", "submodule", "deinit", "-f", "--", "nested")
    (repo / "module" / "nested").rmdir()
    manifest = workspace.manifest()
    assert manifest["module/nested"]["kind"] == "submodule"
    assert manifest["module/nested"]["initialized"] is False
    assert manifest["module/nested"]["present"] is False


def test_multiple_uninitialized_gitlinks_count_toward_file_limit(tmp_path):
    source = tmp_path / "source"
    _repo(source)
    (source / "module.py").write_text("VALUE = 1\n")
    _commit(source, "source")
    repo = tmp_path / "repo"
    _repo(repo)
    (repo / "app.py").write_text("APP = 1\n")
    _commit(repo, "root")
    for name in ("one", "two"):
        _git(repo, "submodule", "add", str(source), name, protocol=True)
        _git(repo, "submodule", "deinit", "-f", "--", name)
    _commit(repo, "submodules")
    (repo / ".jev-sm").mkdir()
    (repo / ".jev-sm" / "config.yaml").write_text(
        yaml.safe_dump(Settings(max_snapshot_files=2).model_dump(mode="json")))
    workspace = Workspace(repo, tmp_path / "state")
    with pytest.raises(DomainError, match="Snapshot limits exceeded|Too many input files"):
        workspace.manifest()


@pytest.mark.parametrize("setting", ["max_snapshot_files", "max_snapshot_bytes"])
def test_root_and_submodule_share_aggregate_limits(tmp_path, setting):
    value = 3 if setting == "max_snapshot_files" else 1024
    files = {"large.bin": "x" * 2048}
    repo, workspace = _workspace(tmp_path, settings=Settings(**{setting: value}), files=files)
    with pytest.raises(DomainError, match="limit|Too many"):
        workspace.manifest()


def test_submodule_secrets_and_dependency_cache_are_excluded(tmp_path):
    repo, workspace = _workspace(tmp_path, files={
        "app.py": "APP = 1\n", ".env": "SECRET=hidden\n", ".env.example": "SECRET=example\n",
        "private.pem": "private\n", "node_modules/cache.js": "cache\n",
        "__pycache__/cache.pyc": "cache\n",
    })
    manifest = workspace.manifest()
    assert "module/app.py" in manifest
    assert "module/.env.example" in manifest
    for excluded in ("module/.env", "module/private.pem", "module/node_modules/cache.js",
                     "module/__pycache__/cache.pyc"):
        assert excluded not in manifest
    snap = workspace.snapshot("excluded")
    snap_root = Path(snap["path"])
    assert not (snap_root / "module/.env").exists()
    assert (snap_root / "module/.env.example").exists()
    assert not (snap_root / "module/node_modules").exists()


@pytest.mark.parametrize("broken", ["git-file", "nonempty-no-git"])
def test_broken_or_non_git_submodule_is_rejected(tmp_path, broken):
    repo, workspace = _workspace(tmp_path)
    git_marker = repo / "module" / ".git"
    if broken == "git-file":
        git_marker.write_text("not a gitdir\n")
    else:
        git_marker.unlink()
    with pytest.raises(DomainError):
        workspace.manifest()


@pytest.mark.parametrize("change", ["file", "initialization"])
def test_snapshot_rejects_submodule_changes_during_copy(tmp_path, monkeypatch, change):
    repo, workspace = _workspace(tmp_path)
    original = shutil.copy2
    changed = False

    def copy_and_change(source, target, *args, **kwargs):
        nonlocal changed
        result = original(source, target, *args, **kwargs)
        if not changed and str(source).endswith("module/module.py"):
            changed = True
            if change == "file":
                Path(source).write_text("changed\n")
            else:
                _git(repo, "submodule", "deinit", "-f", "--", "module")
        return result

    monkeypatch.setattr("jev_sm.workspace.shutil.copy2", copy_and_change)
    with pytest.raises(DomainError, match="SNAPSHOT_CHANGED|changed"):
        workspace.snapshot("changing")
