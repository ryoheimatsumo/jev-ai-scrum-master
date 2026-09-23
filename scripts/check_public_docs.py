#!/usr/bin/env python3
"""Offline checks for paired public guides. Not a semantic translation/security audit."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
BLOCK = re.compile(r"^```[^\n]*\n.*?^```\s*$", re.M | re.S)
OBSOLETE = (
    "OWNER/jev-ai-scrum-master",
    "## Publish this alpha snapshot to GitHub",
    "## Deeper Jev paths without MCP",
    "# AFTER publication:",
)


def check(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        catalog = json.loads((root / "docs/languages.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Cannot read language catalog: {type(exc).__name__}"]
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("pairs"), list):
        return ["Unsupported language catalog"]
    seen: set[str] = set()
    for pair in catalog["pairs"]:
        if not isinstance(pair, dict) or set(pair) != {"en", "ja"}:
            errors.append("Each language pair must contain exactly en and ja")
            continue
        for language, name in pair.items():
            if not isinstance(name, str) or not name:
                errors.append("Language path must be a nonempty string")
                continue
            file = (root / name).resolve()
            if not file.is_relative_to(root):
                errors.append(f"Unsafe language path: {name}")
                continue
            if name in seen:
                errors.append(f"Duplicate language path: {name}")
            seen.add(name)
            try:
                text = file.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                errors.append(f"Missing/unreadable guide: {name}")
                continue
            other = pair["ja" if language == "en" else "en"]
            if not isinstance(other, str):
                errors.append(f"Invalid counterpart: {name}")
                continue
            expected = (root / other).resolve()
            targets = []
            for target in LINK.findall("\n".join(text.splitlines()[:8])):
                parsed = urlsplit(target)
                if not parsed.scheme and not parsed.netloc:
                    targets.append((file.parent / unquote(parsed.path)).resolve())
            if expected not in targets:
                errors.append(f"Missing top-level language switch: {name}")
            if len(re.findall(r"^```", text, re.M)) % 2:
                errors.append(f"Unbalanced fenced code block: {name}")
            prose = BLOCK.sub("", text)
            clean = LINK.sub("", prose).replace("日本語", "")
            if language == "en" and JAPANESE.search(clean):
                errors.append(f"Japanese prose in English guide: {name}")
            if language == "ja" and not JAPANESE.search(clean):
                errors.append(f"Japanese guide has no Japanese prose: {name}")
            for phrase in OBSOLETE:
                if phrase in text:
                    errors.append(f"Obsolete public wording: {name}")
            for target in LINK.findall(prose):
                target = target.strip().split(' "', 1)[0]
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                dest = (file.parent / unquote(parsed.path)).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    errors.append(f"Broken local link in {name}: {target}")
    for name in catalog.get("single_source", []):
        if not isinstance(name, str):
            errors.append("Invalid single-source path")
            continue
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.exists():
            errors.append(f"Missing single-source record: {name}")
    return errors


if __name__ == "__main__":
    problems = check()
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        raise SystemExit(1)
    print("Public documentation pairs, local links, and wording checks passed")
