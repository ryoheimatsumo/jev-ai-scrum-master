#!/usr/bin/env python3
"""Bootstrap the bundled CLI without writing to the host or target project.

Stdlib only, Python 3.9+ for this launcher. The CLI needs Python 3.12+.
No package downloads or installation happen during status, preview, or exec.
Hashes detect mismatches; they are not signatures or a same-user security boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

OWNER = "jev-ai-scrum-master"
SKILL_ROOT = Path(__file__).resolve().parents[1]


class SetupError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_info(root=SKILL_ROOT):
    runtime = root / "runtime"
    try:
        manifest = json.loads((runtime / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SetupError("BUNDLE_MISSING", "Runtime not bundled. Use a built marketplace package, or the separately installed jev-sm CLI.") from exc
    if manifest.get("schema_version") != 1 or manifest.get("package") != OWNER:
        raise SetupError("INVALID_BUNDLE", "Unexpected runtime manifest")
    version = manifest.get("version", "")
    filename = manifest.get("wheel", "")
    sha = manifest.get("sha256", "")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:a[0-9]+)?", version):
        raise SetupError("INVALID_BUNDLE", "Unsupported version")
    expected = "jev_ai_scrum_master-" + version + "-py3-none-any.whl"
    if filename != expected or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise SetupError("INVALID_BUNDLE", "Invalid wheel identity")
    path = runtime / filename
    if path.is_symlink() or not path.is_file() or digest(path) != sha:
        raise SetupError("BUNDLE_MISMATCH", "Bundled CLI hash mismatch; reinstall the trusted Skill. Nothing was installed.")
    return manifest, path


def runtime_home():
    configured = os.environ.get("JEV_SM_RUNTIME_HOME")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise SetupError("INVALID_RUNTIME_HOME", "JEV_SM_RUNTIME_HOME must be absolute")
        return path
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/jev-sm/runtimes"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "jev-sm/runtimes"
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    if not base.is_absolute():
        raise SetupError("INVALID_RUNTIME_HOME", "XDG_DATA_HOME must be absolute")
    return base / "jev-sm/runtimes"


def target_for(manifest, with_jev, home=None):
    profile = "jev" if with_jev else "base"
    identity = manifest["version"] + "-" + manifest["sha256"][:16] + "-" + profile
    return (home if home is not None else runtime_home()) / identity


def python_at(target):
    return target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def receipt_for(manifest, with_jev):
    return {"owner": OWNER, "schema_version": 1, "version": manifest["version"],
            "wheel_sha256": manifest["sha256"], "with_jev": with_jev}


def reject_links(path):
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise SetupError("UNSAFE_RUNTIME_PATH", "Runtime destination may not be a symbolic link")


def inspect(manifest, with_jev, home=None):
    target = target_for(manifest, with_jev, home)
    reject_links(target)
    expected = receipt_for(manifest, with_jev)
    status = "not_installed"
    if target.exists():
        try:
            receipt = json.loads((target / "jev-sm-runtime.json").read_text(encoding="utf-8"))
            valid = all(receipt.get(k) == v for k, v in expected.items())
            status = "ready" if valid and python_at(target).is_file() else "invalid_installation"
        except (ValueError, OSError):
            status = "invalid_installation"
    return {"status": status, "version": manifest["version"], "with_jev": with_jev,
            "runtime_dir": str(target), "python": str(python_at(target)),
            "network_performed": False, "project_changed": False,
            "jev_calls_enabled": False, "mcp_required": False,
            "note": "SDK installation is not permission to send project data. Enable Jev separately per project."}


def install_environment():
    # Never pass model/cloud/GitHub credentials or project Python settings to installers.
    allowed = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
               "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    return {k: v for k, v in os.environ.items() if k in allowed}


def run_install(argv, cwd, env):
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError("SETUP_FAILED", "Runtime setup could not complete; no ready receipt was written.") from exc
    if result.returncode:
        # Do not echo package-manager output containing machine paths or credentials.
        raise SetupError("SETUP_FAILED", "Runtime dependency installation failed (exit %s). Check network access, Python version and wheel availability." % result.returncode)


def find_python():
    candidates = [sys.executable]
    for name in ("python3.14", "python3.13", "python3.12", "python3", "python"):
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)
    for candidate in candidates:
        try:
            answer = subprocess.run([candidate, "-I", "-c", "import sys; print(int(sys.version_info >= (3,12)))"],
                                    capture_output=True, timeout=10, env=install_environment())
            if answer.returncode == 0 and answer.stdout.strip() == b"1":
                return candidate
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None


def check_home_for_write(home):
    reject_links(home)
    home_abs = home.resolve()
    if home_abs == SKILL_ROOT or SKILL_ROOT in home_abs.parents:
        raise SetupError("UNSAFE_RUNTIME_PATH", "Runtime must live outside the Skill/plugin directory")
    existing = home
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    if shutil.which("git"):
        probe = subprocess.run(["git", "-C", str(existing), "rev-parse", "--show-toplevel"],
                               capture_output=True, env=install_environment(), timeout=10)
        if probe.returncode == 0:
            raise SetupError("RUNTIME_IN_WORKTREE", "Choose a runtime directory outside Git worktrees")


def setup(manifest, wheel, *, with_jev=False, write=False, allow_downloads=False,
          wheelhouse=None, home=None):
    state = inspect(manifest, with_jev, home)
    if state["status"] == "ready":
        return state | {"installed": False, "preview": not write}
    if state["status"] == "invalid_installation":
        raise SetupError("INVALID_INSTALLATION", "Existing runtime is incomplete or mismatched. Inspect it before removing it; it was not overwritten.")
    state.update({"preview": not write, "installed": False,
                  "downloads_allowed": allow_downloads,
                  "next_action": "Review setup, then invoke setup --write --allow-downloads (or --wheelhouse for offline setup)."})
    if not write:
        return state
    if allow_downloads and wheelhouse:
        raise SetupError("INVALID_OPTIONS", "Choose either online setup or an offline wheelhouse")
    if not allow_downloads and wheelhouse is None:
        raise SetupError("DOWNLOAD_CONSENT_REQUIRED", "No automatic downloads. Approve --allow-downloads or provide an offline --wheelhouse.")
    if wheelhouse is not None:
        wheelhouse = Path(wheelhouse).expanduser().resolve()
        if not wheelhouse.is_dir():
            raise SetupError("INVALID_WHEELHOUSE", "Offline wheelhouse does not exist")
    interpreter = find_python()
    uv = shutil.which("uv")
    if interpreter is None and not (uv and allow_downloads):
        raise SetupError("PYTHON_REQUIRED", "Install Python 3.12+, or install uv and explicitly allow downloads. Nothing was installed.")
    target = Path(state["runtime_dir"])
    home = target.parent
    check_home_for_write(home)
    home.mkdir(parents=True, exist_ok=True)
    lock = home / ("." + target.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SetupError("SETUP_BUSY", "A setup lock exists. Wait for the running setup, or inspect an interrupted one.") from exc
    os.close(fd)
    staging = None
    try:
        if target.exists():
            raise SetupError("SETUP_BUSY", "Runtime changed after inspection; retry status")
        staging = Path(tempfile.mkdtemp(prefix=".install-", dir=home))
        env = install_environment()
        if interpreter:
            run_install([interpreter, "-I", "-m", "venv", str(staging)], home, env)
        else:
            # uv is user-installed; this never installs uv or changes shell startup files.
            run_install([uv, "--no-config", "venv", "--python", "3.12", "--seed", str(staging)], home, env)
        pip = [str(python_at(staging)), "-I", "-m", "pip", "--isolated", "install",
               "--disable-pip-version-check", "--no-input", "--only-binary=:all:"]
        if allow_downloads:
            pip += ["--index-url", "https://pypi.org/simple"]
        else:
            pip += ["--no-index", "--find-links", str(wheelhouse)]
        # Snapshot the validated wheel; check again to detect changes since inspection.
        copied = staging / wheel.name
        shutil.copyfile(wheel, copied)
        if digest(copied) != manifest["sha256"]:
            raise SetupError("BUNDLE_MISMATCH", "Runtime bundle changed during setup")
        package = str(copied) + ("[jev]" if with_jev else "")
        run_install(pip + [package], home, env)
        run_install([str(python_at(staging)), "-I", "-m", "pip", "--isolated", "check"], home, env)
        probe = "import importlib.metadata as m; assert m.version('jev-ai-scrum-master') == " + repr(manifest["version"])
        probe += "; import jev_sm.cli"
        if with_jev:
            probe += "; import typesafe_sdk"
        run_install([str(python_at(staging)), "-I", "-c", probe], home, env)
        copied.unlink()
        receipt = receipt_for(manifest, with_jev) | {"installed_at": int(time.time()),
                    "downloads_allowed": allow_downloads}
        (staging / "jev-sm-runtime.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        staging.rename(target)
        staging = None
        return inspect(manifest, with_jev, home) | {"installed": True, "preview": False,
                "network_performed": "package_manager_may_have_downloaded" if allow_downloads else False}
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("status", "setup", "exec"):
        p = sub.add_parser(name)
        p.add_argument("--with-jev", action="store_true", help="Use the runtime that includes the optional Jev SDK")
        if name == "setup":
            p.add_argument("--write", action="store_true")
            p.add_argument("--allow-downloads", action="store_true")
            p.add_argument("--wheelhouse", type=Path)
        if name == "exec":
            p.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        manifest, wheel = bundle_info()
        if args.action == "setup":
            answer = setup(manifest, wheel, with_jev=args.with_jev, write=args.write,
                           allow_downloads=args.allow_downloads, wheelhouse=args.wheelhouse)
        elif args.action == "status":
            answer = inspect(manifest, args.with_jev)
        else:
            answer = inspect(manifest, args.with_jev)
            if answer["status"] != "ready":
                raise SetupError("SETUP_REQUIRED", "Run setup preview and approve installation first. exec never downloads anything.")
            forwarded = args.args[1:] if args.args[:1] == ["--"] else args.args
            if not forwarded:
                raise SetupError("CLI_ARGUMENTS_REQUIRED", "Provide CLI arguments after exec --")
            # Use python -m: venv console-script shebangs can point to the staging directory.
            return subprocess.call([answer["python"], "-I", "-m", "jev_sm", *forwarded])
        print(json.dumps(answer, ensure_ascii=False, indent=2))
        return 0
    except SetupError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": str(exc)}}, ensure_ascii=False))
        return 2
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print(json.dumps({"error": {"code": "RUNTIME_ERROR", "message": "Runtime operation failed; inspect local installation and permissions."}}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
