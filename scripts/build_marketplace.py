#!/usr/bin/env python3
"""Build the CLI wheel *inside* the exported Skill. No publish, network or install.

The Python wheel contains Skill instructions but never itself. Only skills/ receives
runtime/; a skills.sh copy therefore works even without the rest of this repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/sync_skill_assets.py')], check=True)
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())["project"]["version"]
    with tempfile.TemporaryDirectory() as temp:
        staging = Path(temp) / 'source'
        staging.mkdir()
        for name in ('pyproject.toml', 'README.md', 'LICENSE'):
            shutil.copyfile(ROOT / name, staging / name)
        shutil.copytree(ROOT / 'src', staging / 'src', ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '*.egg-info'))
        out = Path(temp) / 'wheels'
        out.mkdir()
        env = dict(os.environ, SOURCE_DATE_EPOCH='1790121600')
        # Use locally installed build backend, without resolving any dependency.
        code = "import setuptools.build_meta as b; b.build_wheel(" + repr(str(out)) + ")"
        subprocess.run([sys.executable, '-c', code], cwd=staging, env=env, check=True,
                       stdout=subprocess.DEVNULL)
        wheels = list(out.glob('*.whl'))
        if len(wheels) != 1:
            raise SystemExit('Expected exactly one runtime wheel')
        data = wheels[0].read_bytes()
        target = ROOT / 'skills/jev-scrum-master/runtime'
        target.mkdir(parents=True, exist_ok=True)
        for old in target.glob('*.whl'):
            old.unlink()
        (target / wheels[0].name).write_bytes(data)
        metadata = {"schema_version": 1, "package": "jev-ai-scrum-master", "version": version,
                    "wheel": wheels[0].name, "sha256": hashlib.sha256(data).hexdigest(),
                    "requires_python": ">=3.12", "external_calls_default": False,
                    "publication_status": "local-artifact-not-published"}
        (target / 'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
        print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
