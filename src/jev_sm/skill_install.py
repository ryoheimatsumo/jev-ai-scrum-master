"""Preview-first local Skill installation. Never changes host settings or permissions."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from importlib.resources import files
from pathlib import Path

from . import __version__
from .common import DomainError, canonical
from .workspace import git

SKILL_NAME = "jev-scrum-master"
MANIFEST = ".jev-sm-install.json"


def bundled_files() -> dict[str, bytes]:
    root = files("jev_sm").joinpath("assets", "skills", SKILL_NAME)
    result: dict[str, bytes] = {}

    def walk(node, prefix=""):
        for entry in sorted(node.iterdir(), key=lambda item: item.name):
            if entry.name == "__pycache__" or entry.name.endswith((".pyc", ".pyo")):
                continue
            relative = prefix + entry.name
            if entry.is_dir():
                walk(entry, relative + "/")
            elif entry.is_file():
                result[relative] = entry.read_bytes()
    walk(root)
    if "SKILL.md" not in result:
        raise DomainError("SKILL_ASSETS_MISSING", "Reinstall the complete package including Skill resources")
    return result


def hashes(content: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}


def reject_links(path: Path) -> None:
    # Check lexical parents BEFORE resolve(); do not write through user-managed links.
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise DomainError("UNSAFE_SKILL_PATH", "Skill installation refuses symlinked paths")


def destination(repo: Path, host: str, scope: str, *, home: Path | None = None) -> Path:
    if host not in {"codex", "claude"} or scope not in {"project", "user"}:
        raise DomainError("INVALID_SKILL_TARGET", "Choose codex/claude and project/user")
    base = (home or Path.home()) if scope == "user" else repo
    base = Path(os.path.abspath(base.expanduser()))
    reject_links(base)
    if scope == "project":
        top = Path(git(base, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if top != base.resolve():
            raise DomainError("NOT_REPO_ROOT", "Pass the worktree root with --repo")
    target = base / (".agents" if host == "codex" else ".claude") / "skills" / SKILL_NAME
    reject_links(target)
    return target


def installed_files(target: Path) -> dict[str, bytes]:
    reject_links(target)
    if not target.is_dir():
        raise DomainError("SKILL_CONFLICT", "Existing Skill path is not a directory")
    result = {}
    for entry in target.rglob("*"):
        if entry.is_symlink():
            raise DomainError("UNSAFE_SKILL_PATH", "Existing Skill contains a symlink")
        if entry.is_file():
            result[entry.relative_to(target).as_posix()] = entry.read_bytes()
        elif not entry.is_dir():
            raise DomainError("SKILL_CONFLICT", "Existing Skill has a non-regular entry")
    return result


def inspect_install(target: Path, bundle: dict[str, bytes]) -> dict:
    reject_links(target)
    if not target.exists():
        return {"status": "not_installed", "managed": False}
    existing = installed_files(target)
    try:
        manifest = json.loads(existing.pop(MANIFEST))
        if (manifest.get("owner") != "jev-ai-scrum-master" or manifest.get("schema_version") != 1
                or not isinstance(manifest.get("files"), dict)):
            raise ValueError("Not our manifest")
    except (KeyError, ValueError, TypeError, AttributeError):
        return {"status": "unmanaged", "managed": False}
    if hashes(existing) != manifest["files"]:
        return {"status": "locally_modified", "managed": True,
                "installed_version": manifest.get("version")}
    return {"status": "current" if hashes(existing) == hashes(bundle) else "update_available",
            "managed": True, "installed_version": manifest.get("version")}


def install(repo: Path, host: str, scope: str, *, write: bool = False,
            update: bool = False, home: Path | None = None) -> dict:
    content = bundled_files()
    target = destination(repo, host, scope, home=home)
    state = inspect_install(target, content)
    result = {**state, "target": str(target), "host": host, "scope": scope,
              "package_version": __version__, "files": sorted(content), "written": False,
              "changes_host_settings": False, "requires_mcp": False,
              "note": "Install before plan approval. This is not a host runtime smoke test."}
    if not write:
        return result | {"preview": True, "next_action": "rerun_with_write"}
    if state["status"] == "current":
        return result | {"preview": False}
    if state["status"] in {"unmanaged", "locally_modified"}:
        raise DomainError("SKILL_CONFLICT", "Existing Skill is unmanaged or modified; review it manually")
    if state["status"] == "update_available" and not update:
        raise DomainError("SKILL_UPDATE_REQUIRED", "Review the update, then pass --update --write")
    reject_links(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Cooperative lock for competing installers. Same-OS-user malicious writes are not isolated.
    lock = target.parent / ("." + SKILL_NAME + ".install.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DomainError("SKILL_INSTALL_BUSY", "An installer lock exists; inspect interrupted installs") from exc
    os.close(fd)
    temp = None
    backup = None
    try:
        if inspect_install(target, content) != state:
            raise DomainError("SKILL_CONFLICT", "Skill changed after inspection")
        temp = Path(tempfile.mkdtemp(prefix="." + SKILL_NAME + ".", dir=target.parent))
        for name, data in content.items():
            path = temp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (temp / MANIFEST).write_text(canonical({"schema_version": 1,
            "owner": "jev-ai-scrum-master", "version": __version__, "files": hashes(content)}),
            encoding="utf-8")
        if target.exists():
            backup = target.parent / ("." + SKILL_NAME + ".previous-" + uuid.uuid4().hex)
            target.rename(backup)
        try:
            temp.rename(target)
            temp = None
        except BaseException:
            if backup is not None and not target.exists():
                backup.rename(target)
                backup = None
            raise
        if backup is not None:
            shutil.rmtree(backup)
        return result | {"status": "installed", "written": True, "preview": False,
                         "next_action": "reload_or_restart_host_and_request_the_skill"}
    finally:
        if temp is not None:
            shutil.rmtree(temp, ignore_errors=True)
        lock.unlink(missing_ok=True)
