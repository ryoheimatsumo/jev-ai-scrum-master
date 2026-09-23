"""Human confirmation is deliberately absent from the MCP surface."""
from __future__ import annotations

import getpass
import uuid
from typing import Protocol

from .common import DomainError, canonical, now


class Authority(Protocol):
    def confirm(self, kind: str, content_hash: str, details: dict) -> dict: ...


class TerminalAuthority:
    def confirm(self, kind: str, content_hash: str, details: dict) -> dict:
        try:
            with open("/dev/tty", "r+", encoding="utf-8", buffering=1) as tty:
                if not tty.isatty():
                    raise OSError("No terminal")
                tty.write(f"\n{kind}\n{canonical(details)}\nSHA256: {content_hash}\n")
                expected = f"approve {content_hash[:12]}"
                tty.write(f"Type exactly '{expected}' to approve (anything else cancels): ")
                answer = tty.readline().strip()
        except OSError as exc:
            raise DomainError("HUMAN_CONFIRMATION_REQUIRED", "Run this command in your own terminal") from exc
        if answer != expected:
            raise DomainError("APPROVAL_CANCELLED", "No approval was recorded")
        return {"id": "approval-" + uuid.uuid4().hex, "kind": kind,
                "content_hash": content_hash, "actor": getpass.getuser(),
                "source": "local_tty", "at": now()}
