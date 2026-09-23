"""Publication helper tests. GitHub calls below are explicit local fakes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish_public.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def make_snapshot(root):
    root.mkdir()
    for name in publisher.REQUIRED:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture only\n")
    runtime = root / "skills/jev-scrum-master/runtime"
    wheel = runtime / "fixture.whl"
    wheel.write_bytes(b"TEST_FIXTURE_NOT_A_REAL_PACKAGE")
    (runtime / "manifest.json").write_text(json.dumps({
        "wheel": wheel.name, "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}))
    script = root / "scripts/publish_public.py"
    script.parent.mkdir()
    script.write_bytes((ROOT / "scripts/publish_public.py").read_bytes())
    doc = {"schema_version": 1, "repository": publisher.EXPECTED_REPOSITORY,
           "version": "0.1.0a3", "visibility": "public", "branch": "main", "files": []}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            doc["files"].append({"path": path.relative_to(root).as_posix(), "mode": "0644",
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (root / publisher.MANIFEST_NAME).write_text(json.dumps(doc))
    return root


@pytest.fixture
def snapshot(tmp_path):
    return make_snapshot(tmp_path / "source with spaces")


def test_preview_is_offline(snapshot, monkeypatch, capsys):
    monkeypatch.setattr(publisher, "ROOT", snapshot)
    def unexpected(*args, **kwargs):
        raise AssertionError("Preview must not call subprocess or network")
    monkeypatch.setattr(subprocess, "run", unexpected)
    assert publisher.main([]) == 0
    assert "OFFLINE PREVIEW ONLY" in capsys.readouterr().out


def test_modified_snapshot_is_refused(snapshot):
    (snapshot / "README.md").write_text("edited")
    with pytest.raises(publisher.PublishError, match="File changed"):
        publisher.load_snapshot(snapshot)


def test_added_secret_never_selected(snapshot):
    (snapshot / ".env").write_text("DUMMY_SECRET=TEST_ONLY")
    (snapshot / "local.sqlite3").write_bytes(b"TEST_ONLY")
    _, captured, _ = publisher.load_snapshot(snapshot)
    assert not {".env", "local.sqlite3"}.intersection(name for name, _, _ in captured)


def test_symlink_refused(snapshot):
    original = snapshot / "README.md"
    original.rename(snapshot / "other.md")
    original.symlink_to("other.md")
    with pytest.raises(publisher.PublishError, match="Symlinks"):
        publisher.load_snapshot(snapshot)


@pytest.mark.parametrize("name", ["../escape", "/absolute", ".git/config", ".env", "history.bundle", "local.sqlite3", "foo\\bar"])
def test_unsafe_manifest_paths_refused(snapshot, name):
    path = snapshot / publisher.MANIFEST_NAME
    doc = json.loads(path.read_text())
    doc["files"][0]["path"] = name
    path.write_text(json.dumps(doc))
    with pytest.raises((publisher.PublishError, OSError)):
        publisher.load_snapshot(snapshot)


def test_account_and_destination_cannot_be_retargeted(snapshot):
    path = snapshot / publisher.MANIFEST_NAME
    doc = json.loads(path.read_text()); doc["repository"] = "someone-else/repo"
    path.write_text(json.dumps(doc))
    with pytest.raises(publisher.PublishError, match="destination"):
        publisher.load_snapshot(snapshot)


@pytest.fixture
def fake_environment(tmp_path):
    """Fake gh plus REAL local Git, never an Internet connection."""
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
state = pathlib.Path(os.environ["PUBLICATION_TEST_STATE"])
state.mkdir(exist_ok=True)
with (state / "calls.jsonl").open("a") as f: f.write(json.dumps(args) + "\n")
mode = os.environ.get("PUBLICATION_TEST_MODE", "success")
repo = state / "repository.git"
if args[:2] == ["auth", "status"]:
    sys.exit(1 if mode == "no-auth" else 0)
if args[0] == "api":
    endpoint = args[-1]
    if endpoint == "user":
        print(json.dumps({"login": "other" if mode == "wrong-user" else "ryoheimatsumo", "id": 39510369})); sys.exit(0)
    if mode == "network":
        print("network unavailable", file=sys.stderr); sys.exit(1)
    if mode == "exists" or repo.exists():
        if endpoint.endswith("/git/ref/heads/main"):
            sha = subprocess.check_output(["git", "--git-dir", str(repo), "rev-parse", "main"], text=True).strip()
            print(json.dumps({"object": {"sha": sha}}))
        else:
            print(json.dumps({"private": mode == "verify-fail", "default_branch": "main"}))
        sys.exit(0)
    print("gh: Not Found (HTTP 404)", file=sys.stderr); sys.exit(1)
if args[:2] == ["repo", "create"]:
    assert "--public" in args
    subprocess.run(["git", "init", "--bare", str(repo)], check=True, stdout=subprocess.DEVNULL)
    source = args[args.index("--source") + 1]
    subprocess.run(["git", "-C", source, "remote", "add", "origin", str(repo)], check=True)
    sys.exit(0)
if args[:2] == ["repo", "edit"]: sys.exit(0)
raise SystemExit("Unexpected fake command: " + repr(args))
''')
    gh.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GH_", "GITHUB_", "GIT_"))}
    env["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
    env["PUBLICATION_TEST_STATE"] = str(tmp_path / "fake-state")
    env["TMPDIR"] = str(tmp_path)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = str(tmp_path / "nonexistent-git-config")
    return env


@pytest.mark.parametrize("mode", ["no-auth", "wrong-user", "exists", "network"])
def test_no_create_on_preflight_failure(snapshot, fake_environment, mode):
    env = dict(fake_environment, PUBLICATION_TEST_MODE=mode)
    result = subprocess.run([sys.executable, str(snapshot / "scripts/publish_public.py"), "--public"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 1
    state = Path(env["PUBLICATION_TEST_STATE"])
    calls = [json.loads(line) for line in (state / "calls.jsonl").read_text().splitlines()]
    assert not any(call[:2] == ["repo", "create"] for call in calls)
    assert not (snapshot / ".git").exists()


def test_real_git_local_publish_to_fake_github(snapshot, fake_environment):
    (snapshot / ".env").write_text("NOT_TO_BE_UPLOADED=FIXTURE")
    (snapshot / "history.bundle").write_bytes(b"NOT_TO_BE_UPLOADED")
    result = subprocess.run([sys.executable, str(snapshot / "scripts/publish_public.py"), "--public"],
                            env=fake_environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Published and verified" in result.stdout
    state = Path(fake_environment["PUBLICATION_TEST_STATE"])
    paths = subprocess.check_output(["git", "--git-dir", str(state / "repository.git"), "ls-tree", "-r", "--name-only", "main"], text=True).splitlines()
    assert publisher.REQUIRED.issubset(set(paths))
    assert "PUBLICATION_MANIFEST.json" in paths
    assert ".env" not in paths and "history.bundle" not in paths
    assert not (snapshot / ".git").exists()
    calls = [json.loads(line) for line in (state / "calls.jsonl").read_text().splitlines()]
    assert not any(call[:2] in (["pr", "create"], ["repo", "delete"]) for call in calls)
    # Rerunning never updates the existing remote.
    again = subprocess.run([sys.executable, str(snapshot / "scripts/publish_public.py"), "--public"],
                           env=fake_environment, capture_output=True, text=True)
    assert again.returncode == 1 and "already exists" in again.stderr


def test_no_success_message_on_remote_verification_failure(snapshot, fake_environment):
    env = dict(fake_environment, PUBLICATION_TEST_MODE="verify-fail")
    result = subprocess.run([sys.executable, str(snapshot / "scripts/publish_public.py"), "--public"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "Published and verified" not in result.stdout
    assert "preserved" in result.stderr
