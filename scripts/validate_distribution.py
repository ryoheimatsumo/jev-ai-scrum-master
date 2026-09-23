#!/usr/bin/env python3
"""Offline package consistency checks, not official marketplace approval or host testing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    project = tomllib.loads((root / 'pyproject.toml').read_text())["project"]
    version = project['version']
    plugin_version = version.replace('a', '-alpha.')
    portable = json.loads((root / 'plugin.json').read_text())
    claude = json.loads((root / '.claude-plugin/plugin.json').read_text())
    for manifest in (portable, claude):
        assert manifest['name'] == project['name']
        assert manifest['version'] == plugin_version
        assert not set(manifest) & {'hooks', 'mcpServers', 'allowed-tools'}
    assert portable['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
    assert set(portable['extensions']['com.openai']) == {'interface'}
    cm = json.loads((root / '.claude-plugin/marketplace.json').read_text())
    om = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    assert cm['name'] == om['name'] == 'jev-dev-tools'
    assert cm['plugins'][0]['name'] == om['plugins'][0]['name'] == project['name']
    assert cm['plugins'][0]['source'] == './'
    assert om['plugins'][0]['source'] == {'source': 'local', 'path': './'}
    skill = root / 'skills/jev-scrum-master'
    source = root / 'src/jev_sm/assets/skills/jev-scrum-master'
    for p in source.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            assert (skill / p.relative_to(source)).read_bytes() == p.read_bytes(), str(p)
    frontmatter = (skill / 'SKILL.md').read_text().split('---', 2)[1]
    assert 'name: jev-scrum-master' in frontmatter
    assert 'description:' in frontmatter
    assert 'allowed-tools' not in frontmatter
    meta = json.loads((skill / 'runtime/manifest.json').read_text())
    assert meta['version'] == version and meta['package'] == project['name']
    wheel = skill / 'runtime' / meta['wheel']
    assert wheel.name == f'jev_ai_scrum_master-{version}-py3-none-any.whl'
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == meta['sha256']
    with ZipFile(wheel) as z:
        assert not any(n.endswith('.whl') for n in z.namelist()), 'Recursive bundled wheel'
        expected = set()
        for p in (root / 'src/jev_sm').rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                name = p.relative_to(root / 'src').as_posix()
                expected.add(name)
                assert z.read(name) == p.read_bytes(), f'Stale runtime: {name}'
        actual = {n for n in z.namelist() if n.startswith('jev_sm/') and not n.endswith('/')}
        assert expected == actual, 'Wheel package content mismatch'
    return {'status': 'consistent', 'version': version, 'wheel_sha256': meta['sha256'],
            'checks': ['portable-manifest', 'claude-marketplace', 'codex-local-marketplace',
                       'skill-mirror', 'bundled-wheel-hash', 'wheel-source-parity', 'no-auto-hooks-or-mcp'],
            'official_marketplace_approval': False, 'host_runtime_test': False,
            'remote_publication': False}


if __name__ == '__main__':
    try:
        print(json.dumps(validate(), indent=2))
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print('Distribution inconsistent: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
