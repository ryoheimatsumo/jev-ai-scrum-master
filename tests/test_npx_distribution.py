"""Offline package portability/command tests. These are NOT real npx/host tests."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skills_smoke', ROOT/'scripts/smoke_skills_install.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
AGENTS = smoke.agents()


@pytest.mark.parametrize('agent', [a['id'] for a in AGENTS])
def test_npx_command_targets_only_selected_agent(agent):
    result = smoke.install_command('npx', '1.7.0', ROOT, agent, 'copy')
    assert result[:4] == ['npx', '--yes', 'skills@1.7.0', 'add']
    assert result[result.index('--agent')+1] == agent
    assert '--all' not in result and '-g' not in result
    assert '--copy' in result


@pytest.mark.parametrize('version', ['latest', '1.0.0;touch bad', '@evil/skills', '../local', ''])
def test_npx_smoke_rejects_unpinned_or_unsafe_version(version):
    with pytest.raises(ValueError):
        smoke.install_command('npx', version, ROOT, 'cursor', 'copy')


def test_npx_preview_never_downloads(monkeypatch, capsys):
    monkeypatch.setattr(smoke, 'run_smoke', lambda *a: pytest.fail('not permitted in preview'))
    assert smoke.main(['--agent', 'windsurf']) == 0
    assert json.loads(capsys.readouterr().out)['network_performed'] is False
    assert smoke.main(['--write']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'blocked'


def test_npx_environment_never_inherits_secrets(monkeypatch, tmp_path):
    for k in ('GH_TOKEN', 'GITHUB_TOKEN', 'TYPESAFE_API_KEY', 'ANTHROPIC_API_KEY',
              'OPENAI_API_KEY', 'NPM_TOKEN', 'NODE_OPTIONS', 'PYTHONPATH'):
        monkeypatch.setenv(k, 'not-for-installer')
    env = smoke.isolated_environment(tmp_path)
    assert 'not-for-installer' not in env.values()
    assert env['DISABLE_TELEMETRY'] == '1'
    assert env['npm_config_ignore_scripts'] == 'true'


@pytest.mark.parametrize('entry', AGENTS, ids=[a['id'] for a in AGENTS])
def test_skill_folder_portability_at_documented_path(entry, tmp_path):
    # Copy a folder to representative upstream layout; does NOT mock/claim installer execution.
    project = tmp_path/'project with spaces'
    target = project/entry['project_path_hint']/'jev-scrum-master'
    shutil.copytree(ROOT/'skills/jev-scrum-master', target,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    before = {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    state = tmp_path/'runtime data'
    run = subprocess.run([sys.executable, str(target/'scripts/runtime.py'), 'setup'],
                         cwd=project, capture_output=True, text=True,
                         env={**os.environ, 'JEV_SM_RUNTIME_HOME': str(state)})
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['preview'] and result['status'] == 'not_installed'
    assert not state.exists()
    after = {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    assert before == after
    assert entry['host_e2e_tested'] is False


def test_source_skill_is_generic_and_self_contained():
    text = (ROOT/'skills/jev-scrum-master/SKILL.md').read_text()
    assert 'Local Agent Skills host' in text and 'other-agents.md' in text
    assert 'allowed-tools:' not in text
    assert (ROOT/'skills/jev-scrum-master/runtime/manifest.json').is_file()
