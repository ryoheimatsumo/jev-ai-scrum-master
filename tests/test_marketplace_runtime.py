"""Marketplace packaging and bootstrap checks; no API keys or network access."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/jev-scrum-master/scripts/runtime.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    module = load(SCRIPT, 'runtime_test')
    module.SKILL_ROOT = tmp_path / 'installed skill'
    monkeypatch.setenv('JEV_SM_RUNTIME_HOME', str(tmp_path / 'runtime home'))
    return module


@pytest.fixture
def wheel(runtime, tmp_path):
    folder = tmp_path / 'bundle/runtime'
    folder.mkdir(parents=True)
    path = folder / 'jev_ai_scrum_master-0.1.0a3-py3-none-any.whl'
    path.write_bytes(b'test wheel fixture, not used as a real package')
    meta = {'schema_version': 1, 'package': 'jev-ai-scrum-master', 'version': '0.1.0a3',
            'wheel': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (folder / 'manifest.json').write_text(json.dumps(meta))
    return meta, path


def ready(runtime, meta, with_jev=False):
    target = runtime.target_for(meta, with_jev)
    target.mkdir(parents=True)
    python = runtime.python_at(target)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b'fixture')
    (target / 'jev-sm-runtime.json').write_text(json.dumps(runtime.receipt_for(meta, with_jev)))
    return target


def test_distribution_matches_current_source():
    validator = load(ROOT / 'scripts/validate_distribution.py', 'distribution_validator')
    assert validator.validate()['status'] == 'consistent'


def test_launcher_syntax_works_with_python39():
    # Grammar check only; real 3.9 execution still requires a platform matrix.
    ast.parse(SCRIPT.read_text(), feature_version=(3, 9))


def test_status_and_preview_are_read_only(runtime, wheel):
    meta, path = wheel
    assert runtime.inspect(meta, False)['status'] == 'not_installed'
    assert runtime.setup(meta, path, with_jev=True)['preview']
    assert not runtime.runtime_home().exists()


def test_explicit_consent_needed_before_network_or_write(runtime, wheel):
    meta, path = wheel
    with pytest.raises(runtime.SetupError, match='No automatic downloads'):
        runtime.setup(meta, path, write=True)
    assert not runtime.runtime_home().exists()


def test_valid_bundle(runtime, wheel):
    meta, path = wheel
    assert runtime.bundle_info(path.parent.parent) == (meta, path)


@pytest.mark.parametrize('bad', ['../evil.whl', '/tmp/evil.whl', 'wrong.whl', 'a\\b.whl'])
def test_bundle_filename_cannot_escape(runtime, wheel, bad):
    meta, path = wheel
    meta['wheel'] = bad
    (path.parent / 'manifest.json').write_text(json.dumps(meta))
    with pytest.raises(runtime.SetupError):
        runtime.bundle_info(path.parent.parent)


@pytest.mark.parametrize('field,value', [('schema_version', 2), ('package', 'wrong'),
    ('version', '../1'), ('version', 'latest'), ('sha256', '0'), ('sha256', 'f' * 64)])
def test_corrupt_or_altered_manifest_rejected(runtime, wheel, field, value):
    meta, path = wheel
    meta[field] = value
    (path.parent / 'manifest.json').write_text(json.dumps(meta))
    with pytest.raises(runtime.SetupError):
        runtime.bundle_info(path.parent.parent)


def test_changed_wheel_is_rejected(runtime, wheel):
    _, path = wheel
    path.write_bytes(b'changed')
    with pytest.raises(runtime.SetupError, match='hash mismatch'):
        runtime.bundle_info(path.parent.parent)


def test_wheel_symlink_is_rejected(runtime, wheel, tmp_path):
    _, path = wheel
    other = tmp_path / 'other'
    path.rename(other)
    path.symlink_to(other)
    with pytest.raises(runtime.SetupError):
        runtime.bundle_info(path.parent.parent)


def test_receipt_is_content_and_profile_specific(runtime, wheel):
    meta, path = wheel
    ready(runtime, meta)
    assert runtime.setup(meta, path, write=True)['installed'] is False
    assert runtime.inspect(meta, True)['status'] == 'not_installed'
    assert runtime.target_for(meta, False) != runtime.target_for(meta | {'sha256': 'f'*64}, False)


def test_incomplete_install_not_overwritten(runtime, wheel):
    meta, path = wheel
    target = runtime.target_for(meta, False)
    target.mkdir(parents=True)
    (target / 'keep').write_text('local file')
    with pytest.raises(runtime.SetupError, match='not overwritten'):
        runtime.setup(meta, path, write=True, allow_downloads=True)
    assert (target / 'keep').read_text() == 'local file'


def test_tampered_receipt_rejected(runtime, wheel):
    meta, _ = wheel
    target = ready(runtime, meta)
    (target / 'jev-sm-runtime.json').write_text(json.dumps(runtime.receipt_for(meta, True)))
    assert runtime.inspect(meta, False)['status'] == 'invalid_installation'


def test_environment_does_not_leak_credentials(runtime, monkeypatch):
    for key in ('TYPESAFE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GH_TOKEN',
                'PYTHONPATH', 'PIP_INDEX_URL', 'UV_INDEX_URL'):
        monkeypatch.setenv(key, 'must-not-leak')
    assert 'must-not-leak' not in runtime.install_environment().values()


def test_missing_python_fails_before_writes(runtime, wheel, monkeypatch):
    monkeypatch.setattr(runtime, 'find_python', lambda: None)
    monkeypatch.setattr(runtime.shutil, 'which', lambda name: None)
    with pytest.raises(runtime.SetupError, match='Python 3.12'):
        runtime.setup(*wheel, write=True, allow_downloads=True)
    assert not runtime.runtime_home().exists()


def test_runtime_cannot_be_inside_git_project(runtime, wheel, tmp_path):
    project = tmp_path / 'repo'
    project.mkdir()
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    with pytest.raises(runtime.SetupError, match='outside Git'):
        runtime.setup(*wheel, write=True, allow_downloads=True, home=project / '.runtime')
    assert not (project / '.runtime').exists()


def test_relative_runtime_home_rejected(runtime, monkeypatch):
    monkeypatch.setenv('JEV_SM_RUNTIME_HOME', 'relative')
    with pytest.raises(runtime.SetupError, match='absolute'):
        runtime.runtime_home()


def test_symlinked_destination_rejected(runtime, wheel, tmp_path):
    other = tmp_path / 'other'
    other.mkdir()
    runtime.runtime_home().symlink_to(other, target_is_directory=True)
    with pytest.raises(runtime.SetupError, match='symbolic link'):
        runtime.setup(*wheel, write=True, allow_downloads=True)
    assert not list(other.iterdir())


def test_concurrent_install_lock(runtime, wheel):
    meta, _ = wheel
    home = runtime.runtime_home()
    home.mkdir(parents=True)
    (home / ('.' + runtime.target_for(meta, False).name + '.lock')).write_text('busy')
    with pytest.raises(runtime.SetupError, match='setup lock'):
        runtime.setup(*wheel, write=True, allow_downloads=True)


def test_offline_setup_without_wheelhouse_fails(runtime, wheel, tmp_path):
    with pytest.raises(runtime.SetupError, match='does not exist'):
        runtime.setup(*wheel, write=True, wheelhouse=tmp_path / 'missing')


def test_online_and_offline_options_cannot_mix(runtime, wheel, tmp_path):
    with pytest.raises(runtime.SetupError, match='either'):
        runtime.setup(*wheel, write=True, allow_downloads=True, wheelhouse=tmp_path)


def test_failed_install_cleans_its_staging_and_lock(runtime, wheel, monkeypatch):
    def fail(*args):
        raise runtime.SetupError('SETUP_FAILED', 'failure fixture')
    monkeypatch.setattr(runtime, 'run_install', fail)
    with pytest.raises(runtime.SetupError, match='failure fixture'):
        runtime.setup(*wheel, write=True, allow_downloads=True)
    assert not list(runtime.runtime_home().iterdir())


def test_setup_offline_uses_only_local_wheels(runtime, wheel, monkeypatch, tmp_path):
    calls = []
    def fake(argv, cwd, env):
        calls.append(argv)
        if 'venv' in argv:
            target = Path(argv[-1])
            runtime.python_at(target).parent.mkdir(parents=True)
            runtime.python_at(target).write_bytes(b'fake python for setup unit test')
    monkeypatch.setattr(runtime, 'run_install', fake)
    result = runtime.setup(*wheel, write=True, wheelhouse=tmp_path)
    assert result['installed'] and not result['network_performed']
    pip = next(c for c in calls if 'install' in c)
    assert '--no-index' in pip and '--find-links' in pip and '--only-binary=:all:' in pip
    assert '--index-url' not in pip


def test_launch_without_setup_never_installs(runtime, wheel, monkeypatch, capsys):
    monkeypatch.setattr(runtime, 'bundle_info', lambda: wheel)
    assert runtime.main(['exec', '--', '--help']) == 2
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'SETUP_REQUIRED'
    assert not runtime.runtime_home().exists()


def test_launch_forwards_arguments_and_exit_code_without_shell(runtime, wheel, monkeypatch):
    ready(runtime, wheel[0])
    monkeypatch.setattr(runtime, 'bundle_info', lambda: wheel)
    calls = []
    def call(argv):
        calls.append(argv)
        return 7
    monkeypatch.setattr(runtime.subprocess, 'call', call)
    assert runtime.main(['exec', '--', '--repo', '/repo with spaces', 'prepare', 'a; $(touch bad)']) == 7
    assert calls[0][1:4] == ['-I', '-m', 'jev_sm']
    assert calls[0][-1] == 'a; $(touch bad)'


def test_copy_only_skill_is_self_contained(tmp_path):
    copy = tmp_path / 'cache with spaces' / 'jev-scrum-master'
    shutil.copytree(ROOT / 'skills/jev-scrum-master', copy)
    home = tmp_path / 'state'
    env = {**os.environ, 'JEV_SM_RUNTIME_HOME': str(home)}
    proc = subprocess.run([sys.executable, str(copy/'scripts/runtime.py'), 'status'],
                          capture_output=True, text=True, env=env, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['status'] == 'not_installed'
    assert not home.exists()


def test_symlinked_skill_entry_resolves_bundle(tmp_path):
    link = tmp_path / 'jev-scrum-master'
    link.symlink_to(ROOT / 'skills/jev-scrum-master', target_is_directory=True)
    proc = subprocess.run([sys.executable, str(link/'scripts/runtime.py'), 'status'],
        capture_output=True, text=True, env={**os.environ, 'JEV_SM_RUNTIME_HOME': str(tmp_path/'state')})
    assert proc.returncode == 0
    assert json.loads(proc.stdout)['status'] == 'not_installed'
