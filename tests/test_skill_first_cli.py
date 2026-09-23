"""CLI contracts shared with Skill and MCP; no live host/provider involved."""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from jev_sm.cli import main
from conftest import new_task, plan, start, verify


def invoke(core, capsys, *args):
    code = main(["--repo", str(core.workspace.root), "--state-dir", str(core.workspace.state_dir.parent), *args])
    captured = capsys.readouterr()
    return code, json.loads(captured.err if code == 4 else captured.out)


def test_cli_prepare_compact_and_explicit_schema(core, capsys):
    code, result = invoke(core, capsys, "prepare", "Keep the goal observable", "--key", "prepare-compact")
    assert code == 0 and "plan_schema" not in result
    assert result["schema_command"] == "jev-sm schema contract"
    code, same = invoke(core, capsys, "prepare", "Keep the goal observable", "--key", "prepare-compact", "--include-schema")
    assert same["task_id"] == result["task_id"] and "plan_schema" in same


def test_schema_does_not_need_repository(tmp_path, capsys):
    assert main(["--repo", str(tmp_path / "not-a-repo"), "schema", "context"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert "snippets" in result["properties"]
    assert not (tmp_path / "not-a-repo").exists()


def test_json_plan_can_arrive_on_stdin(core, capsys, monkeypatch):
    _, task = invoke(core, capsys, "prepare", "Implement storage")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(plan())))
    code, result = invoke(core, capsys, "submit-plan", task["task_id"], "-", "--revision", "0", "--key", "stdin-plan")
    assert code == 0 and result["state"] == "WAITING_USER"
    assert not core.gate(task["task_id"])["eligible"]


def test_prepare_file_and_exclusivity(core, capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("依頼を日本語で整理する"))
    assert invoke(core, capsys, "prepare", "--request-file", "-")[0] == 0
    code, result = invoke(core, capsys, "prepare", "inline", "--request-file", "-")
    assert code == 4 and result["error"]["code"] == "INVALID_INPUT"
    assert invoke(core, capsys, "prepare")[0] == 4


@pytest.mark.parametrize("payload", ["[]", "null", '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{'])
def test_invalid_json_has_machine_error_without_echo(core, capsys, monkeypatch, payload):
    task = new_task(core)
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    code, result = invoke(core, capsys, "submit-plan", task, "-", "--revision", "1")
    assert code == 4 and result["error"]["code"] == "INVALID_INPUT"


def test_schema_error_does_not_echo_rejected_secret(core, capsys, monkeypatch):
    task = new_task(core)
    value = plan()
    value["approved"] = "credential-should-not-echo"
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(value)))
    code, result = invoke(core, capsys, "submit-plan", task, "-", "--revision", "1")
    assert code == 4 and "credential-should-not-echo" not in json.dumps(result)


def test_stdin_byte_limit(core, capsys, monkeypatch):
    task = new_task(core)
    monkeypatch.setattr(sys, "stdin", io.StringIO("あ" * 400000))
    code, result = invoke(core, capsys, "select-context", task, "--input", "-")
    assert code == 4 and result["error"]["code"] == "INPUT_TOO_LARGE"


def test_status_compact_by_default_full_opt_in(core, capsys):
    task = start(core)
    verify(core, task)
    _, compact = invoke(core, capsys, "status", task)
    _, full = invoke(core, capsys, "status", task, "--full")
    assert "baseline_manifest" not in compact["task"]
    assert "baseline_manifest" in full["task"]
    assert compact["detail_command"] == "evidence"
    assert len(json.dumps(compact)) < len(json.dumps(full))
    job = compact["jobs"][0]["id"]
    assert invoke(core, capsys, "status", task, "--job-id", job)[1]["job"]["id"] == job
    assert invoke(core, capsys, "status", task, "--full", "--job-id", job)[0] == 4


def test_evidence_cli_hash_verification_and_pagination(core, capsys):
    task = start(core)
    verify(core, task)
    ev = core.store.get(task)["jobs"][-1]["evidence"][0]
    _, meta = invoke(core, capsys, "evidence", task, ev["id"])
    artifact = next(a for a in meta["artifacts"] if a.endswith(".json"))
    _, page = invoke(core, capsys, "evidence", task, ev["id"], "--artifact", artifact, "--max-chars", "8")
    assert len(page["text"]) == 8 and page["next_offset"] == 8
    code, result = invoke(core, capsys, "evidence", task, ev["id"], "--artifact", "../escape")
    assert code == 4 and result["error"]["code"] == "ARTIFACT_NOT_FOUND"


def test_cli_context_disabled_retains_everything(core, capsys, monkeypatch):
    task = new_task(core)
    request = {"query": "save", "snippets": [{"id": "a", "text": "Must save", "mandatory": True},
                                               {"id": "b", "text": "Other evidence"}], "max_chars": 1}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))
    _, result = invoke(core, capsys, "select-context", task, "--input", "-")
    assert len(result["selected"]) == 2 and not result["parked_ids"] and result["over_budget"]
    assert result["judgment"]["error"] == "JUDGMENT_DISABLED"


@pytest.mark.parametrize("mandatory", ["false", "true", 1, None])
def test_context_does_not_coerce_mandatory_flag(core, capsys, monkeypatch, mandatory):
    task = new_task(core)
    request = {"query": "save", "snippets": [{"id": "a", "text": "x", "mandatory": mandatory}]}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))
    assert invoke(core, capsys, "select-context", task, "--input", "-")[0] == 4


def test_cli_rule_proposal_is_never_auto_approved(core, capsys, monkeypatch):
    from test_core import proposal
    task = start(core)
    verify(core, task)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(proposal(core, task))))
    code, created = invoke(core, capsys, "propose-improvement", task, "-", "--revision",
                           str(core.store.get(task)["revision"]), "--key", "cli-rule")
    assert code == 0 and created["rule_status"] == "PROPOSED"
    _, values = invoke(core, capsys, "rule", "list", "--task-id", task)
    assert values["rules"][0]["id"] == created["rule_id"]
    _, candidates = invoke(core, capsys, "rule", "candidates", "--kind", "feature", "--path", "app.py")
    assert candidates["candidates"] == []


def test_tasks_are_paginated_without_raw_state(core, capsys):
    new_task(core)
    new_task(core)
    _, result = invoke(core, capsys, "tasks", "--limit", "1")
    assert result["next_offset"] == 1 and len(result["tasks"]) == 1
    assert "contract" not in result["tasks"][0]
    assert invoke(core, capsys, "tasks", "--limit", "0")[0] == 4


def test_cache_clear_requires_write_and_preserves_decisions(core, capsys):
    from jev_sm.judgment import DecisionEngine
    from test_judgment import FixtureBackend, Q
    task = new_task(core)
    DecisionEngine(core.workspace, core.store, FixtureBackend()).judge(task, "cli", {}, Q)
    assert invoke(core, capsys, "cache", "clear")[1]["preview"]
    assert invoke(core, capsys, "cache", "stats")[1]["entries"] == 1
    assert invoke(core, capsys, "cache", "clear", "--write")[1]["deleted_entries"] == 1
    assert len(core.store.decisions(task)) == 1


def test_no_mcp_or_typesafe_imports_on_primary_cli_path(core):
    source = str(Path(__file__).resolve().parents[1] / "src")
    guard = '''import importlib.abc,runpy,sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'mcp','typesafe_sdk'}:
            raise RuntimeError('Optional SDK imported on the primary path: '+fullname)
sys.meta_path.insert(0,BlockOptional())
sys.argv=['jev-sm',*sys.argv[1:]]
runpy.run_module('jev_sm',run_name='__main__')
'''
    command = [sys.executable, "-c", guard, "--repo", str(core.workspace.root), "--state-dir",
               str(core.workspace.state_dir.parent), "prepare", "A task without SDKs"]
    response = subprocess.run(command, capture_output=True, text=True, timeout=10,
                              env={**os.environ, "PYTHONPATH": source})
    assert response.returncode == 0, response.stderr
    assert json.loads(response.stdout)["state"] == "PLANNING"


def test_skills_installer_cli_preview_only(core, capsys):
    code, result = invoke(core, capsys, "skill", "install", "--host", "codex")
    assert code == 0 and result["preview"] and not Path(result["target"]).exists()


def test_full_cli_demo_with_explicit_simulated_approvals():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/demo_cli.py"), "--simulate-approvals"],
                            check=True, text=True, capture_output=True, timeout=45)
    data = json.loads(result.stdout)
    assert data["approvals"] == "SIMULATED_DEMO_ONLY"
    assert data["cli_process_count"] >= 20
    assert data["mcp_server_used"] is False and data["jev_api_used"] is False
    assert data["steps"]["completed"] == "DONE"
    assert "EVIDENCE_STALE" in data["steps"]["after_uncommitted_change"]
