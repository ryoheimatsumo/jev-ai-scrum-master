#!/usr/bin/env python3
"""Offline publication-hygiene checks. Not a full secret or vulnerability scanner.

Inspect tracked working-tree files, including text inside wheel/ZIP archives.
Report locations and rule names, never matching credential values. Does not inspect
Git history, remote settings, releases, issues, or dependency advisories.
"""
from __future__ import annotations

import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 64 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_MEMBERS = 2000
CREDENTIALS = {
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "provider-token": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "cloud-access-key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
}
MACHINE_PATH = re.compile(r"/(?:mnt/data|Users/[^/\s]+|home/[^/\s]+)/")
HOSTNAME = re.compile(r'hostname="([^"\n]+)"')
EMAIL = re.compile(r"[A-Za-z0-9_.+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".jks", ".sqlite", ".sqlite3", ".db"}


def secret_filename(name: str) -> bool:
    p = PurePosixPath(name)
    return (p.name.startswith(".env") and p.name != ".env.example") or p.suffix.lower() in SECRET_EXTENSIONS or p.name in {"id_rsa", "id_ed25519", "history.bundle"}


def inspect_text(name: str, text: str) -> list[dict]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for rule, pattern in CREDENTIALS.items():
            if pattern.search(line):
                findings.append({"path": name, "line": number, "rule": rule})
        if name.startswith("docs/validation/"):
            if MACHINE_PATH.search(line):
                findings.append({"path": name, "line": number, "rule": "local-machine-path"})
            if any(host not in {"localhost", "redacted-host"} for host in HOSTNAME.findall(line)):
                findings.append({"path": name, "line": number, "rule": "local-hostname"})
            if any(not (domain.endswith(".invalid") or domain in {"example.com", "example.org", "users.noreply.github.com"}) for domain in EMAIL.findall(line)):
                findings.append({"path": name, "line": number, "rule": "review-personal-email"})
    return findings


def inspect_payload(name: str, data: bytes, depth: int = 0, budget: list[int] | None = None) -> tuple[list[dict], int]:
    findings = []
    if budget is None:
        budget = [MAX_BYTES, MAX_MEMBERS]
    if secret_filename(name):
        findings.append({"path": name, "rule": "secret-like-filename"})
    if len(data) > MAX_BYTES:
        return findings + [{"path": name, "rule": "payload-too-large"}], 0
    if PurePosixPath(name).suffix.lower() in {".whl", ".zip"}:
        if depth >= 3:
            return findings + [{"path": name, "rule": "archive-depth-limit"}], 0
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                count = 0
                seen = set()
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    path = PurePosixPath(info.filename)
                    member = name + "!" + info.filename
                    budget[1] -= 1
                    if budget[1] < 0 or info.file_size > MAX_MEMBER or info.file_size > budget[0]:
                        findings.append({"path": member, "rule": "archive-size-limit"})
                        break
                    budget[0] -= info.file_size
                    if path.is_absolute() or ".." in path.parts or "\\" in info.filename or info.filename in seen:
                        findings.append({"path": member, "rule": "unsafe-archive-path"})
                        continue
                    seen.add(info.filename)
                    if (info.external_attr >> 16) & 0o170000 == 0o120000:
                        findings.append({"path": member, "rule": "archive-symlink"})
                        continue
                    if secret_filename(info.filename):
                        findings.append({"path": member, "rule": "secret-like-filename"})
                    more, n = inspect_payload(member, archive.read(info), depth + 1, budget)
                    findings.extend(more)
                    count += n
                return findings, count
        except (BadZipFile, RuntimeError, OSError, ValueError):
            return findings + [{"path": name, "rule": "unreadable-archive"}], 0
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return findings + [{"path": name, "rule": "unreviewed-binary"}], 0
    return findings + inspect_text(name, text), 1


def scan(root: Path = ROOT) -> dict:
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    findings = []
    files = texts = 0
    for name in filter(None, paths):
        path = root / name
        if not path.exists():  # working-tree deletion, pending commit
            continue
        files += 1
        if path.is_symlink():
            findings.append({"path": name, "rule": "tracked-symlink"})
            continue
        if path.stat().st_size > MAX_BYTES:
            findings.append({"path": name, "rule": "payload-too-large"})
            continue
        more, n = inspect_payload(name, path.read_bytes())
        findings.extend(more)
        texts += n
    return {"status": "review_required" if findings else "no_matches",
            "tracked_files": files, "text_payloads_including_archives": texts,
            "findings": findings,
            "scope": "selected patterns in tracked working-tree files and bounded archives; not a security guarantee"}


def main() -> int:
    try:
        result = scan()
        print(json.dumps(result, indent=2))
        return int(bool(result["findings"]))
    except (OSError, subprocess.SubprocessError, UnicodeError):
        print(json.dumps({"status": "error", "message": "Unable to inspect the tracked working tree"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
