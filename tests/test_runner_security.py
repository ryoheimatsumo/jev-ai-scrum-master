import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from jev_sm.common import DomainError, inside, redact
from jev_sm.models import Check, Settings
from jev_sm.runner import bounded_process, clean_environment, parse_report
from jev_sm.workspace import Workspace

from conftest import case_script, start, verify


@pytest.mark.parametrize("value", ["../secret", "/etc/passwd", "a/../../secret", "a\\..\\b"])
def test_path_traversal_rejected(tmp_path, value):
    with pytest.raises((ValueError, DomainError)):
        inside(tmp_path, value)


def test_symlink_input_rejected(core, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("do not copy")
    (core.workspace.root / "link").symlink_to(outside)
    with pytest.raises(DomainError):
        core.workspace.manifest()


def test_doctor_inventory_reports_multiple_bad_inputs_and_deleted_files(core, tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("secret")
    (core.workspace.root / "bad-one").symlink_to(outside)
    (core.workspace.root / "bad-two").symlink_to(outside)
    (core.workspace.root / "gone.py").write_text("deleted")
    subprocess.run(["git", "-C", str(core.workspace.root), "add", "bad-one", "bad-two", "gone.py"], check=True)
    (core.workspace.root / "gone.py").unlink()
    report = core.workspace.input_diagnostics()
    assert not report["compatible"]
    assert len(report["errors"]) >= 2
    assert not any("gone.py" in error["message"] for error in report["errors"])


def test_symlink_directory_escape_rejected(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "out"
    root.mkdir(); outside.mkdir()
    (root / "alias").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DomainError):
        inside(root, "alias/report.json")


def test_gitlink_manifest_records_uninitialized_submodule(tmp_path):
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    source.mkdir(); repo.mkdir()
    subprocess.run(["git", "-C", str(source), "init", "-b", "main"], check=True, capture_output=True)
    (source / "module.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "module"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True)
    (repo / "app.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "root"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "protocol.file.allow=always", "submodule",
                    "add", str(source), "tabic-context"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-am", "submodule"], check=True,
                   capture_output=True)
    (repo / ".jev-sm").mkdir()
    (repo / ".jev-sm" / "config.yaml").write_text(yaml.safe_dump(Settings().model_dump(mode="json")))
    subprocess.run(["git", "-C", str(repo), "submodule", "deinit", "-f", "--", "tabic-context"],
                   check=True, capture_output=True)
    workspace = Workspace(repo, tmp_path / "state")
    manifest = workspace.manifest()
    assert manifest["tabic-context"]["kind"] == "submodule"
    assert manifest["tabic-context"]["initialized"] is False
    assert manifest["tabic-context"]["mode"] == 160000


def test_initialized_submodule_files_are_hashed_and_snapshot_safe(tmp_path):
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    source.mkdir(); repo.mkdir()
    for root in (source, repo):
        subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
    (source / "module.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "module"], check=True,
                   capture_output=True)
    (repo / "app.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "root"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "protocol.file.allow=always", "submodule",
                    "add", str(source), "tabic-context"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-am", "submodule"], check=True,
                   capture_output=True)
    (repo / ".jev-sm").mkdir()
    (repo / ".jev-sm" / "config.yaml").write_text(yaml.safe_dump(Settings().model_dump(mode="json")))
    workspace = Workspace(repo, tmp_path / "state")
    manifest = workspace.manifest()
    assert manifest["tabic-context"]["initialized"] is True
    assert manifest["tabic-context/module.py"]["sha256"]
    snap = workspace.snapshot("run")
    assert workspace.snapshot_unchanged(snap)
    (Path(snap["path"]) / "tabic-context" / "module.py").write_text("tampered\n")
    assert not workspace.snapshot_unchanged(snap)


def test_doctor_lists_multiple_child_errors_and_nested_submodules(tmp_path):
    nested_source = tmp_path / "nested-source"
    parent_source = tmp_path / "parent-source"
    repo = tmp_path / "repo"
    for root in (nested_source, parent_source, repo):
        root.mkdir()
        subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True,
                       capture_output=True)

    (nested_source / "nested.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(nested_source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(nested_source), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "nested"],
                   check=True, capture_output=True)

    # Symlinks are tracked by Git but rejected by the managed input boundary.
    (parent_source / "bad-one").symlink_to("missing-one")
    (parent_source / "bad-two").symlink_to("missing-two")
    subprocess.run(["git", "-C", str(parent_source), "-c", "protocol.file.allow=always",
                    "submodule", "add", str(nested_source), "nested"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(parent_source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(parent_source), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "parent"],
                   check=True, capture_output=True)

    (repo / "app.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-m", "root"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "protocol.file.allow=always",
                    "submodule", "add", str(parent_source), "parent"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-am", "submodules"],
                   check=True, capture_output=True)
    (repo / ".jev-sm").mkdir()
    (repo / ".jev-sm" / "config.yaml").write_text(yaml.safe_dump(Settings().model_dump(mode="json")))

    report = Workspace(repo, tmp_path / "state").input_diagnostics()
    assert not report["compatible"]
    assert sum("bad-one" in error["message"] or "bad-two" in error["message"]
               for error in report["errors"]) == 2
    listed = {module["path"] for module in report["submodules"]}
    assert {"parent", "parent/nested"} <= listed


def test_state_directory_cannot_be_inside_repository(core):
    with pytest.raises(DomainError):
        Workspace(core.workspace.root, core.workspace.root / "state")


def test_ignored_source_is_included(core):
    (core.workspace.root / ".gitignore").write_text("hidden.py\n")
    (core.workspace.root / "hidden.py").write_text("value = 42\n")
    assert "hidden.py" in core.workspace.manifest()


def test_secret_file_excluded(core):
    (core.workspace.root / ".env").write_text("KEY=private")
    (core.workspace.root / "private.pem").write_text("private")
    assert ".env" not in core.workspace.manifest()
    assert "private.pem" not in core.workspace.manifest()


def test_child_environment_does_not_inherit_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "top-secret-key")
    monkeypatch.setenv("OPENAI_API_KEY", "top-secret-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "top-secret-key")
    monkeypatch.setenv("PYTHONPATH", "/unsafe")
    env = clean_environment(tmp_path, tmp_path / "home")
    assert not ({"TYPESAFE_API_KEY", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "PYTHONPATH"} & set(env))
    assert env["HOME"] != str(Path.home())


def test_actual_child_cannot_read_key(core, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "should-not-be-inherited")
    case_script(core, [{"id": "app::save", "status": "passed"}],
                extra="import os\nassert 'TYPESAFE_API_KEY' not in os.environ")
    task = start(core)
    verify(core, task)
    assert core.store.get(task)["jobs"][-1]["evidence"][0]["outcome"] == "PASS"


def test_timeout_terminates_process(tmp_path):
    result = bounded_process([sys.executable, "-c", "import time; time.sleep(20)"], tmp_path,
                             clean_environment(tmp_path, tmp_path / "home"), 0.15, 4096)
    assert result["timeout"]
    assert result["seconds"] < 5


def test_output_limit_terminates_process(tmp_path):
    result = bounded_process([sys.executable, "-c", "print('x' * 1000000)"], tmp_path,
                             clean_environment(tmp_path, tmp_path / "home"), 5, 1024)
    assert result["output_limited"]
    assert len(result["stdout"]) <= 1024


def test_unknown_binary_is_blocked(tmp_path):
    result = bounded_process(["/not-a-real-binary"], tmp_path, {}, 1, 1024)
    assert result["exit_code"] is None and result["error"]


def test_behavior_cannot_use_exit_only():
    with pytest.raises(ValidationError):
        Check(argv=["true"], kind="test", parser="exit")


def test_report_must_be_in_reserved_output():
    with pytest.raises(ValidationError):
        Check(argv=["true"], report_path="tests/old.xml")


def test_junit_cases_not_summary_counts(tmp_path):
    p = tmp_path / "result.xml"
    p.write_text('<testsuite tests="999"><testcase classname="app" name="save"/></testsuite>')
    report = parse_report(p, "junit")
    assert len(report.cases) == 1
    assert report.cases[0].id == "app::save"


def test_junit_skip_and_failure(tmp_path):
    p = tmp_path / "result.xml"
    p.write_text('<testsuites><testsuite><testcase name="one"><skipped/></testcase>'
                 '<testcase name="two"><failure/></testcase></testsuite></testsuites>')
    assert [c.status for c in parse_report(p, "junit").cases] == ["skipped", "failed"]


def test_duplicate_case_ids_rejected(tmp_path):
    p = tmp_path / "result.xml"
    p.write_text('<testsuite><testcase name="same"/><testcase name="same"/></testsuite>')
    with pytest.raises(ValidationError):
        parse_report(p, "junit")


def test_xml_entities_rejected(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_text('<!DOCTYPE testsuite [<!ENTITY x "danger">]><testsuite>&x;</testsuite>')
    with pytest.raises(Exception):
        parse_report(p, "junit")


def test_suite_error_not_ignored(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_text('<testsuite><error>setup failed</error><testcase name="ok"/></testsuite>')
    with pytest.raises(ValueError):
        parse_report(p, "junit")


def test_redaction_masks_known_env_and_assignment(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "uniquesecretvalue")
    value = redact("uniquesecretvalue password=hiddenstuff api_key: wowsecret")
    assert "uniquesecretvalue" not in value and "hiddenstuff" not in value and "wowsecret" not in value
