#!/usr/bin/env python3
"""Demonstrate the Skill-first flow through real, separate CLI processes in a temp repo.

Only human confirmations use the local authority (or explicit simulated test receipts).
MCP, host LLMs and external Jev are not used. This is not a performance benchmark.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml
from jev_sm import __version__
from jev_sm.core import Core
from jev_sm.models import Check, Settings
from jev_sm.workspace import Workspace
from demo import DemoApproval


def run(simulated: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="jev-sm-cli-demo-", dir="/private/tmp") as directory:
        base = Path(directory)
        repo = base / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
        for source in (ROOT / "examples/demo").glob("*.py"):
            shutil.copy2(source, repo / source.name)
        original = (repo / "app.py").read_text()
        (repo / "app.py").write_text(original.replace(
            'path.write_text(json.dumps(spots), encoding="utf-8")',
            'return None  # intentional persistence defect'))
        (repo / ".jev-sm").mkdir()
        cfg = Settings(checks={"unit": Check(argv=[sys.executable, "check.py"], parser="json",
            report_path=".jev-sm-output/checks.json", timeout_seconds=10)})
        (repo / ".jev-sm/config.yaml").write_text(yaml.safe_dump(cfg.model_dump(mode="json")))
        calls = []

        def cli(*args, data=None, expected=0):
            response = subprocess.run([sys.executable, "-m", "jev_sm", "--repo", str(repo),
                "--state-dir", str(base / "state"), *args], input=data, text=True,
                capture_output=True, timeout=30,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
            if response.returncode != expected:
                raise RuntimeError(f"CLI {args[0]} returned {response.returncode}: {response.stderr}")
            result = json.loads(response.stdout)
            calls.append({"command": args[0], "exit_code": response.returncode})
            return result

        # Use the temporary fixture repository so the demo never depends on a user's
        # home-directory Skill links or managed host installation.
        preview = cli("skill", "install", "--host", "codex", "--scope", "project")
        assert preview["preview"]
        installed = cli("skill", "install", "--host", "codex", "--scope", "project", "--write")
        assert installed["written"]
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Demo fixture", "-c",
            "user.email=demo@example.invalid", "commit", "-m", "Temporary CLI demo fixture"],
            check=True, capture_output=True)
        core = Core(Workspace(repo, base / "state"), authority=DemoApproval() if simulated else None)
        assert cli("doctor")["mcp_required"] is False
        assert "criteria" in cli("schema", "contract")["properties"]
        task = cli("prepare", "Replace one spot and persist it", "--key", "demo-create")["task_id"]
        def revision():
            return str(cli("status", task)["task"]["revision"])
        cli("submit-plan", task, "-", "--revision", revision(), "--key", "demo-plan",
            data=(ROOT / "examples/plan.json").read_text())
        core.approve_plan(task)  # Real TTY unless --simulate-approvals was explicitly requested.
        cli("start", task, "--revision", revision(), "--key", "demo-start")
        context = cli("select-context", task, "--input", "-", data=json.dumps({
            "query": "Verify storage", "snippets": [{"id": "ac", "text": "Persist the result", "mandatory": True}]}))
        assert context["judgment"]["error"] == "JUDGMENT_DISABLED" and len(context["selected"]) == 1
        cli("advise", "readiness", task)
        cli("verify", task, "--revision", revision(), "--key", "demo-broken")
        broken = cli("gate", task, expected=2)
        assert broken["criteria"]["AC-2"] == "FAIL"
        (repo / "app.py").write_text(original)
        cli("verify", task, "--revision", revision(), "--key", "demo-fixed")
        needs_review = cli("gate", task, expected=2)
        assert "INDEPENDENT_REVIEW_REQUIRED" in needs_review["issues"]
        status = cli("status", task)
        ev = status["jobs"][-1]["evidence"][0]["id"]
        metadata = cli("evidence", task, ev)
        artifact = next(a for a in metadata["artifacts"] if a.endswith(".json"))
        page = cli("evidence", task, ev, "--artifact", artifact, "--max-chars", "20")
        assert page["next_offset"] == 20
        core.human_attest(task, "review")
        assert cli("gate", task)["eligible"]
        done = cli("complete", task, "--revision", revision(), "--key", "demo-complete")
        assert done["state"] == "DONE" and done["eligible"]
        proposal = {"title": "Check independent reload", "hypothesis": "Reload can expose a missing write",
            "proposed_action": "Suggest save plus independent reload in the verification plan",
            "task_kinds": ["feature"], "path_globs": ["app.py"], "evidence_ids": [ev],
            "positive_example": "A save method that never writes", "negative_example": "A documentation typo",
            "action_kind": "verification_candidate"}
        result = cli("propose-improvement", task, "-", "--revision", revision(),
                     "--key", "demo-retro", data=json.dumps(proposal))
        assert result["rule_status"] == "PROPOSED"
        assert len(cli("rule", "list", "--task-id", task)["rules"]) == 1
        assert cli("rule", "candidates", "--kind", "feature", "--path", "app.py")["candidates"] == []
        (repo / "app.py").write_text(original + "\n# next uncommitted change\n")
        stale = cli("gate", task, expected=3)
        return {"interface": "skill+cli", "version": __version__,
                "approvals": "SIMULATED_DEMO_ONLY" if simulated else "interactive_tty",
                "cli_process_count": len(calls), "cli_calls": calls,
                "jev_api_used": False, "mcp_server_used": False, "host_llm_used": False,
                "steps": {"skill_installed_without_mcp": True,
                          "broken_persistence": broken["criteria"],
                          "fixed_but_review_required": needs_review["issues"],
                          "completed": done["state"], "retrospective": result["rule_status"],
                          "after_uncommitted_change": stale["issues"]},
                "note": "Real CLI/runner subprocesses; approvals explicitly simulated only when opted in. Not a host/Jev quality benchmark."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate-approvals", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    data = run(args.simulate_approvals)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.result:
        args.result.write_text(text + "\n", encoding="utf-8")
    print(text)
