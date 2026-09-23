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
    def __init__(self, root: Path, state_root: Path | None = None):
        self.root = root.resolve()
        top = Path(git(self.root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if self.root != top:
            raise DomainError("NOT_REPO_ROOT", "Pass the Git worktree root with --repo")
        self.id = digest(str(self.root))[:24]
        if state_root is None:
            if sys.platform == "darwin":
                base = Path.home() / "Library/Application Support"
            else:
                base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
            state_root = base / "jev-sm"
        self.state_dir = state_root.resolve() / self.id
        if self.state_dir.is_relative_to(self.root):
            raise DomainError("UNSAFE_STATE_PATH", "State and approval records must live outside the repository")
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

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
            if not path.is_file():
                raise DomainError("UNSUPPORTED_INPUT", f"Submodule or non-regular input: {name}")
            paths.append(name)
        if len(paths) > settings.max_snapshot_files:
            raise DomainError("SNAPSHOT_LIMIT", "Too many input files; explicit scope support is not implemented")
        return paths

    def manifest(self, root: Path | None = None, paths: list[str] | None = None) -> dict:
        base = root or self.root
        paths = paths if paths is not None else self.source_paths()
        result, size = {}, 0
        for name in paths:
            path = inside(base, name, must_exist=True)
            size += path.stat().st_size
            if size > self.settings().max_snapshot_bytes:
                raise DomainError("SNAPSHOT_LIMIT", "Snapshot byte limit exceeded")
            result[name] = {"sha256": file_hash(path), "executable": bool(path.stat().st_mode & 0o111)}
        return result

    def content_hash(self) -> str:
        return digest(self.manifest())

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
            source = inside(self.root, name, must_exist=True)
            target = inside(path, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
        copied = self.manifest(path, list(before))
        after = self.manifest()
        if before != after or before != copied:
            raise DomainError("SNAPSHOT_CHANGED", "Inputs changed while the snapshot was being copied")
        return {"path": str(path), "manifest": before, "hash": digest(before), "head": self.head(),
                "config_hash": digest(settings), "environment_hash": self.environment_hash()}

    def snapshot_unchanged(self, snap: dict) -> bool:
        try:
            root = Path(snap["path"])
            if self.manifest(root, list(snap["manifest"])) != snap["manifest"]:
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
