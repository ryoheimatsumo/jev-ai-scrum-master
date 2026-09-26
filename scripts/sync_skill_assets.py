#!/usr/bin/env python3
"""Mirror packaged canonical Skill assets into discoverable repo skills/; --check for CI."""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/jev_sm/assets/skills/jev-scrum-master"
TARGET = ROOT / "skills/jev-scrum-master"
TEMPLATE = "SKILL.template.md"


def inventory(path):
    result = {}
    for p in path.rglob("*"):
        if p.is_file() and "runtime" not in p.relative_to(path).parts and "__pycache__" not in p.parts:
            name = p.relative_to(path).as_posix()
            name = "SKILL.md" if name == TEMPLATE else name
            if name in result:
                raise ValueError("Packaged Skill contains duplicate manifest names: " + name)
            result[name] = p.read_bytes()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        if inventory(SOURCE) != inventory(TARGET):
            raise SystemExit("Skill mirror differs; run python scripts/sync_skill_assets.py")
        print("Skill mirror matches packaged source")
    else:
        # Runtime is a generated, self-contained wheel; not mirrored into the wheel itself.
        saved = None
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            if (TARGET / "runtime").exists():
                saved = Path(temp) / "runtime"
                shutil.copytree(TARGET / "runtime", saved)
            if TARGET.exists():
                shutil.rmtree(TARGET)
            shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            if saved:
                shutil.copytree(saved, TARGET / "runtime")
