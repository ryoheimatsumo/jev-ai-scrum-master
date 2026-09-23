"""Emit actual behavioral outcomes in the jev-sm report format."""
import json
import sys
from pathlib import Path

from app import change_spot, load_spots, save_spots

output = Path(".jev-sm-output")
output.mkdir(exist_ok=True)
original = [{"id": "a", "name": "Old"}, {"id": "b", "name": "Keep"}]
cases = []


def record(identity, check):
    try:
        check()
        cases.append({"id": identity, "status": "passed"})
    except Exception as exc:
        print(identity, type(exc).__name__, str(exc))
        cases.append({"id": identity, "status": "failed"})


def target_only():
    changed = change_spot(original, "a", "New")
    assert changed == [{"id": "a", "name": "New"}, original[1]]
    assert original[0]["name"] == "Old"


def reload():
    path = output / "saved.json"
    changed = change_spot(original, "a", "New")
    save_spots(path, changed)
    del changed
    assert load_spots(path) == [{"id": "a", "name": "New"}, original[1]]


record("change::target-only", target_only)
record("persistence::reload", reload)
(output / "checks.json").write_text(json.dumps({"schema_version": 1, "cases": cases}))
sys.exit(1 if any(c["status"] == "failed" for c in cases) else 0)
