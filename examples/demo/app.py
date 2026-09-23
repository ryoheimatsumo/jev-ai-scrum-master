"""Minimal persistence fixture; not the user's travel app."""
import json
from pathlib import Path


def change_spot(spots: list[dict], target: str, name: str) -> list[dict]:
    return [{**spot, "name": name} if spot["id"] == target else dict(spot) for spot in spots]


def save_spots(path: Path, spots: list[dict]) -> None:
    path.write_text(json.dumps(spots), encoding="utf-8")


def load_spots(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))
