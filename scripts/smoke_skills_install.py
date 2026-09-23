#!/usr/bin/env python3
"""Opt-in real npx distribution smoke test in a throw-away project and HOME.

Default is a read-only preview. This script tests installer placement and bundle integrity,
not live agents, Jev, or official marketplace acceptance. Never mocks the skills installer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = 'jev-scrum-master'


def agents():
    return json.loads((ROOT / 'distribution/agents.json').read_text())['agents']


def install_command(npx: str, version: str, source: Path, agent: str, mode: str):
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise ValueError('Use an explicit reviewed skills package version, not latest or shell syntax')
    if agent not in {a['id'] for a in agents()} or mode not in {'copy', 'symlink'}:
        raise ValueError('Unsupported agent or installation mode')
    result = [npx, '--yes', f'skills@{version}', 'add', str(source.resolve()),
              '--skill', SKILL, '--agent', agent, '--yes']
    if mode == 'copy':
        result += ['--copy']
    return result


def isolated_environment(home: Path):
    # Keep credentials out of the third-party installer. It needs no GitHub auth for local source.
    keep = {'PATH', 'SYSTEMROOT', 'WINDIR', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}
    env = {k: v for k, v in os.environ.items() if k in keep}
    env.update({'HOME': str(home), 'USERPROFILE': str(home), 'XDG_CONFIG_HOME': str(home/'config'),
                'XDG_DATA_HOME': str(home/'data'), 'XDG_CACHE_HOME': str(home/'cache'),
                'CODEX_HOME': str(home/'codex'), 'CLAUDE_CONFIG_DIR': str(home/'claude'),
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1', 'CI': '1',
                'npm_config_cache': str(home/'npm-cache'), 'npm_config_userconfig': os.devnull,
                'npm_config_globalconfig': str(home/'empty-npmrc'),
                'npm_config_registry': 'https://registry.npmjs.org',
                'npm_config_ignore_scripts': 'true', 'npm_config_fetch_retries': '0',
                'npm_config_fetch_timeout': '10000',
                'JEV_SM_RUNTIME_HOME': str(home/'runtimes')})
    return env


def run_smoke(agent: str, version: str, mode: str):
    npx = shutil.which('npx')
    if not npx:
        return {'status': 'blocked', 'reason': 'npx is not installed', 'agent': agent}
    with tempfile.TemporaryDirectory(prefix='jev-skills-smoke-') as temp:
        work = Path(temp)
        home, project, source = work/'home', work/'project with spaces', work/'source'
        home.mkdir()
        project.mkdir()
        (source/'skills').mkdir(parents=True)
        shutil.copytree(ROOT/'skills'/SKILL, source/'skills'/SKILL,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        # Mark as the selected host project, avoiding implicit registration of unselected hosts.
        hint = next(a['project_path_hint'] for a in agents() if a['id'] == agent)
        (project/Path(hint).parts[0]).mkdir(exist_ok=True)
        (project/'AGENTS.md').write_text('preserve this project instruction\n')
        (project/'CLAUDE.md').write_text('preserve this host instruction\n')
        env = isolated_environment(home)
        command = install_command(npx, version, source, agent, mode)
        try:
            run = subprocess.run(command, cwd=project, env=env, capture_output=True,
                                 text=True, timeout=90)
        except subprocess.TimeoutExpired:
            return {'status': 'blocked', 'reason': 'npx timeout', 'agent': agent}
        if run.returncode:
            # Isolated environment and local public fixtures only. Bound log output.
            return {'status': 'failed', 'agent': agent, 'exit_code': run.returncode,
                    'stderr_tail': run.stderr[-3000:], 'stdout_tail': run.stdout[-3000:]}
        found = [p.parent for p in project.rglob('SKILL.md') if p.parent.name == SKILL]
        if not found:
            return {'status': 'failed', 'agent': agent, 'reason': 'No installed Skill found'}
        expected = json.loads((source/'skills'/SKILL/'runtime/manifest.json').read_text())
        for entry in found:
            metadata = json.loads((entry/'runtime/manifest.json').read_text())
            wheel = entry/'runtime'/metadata['wheel']
            assert metadata == expected
            assert hashlib.sha256(wheel.read_bytes()).hexdigest() == metadata['sha256']
            probe = subprocess.run([sys.executable, str(entry/'scripts/runtime.py'), 'status'],
                                   cwd=project, env=env, capture_output=True, text=True, timeout=15)
            assert probe.returncode == 0, probe.stderr
            assert json.loads(probe.stdout)['status'] == 'not_installed'
        assert (project/'AGENTS.md').read_text() == 'preserve this project instruction\n'
        assert (project/'CLAUDE.md').read_text() == 'preserve this host instruction\n'
        assert not (project/'.jev-sm').exists(), 'Skill installation must not initialize a task project'
        assert not (home/'runtimes').exists(), 'Skill installation must not activate Python runtime'
        return {'status': 'passed', 'agent': agent, 'mode': mode, 'skills_version': version,
                'installed_paths': [str(p.relative_to(project)) for p in found],
                'bundle_sha256': expected['sha256'], 'real_npx_executed': True,
                'host_e2e': False, 'jev_api_called': False, 'python_runtime_installed': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agent', choices=[a['id'] for a in agents()], default='cursor')
    p.add_argument('--skills-version', default='1.7.0', help='Explicit version; verify publication first')
    p.add_argument('--mode', choices=['copy', 'symlink'], default='copy')
    p.add_argument('--write', action='store_true')
    p.add_argument('--allow-downloads', action='store_true')
    args = p.parse_args(argv)
    command = install_command('npx', args.skills_version, ROOT, args.agent, args.mode)
    if not args.write:
        print(json.dumps({'status': 'preview', 'command': command,
                          'network_performed': False, 'requires_write_and_download_consent': True}, indent=2))
        return 0
    if not args.allow_downloads:
        print(json.dumps({'status': 'blocked', 'reason': 'Explicit --allow-downloads is required'}))
        return 2
    try:
        result = run_smoke(args.agent, args.skills_version, args.mode)
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        result = {'status': 'failed', 'reason': str(exc), 'agent': args.agent}
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
