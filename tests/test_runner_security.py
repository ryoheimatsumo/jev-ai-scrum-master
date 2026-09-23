import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from jev_sm.common import DomainError, inside, redact
from jev_sm.models import Check
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


def test_symlink_directory_escape_rejected(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "out"
    root.mkdir(); outside.mkdir()
    (root / "alias").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DomainError):
        inside(root, "alias/report.json")


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
