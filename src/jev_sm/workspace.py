"""Content snapshots include dirty and untracked source files, not only HEAD."""
from __future__ import annotations

import fnmatch
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .common import DomainError, canonical, digest, file_hash, inside
from .models import Settings


def git(root: Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args],
                              capture_output=True, check=True, env=env, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise DomainError("GIT_UNAVAILABLE", "A local Git repository and Git executable are required") from exc


class Workspace:
    def __init__(self, root: Path, state_root: Path | None = None, *, create_state: bool = True):
        self.root = root.resolve()
        top = Path(git(self.root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if self.root != top:
            raise DomainError("NOT_REPO_ROOT", "Pass the Git worktree root with --repo")
        self.id = digest(str(self.root))[:24]
        self.state_source = "explicit" if state_root is not None else "default"
        if state_root is None:
            if sys.platform == "darwin":
                base = Path.home() / "Library/Application Support"
            else:
                base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
            state_root = base / "jev-sm"
        self.state_dir = state_root.resolve() / self.id
        if self.state_dir.is_relative_to(self.root):
            raise DomainError("UNSAFE_STATE_PATH", "State and approval records must live outside the repository")
        if create_state:
            try:
                self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError as exc:
                raise DomainError(
                    "STATE_UNAVAILABLE",
                    f"Cannot create state directory {self.state_dir}; grant access to this path or choose a writable --state-dir, then retry. Existing approval history remains at this selected root.",
                    retryable=True,
                ) from exc

    def state_status(self) -> dict:
        """Describe the selected state location without touching the filesystem."""
        try:
            exists = self.state_dir.exists()
        except OSError:
            return {"path": str(self.state_dir), "source": self.state_source,
                    "exists": None, "access": "unavailable", "writability": "unverified"}
        return {
            "path": str(self.state_dir),
            "source": self.state_source,
            "exists": exists,
            "access": "unverified",
            "writability": "unverified",
        }

    @property
    def config_path(self) -> Path:
        return inside(self.root, ".jev-sm/config.yaml")

    def settings(self) -> Settings:
        if not self.config_path.exists():
            raise DomainError("NOT_INITIALIZED", "Run jev-sm init and configure checks first")
        if self.config_path.stat().st_size > 262144:
            raise DomainError("CONFIG_TOO_LARGE", "Configuration is too large")
        return Settings.model_validate(yaml.safe_load(self.config_path.read_text()) or {})

    def config_hash(self) -> str:
        return digest(self.settings())

    def head(self) -> str | None:
        try:
            return git(self.root, "rev-parse", "--verify", "HEAD").decode().strip()
        except DomainError:
            return None

    @staticmethod
    def secret_path(path: str) -> bool:
        parts = Path(path).parts
        return any(p == ".env" or p.startswith(".env.") and p != ".env.example" for p in parts) or (
            Path(path).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
        )

    def source_paths(self) -> list[str]:
        # Include tracked + untracked, INCLUDING gitignored source. Exclude only fixed,
        # human-visible dependency/cache directories and known secret/output paths.
        settings = self.settings()
        raw = git(self.root, "ls-files", "--cached", "--others", "-z")
        stage = self._stage_entries(self.root)
        paths = []
        for name in sorted(set(x.decode("utf-8") for x in raw.split(b"\0") if x)):
            parts = Path(name).parts
            if ".git" in parts or ".jev-sm-output" in parts:
                continue
            if any(p in settings.excluded_directories for p in parts):
                continue
            if self.secret_path(name):
                continue
            path = inside(self.root, name)
            if not path.exists():  # Tracked deletion is reflected by absence in the manifest.
                continue
            # Gitlinks are represented by a directory when initialized and by a
            # missing path otherwise.  Their contents are collected by manifest.
            if stage.get(name, (0, ""))[0] == 0o160000:
                continue
            if not path.is_file():
                raise DomainError("UNSUPPORTED_INPUT", f"Submodule or non-regular input: {name}")
            paths.append(name)
        if len(paths) > settings.max_snapshot_files:
            raise DomainError("SNAPSHOT_LIMIT", "Too many input files; explicit scope support is not implemented")
        return paths

    def _gitlink_mode(self, name: str) -> bool:
        """Return whether the index records *name* as a gitlink (mode 160000)."""
        raw = git(self.root, "ls-files", "--stage", "-z", "--", name)
        return any(item.startswith(b"160000 ") for item in raw.split(b"\0") if item)

    def _stage_entries(self, root: Path) -> dict[str, tuple[int, str]]:
        raw = git(root, "ls-files", "--stage", "-z")
        result = {}
        for item in raw.split(b"\0"):
            if not item:
                continue
            header, name = item.split(b"\t", 1)
            mode, commit, _stage = header.decode("ascii").split()
            result[name.decode("utf-8")] = (int(mode, 8), commit)
        return result

    def _submodule_meta(self, name: str, commit: str, base: Path) -> dict:
        path = inside(base, name)
        present = path.exists()
        if present and (not path.is_dir() or path.is_symlink()):
            raise DomainError("UNSAFE_INPUT", f"Submodule path is not a safe directory: {name}")
        initialized = present
        head = None
        dirty = untracked = False
        if initialized:
            try:
                top = Path(git(path, "rev-parse", "--show-toplevel").decode().strip()).resolve()
                if top != path.resolve():
                    if any(item.name != ".git" for item in path.iterdir()):
                        raise DomainError("UNSAFE_INPUT", f"Submodule directory is not initialized: {name}")
                    initialized = False
                    return {"kind": "submodule", "mode": 160000, "commit": commit,
                            "initialized": False, "present": present, "head": None, "dirty": False,
                            "untracked": False}
                head = git(path, "rev-parse", "--verify", "HEAD").decode().strip()
                status = git(path, "status", "--porcelain", "--untracked-files=all")
                dirty = bool(status)
                untracked = any(line and line[:2] == b"??" for line in status.splitlines())
            except DomainError:
                if (path / ".git").exists() or any(path.iterdir()):
                    raise
                initialized = False
        return {"kind": "submodule", "mode": 160000, "commit": commit,
                "initialized": initialized, "present": present, "head": head, "dirty": dirty,
                "untracked": untracked}

    def _collect_submodule(self, name: str, commit: str, base: Path, output: dict,
                           total: list[int], seen: set[Path],
                           errors: list[dict] | None = None) -> None:
        """Collect a gitlink, optionally retaining diagnostic errors per child.

        Production manifest collection leaves ``errors`` unset so the first
        invalid input remains fail-closed.  Doctor passes a sink to inspect all
        siblings in a module without treating partial inventory as a manifest.
        """
        total[0] += 1
        if total[0] > self.settings().max_snapshot_files:
            raise DomainError("SNAPSHOT_LIMIT", "Too many input files; explicit scope support is not implemented")
        meta = self._submodule_meta(name, commit, base)
        output[name] = meta
        if not meta["initialized"]:
            return
        path = inside(base, name, must_exist=True)
        real = path.resolve()
        if real in seen:
            raise DomainError("UNSAFE_INPUT", f"Repeated submodule path: {name}")
        seen.add(real)
        try:
            stage = self._stage_entries(path)
            raw = git(path, "ls-files", "--cached", "--others", "-z")
        except DomainError as exc:
            raise DomainError("UNSAFE_INPUT", f"Initialized submodule is not readable: {name}") from exc
        names = sorted(set(x.decode("utf-8") for x in raw.split(b"\0") if x))
        for child in names:
            if child in {".", "./"}:
                continue
            relative = f"{name}/{child}"
            if ".git" in Path(child).parts or ".jev-sm-output" in Path(child).parts:
                continue
            if any(part in self.settings().excluded_directories for part in Path(child).parts):
                continue
            if self.secret_path(relative):
                continue
            child_stage = stage.get(child)
            if child_stage and child_stage[0] == 0o160000:
                try:
                    self._collect_submodule(relative, child_stage[1], base, output, total, seen,
                                            errors)
                except (DomainError, OSError) as exc:
                    if errors is None:
                        raise
                    detail = (exc.as_dict() if isinstance(exc, DomainError)
                              else {"code": "UNSAFE_INPUT", "message": str(exc),
                                    "retryable": False})
                    if relative not in detail["message"]:
                        detail["message"] = f"{detail['message']}: {relative}"
                    errors.append(detail)
                continue
            try:
                # Resolve inside the same diagnostic boundary as the type and
                # stat checks so unsafe child paths are listed with siblings.
                child_path = inside(path, child)
                if not child_path.exists():
                    continue
                if not child_path.is_file():
                    raise DomainError("UNSUPPORTED_INPUT", f"Submodule or non-regular input: {relative}")
                total[0] += 1
                if total[0] > self.settings().max_snapshot_files:
                    raise DomainError("SNAPSHOT_LIMIT", "Too many input files; explicit scope support is not implemented")
                size = child_path.stat().st_size
                total[1] += size
                if total[1] > self.settings().max_snapshot_bytes:
                    raise DomainError("SNAPSHOT_LIMIT", "Snapshot byte limit exceeded")
                output[relative] = {"sha256": file_hash(child_path),
                                    "executable": bool(child_path.stat().st_mode & 0o111)}
            except (DomainError, OSError) as exc:
                if errors is None:
                    raise
                detail = (exc.as_dict() if isinstance(exc, DomainError)
                          else {"code": "UNSAFE_INPUT", "message": str(exc),
                                "retryable": False})
                if relative not in detail["message"]:
                    detail["message"] = f"{detail['message']}: {relative}"
                errors.append(detail)
        seen.remove(real)

    def manifest(self, root: Path | None = None, paths: list[str] | None = None) -> dict:
        base = root or self.root
        if base == self.root and paths is None:
            result, total = {}, [0, 0]
            stage = self._stage_entries(self.root)
            raw = git(self.root, "ls-files", "--cached", "--others", "-z")
            names = sorted(set(x.decode("utf-8") for x in raw.split(b"\0") if x))
            for name in names:
                parts = Path(name).parts
                if ".git" in parts or ".jev-sm-output" in parts:
                    continue
                settings = self.settings()
                if any(p in settings.excluded_directories for p in parts) or self.secret_path(name):
                    continue
                path = inside(self.root, name)
                mode = stage.get(name, (0, ""))[0]
                if mode == 0o160000:
                    self._collect_submodule(name, stage[name][1], self.root, result, total, set())
                    continue
                if not path.exists():
                    continue
                if not path.is_file():
                    raise DomainError("UNSUPPORTED_INPUT", f"Submodule or non-regular input: {name}")
                total[0] += 1
                total[1] += path.stat().st_size
                if total[0] > settings.max_snapshot_files or total[1] > settings.max_snapshot_bytes:
                    raise DomainError("SNAPSHOT_LIMIT", "Snapshot limits exceeded")
                result[name] = {"sha256": file_hash(path), "executable": bool(path.stat().st_mode & 0o111)}
            return result
        paths = paths if paths is not None else self.source_paths()
        result, size = {}, 0
        for name in paths:
            path = inside(base, name, must_exist=True)
            size += path.stat().st_size
            if size > self.settings().max_snapshot_bytes:
                raise DomainError("SNAPSHOT_LIMIT", "Snapshot byte limit exceeded")
            result[name] = {"sha256": file_hash(path), "executable": bool(path.stat().st_mode & 0o111)}
        return result

    def _snapshot_manifest(self, root: Path, expected: dict) -> dict:
        """Hash a copied snapshot using the typed source manifest as its schema."""
        result = {}
        for name, meta in expected.items():
            if meta.get("kind") == "submodule":
                target = inside(root, name)
                if meta.get("initialized") and (not target.is_dir() or target.is_symlink()):
                    raise DomainError("MISSING_INPUT", f"Required submodule is missing: {name}")
                if meta.get("present") != target.exists():
                    raise DomainError("SNAPSHOT_CHANGED", f"Submodule presence changed: {name}")
                if not meta.get("initialized") and target.exists() and not target.is_dir():
                    raise DomainError("SNAPSHOT_CHANGED", f"Uninitialized submodule changed type: {name}")
                result[name] = meta
                continue
            target = inside(root, name, must_exist=True)
            if not target.is_file():
                raise DomainError("UNSUPPORTED_INPUT", f"Non-regular snapshot input: {name}")
            result[name] = {"sha256": file_hash(target),
                            "executable": bool(target.stat().st_mode & 0o111)}
        return result

    def content_hash(self) -> str:
        return digest(self.manifest())

    def input_diagnostics(self) -> dict:
        """Read-only compatibility report suitable for doctor/preflight output."""
        result = {"compatible": True, "submodules": [], "errors": [],
                  "limits": {"max_files": None, "max_bytes": None,
                              "files": None, "bytes": None}}
        try:
            settings = self.settings()
            result["limits"].update({"max_files": settings.max_snapshot_files,
                                      "max_bytes": settings.max_snapshot_bytes})
            stage = self._stage_entries(self.root)
            raw = git(self.root, "ls-files", "--cached", "--others", "-z")
            inventory, total = {}, [0, 0]
            for name in sorted(set(x.decode("utf-8") for x in raw.split(b"\0") if x)):
                if name.endswith("/"):
                    name = name.rstrip("/")
                parts = Path(name).parts
                if ".git" in parts or ".jev-sm-output" in parts or self.secret_path(name):
                    continue
                if any(p in settings.excluded_directories for p in parts):
                    continue
                try:
                    if stage.get(name, (0, ""))[0] == 0o160000:
                        self._collect_submodule(name, stage[name][1], self.root, inventory, total,
                                                 set(), result["errors"])
                        # Include root and nested gitlinks that were actually
                        # inspected. Partial inventory is diagnostic-only.
                        continue
                    path = inside(self.root, name)
                    if not path.exists():
                        continue
                    if not path.is_file():
                        raise DomainError("UNSUPPORTED_INPUT", f"Submodule or non-regular input: {name}")
                    total[0] += 1
                    total[1] += path.stat().st_size
                    if total[0] > settings.max_snapshot_files or total[1] > settings.max_snapshot_bytes:
                        raise DomainError("SNAPSHOT_LIMIT", "Snapshot limits exceeded")
                except (DomainError, OSError) as exc:
                    result["errors"].append(exc.as_dict() if isinstance(exc, DomainError)
                                             else {"code": "UNSAFE_INPUT", "message": str(exc), "retryable": False})
            for module_name, value in inventory.items():
                if value.get("kind") != "submodule":
                    continue
                result["submodules"].append({
                    "path": module_name, "registered_commit": value["commit"],
                    "initialized": value["initialized"], "head": value["head"],
                    "dirty": value["dirty"], "untracked": value["untracked"]})
            result["limits"].update({"files": total[0], "bytes": total[1]})
        except DomainError as exc:
            result["errors"].append(exc.as_dict())
        result["compatible"] = not result["errors"]
        return result

    def protected_manifest(self, manifest: dict | None = None) -> dict:
        manifest = manifest if manifest is not None else self.manifest()
        globs = self.settings().protected_globs
        command_inputs = {arg for check in self.settings().checks.values() for arg in check.argv[1:]
                          if arg in manifest}
        return {name: meta for name, meta in manifest.items()
                if name in command_inputs or any(fnmatch.fnmatch(name, p) for p in globs)}

    def protected_hash(self) -> str:
        return digest(self.protected_manifest())

    def environment_hash(self) -> str:
        # Does not pretend to fingerprint remote services or all system libraries.
        commands = {}
        for name, check in self.settings().checks.items():
            binary = check.argv[0]
            resolved = shutil.which(binary) if not Path(binary).is_absolute() else binary
            if resolved and Path(resolved).is_file():
                path = Path(resolved).resolve()
                commands[name] = {"path": str(path), "sha256": file_hash(path)}
            else:
                commands[name] = {"unavailable": binary}
        return digest({"platform": platform.platform(), "python": sys.version,
                       "commands": commands})

    def snapshot(self, run_id: str) -> dict:
        settings = self.settings()
        before = self.manifest()
        path = self.state_dir / "snapshots" / run_id
        path.mkdir(parents=True, exist_ok=False, mode=0o700)
        for name in before:
            if before[name].get("kind") == "submodule":
                if before[name].get("initialized") or before[name].get("present"):
                    inside(path, name).mkdir(parents=True, exist_ok=True)
                continue
            source = inside(self.root, name, must_exist=True)
            target = inside(path, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
        copied = self._snapshot_manifest(path, before)
        after = self.manifest()
        if before != after or before != copied:
            raise DomainError("SNAPSHOT_CHANGED", "Inputs changed while the snapshot was being copied")
        return {"path": str(path), "manifest": before, "hash": digest(before), "head": self.head(),
                "config_hash": digest(settings), "environment_hash": self.environment_hash()}

    def snapshot_unchanged(self, snap: dict) -> bool:
        try:
            root = Path(snap["path"])
            if self._snapshot_manifest(root, snap["manifest"]) != snap["manifest"]:
                return False
            # Detect newly introduced source files inside the run, not only changed originals.
            known = set(snap["manifest"])
            for parent, dirs, files in os.walk(root, followlinks=False):
                dirs[:] = [d for d in dirs if d not in {".jev-sm-output", "__pycache__", ".pytest_cache"}]
                for dirname in dirs:
                    if (Path(parent) / dirname).is_symlink():
                        return False
                for filename in files:
                    relative = (Path(parent) / filename).relative_to(root).as_posix()
                    if relative not in known:
                        return False
            return True
        except (DomainError, OSError):
            return False

    def save_snapshot_metadata(self, run_id: str, snap: dict):
        path = self.state_dir / "artifacts" / run_id
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        (path / "snapshot.json").write_text(canonical(snap), encoding="utf-8")
