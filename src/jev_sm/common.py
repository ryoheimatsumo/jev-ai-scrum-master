"""Small deterministic primitives shared by the core and adapters."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


def now() -> str:
    return datetime.now(UTC).isoformat()


def canonical(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


class DomainError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or "\\" in value or "\x00" in value or path.is_absolute() or ".." in path.parts:
        raise ValueError("A relative POSIX path without '..' is required")
    return value


def inside(root: Path, value: str, *, must_exist: bool = False) -> Path:
    relative_path(value)
    root = root.resolve()
    candidate = root / value
    # Reject symlinks at every component, even if they point inside the root.
    walk = root
    for part in PurePosixPath(value).parts:
        walk = walk / part
        if walk.is_symlink():
            raise DomainError("UNSAFE_PATH", "Symlinks are not supported in managed input/output paths")
    result = candidate.resolve()
    if not result.is_relative_to(root):
        raise DomainError("UNSAFE_PATH", "Path escapes the workspace")
    if must_exist and not result.exists():
        raise DomainError("MISSING_INPUT", f"Required path does not exist: {value}")
    return result


_SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|access[_-]?token|password|secret)"
    r"(\s*[:=]\s*)(?:Bearer\s+)?([^\s,;\"']+)"
)


def redact(text: str) -> str:
    """Best-effort masking, NOT a confidentiality or DLP guarantee."""
    for name, value in os.environ.items():
        if re.search(r"KEY|TOKEN|SECRET|PASSWORD", name) and len(value) >= 8:
            text = text.replace(value, "[REDACTED]")
    return _SECRET.sub(lambda m: m[1] + m[2] + "[REDACTED]", text)
