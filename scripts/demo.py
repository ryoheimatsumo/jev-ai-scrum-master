#!/usr/bin/env python3
"""Run a real local test loop in a fresh disposable Git repo, never a user's repo.

--simulate-approvals is deliberately explicit. It demonstrates transitions, not
human provenance, independent AI review, Jev accuracy, or token savings.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import yaml
from jev_sm.common import now
from jev_sm.core import Core
from jev_sm.models import Check, Settings
from jev_sm.report import render
from jev_sm.workspace import Workspace


class DemoApproval:
    def confirm(self, kind, content_hash, details):
        return {"id": "demo-" + uuid.uuid4().hex, "kind": kind,
                "content_hash": content_hash, "source": "SIMULATED_DEMO_ONLY",
                "actor": "demo-fixture-not-a-human", "at": now()}


def run(simulated: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="jev-sm-demo-") as directory:
        base = Path(directory)
        repo = base / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
        for source in (ROOT / "examples/demo").glob("*.py"):
            shutil.copy2(source, repo / source.name)
        original = (repo / "app.py").read_text()
        (repo / "app.py").write_text(original.replace(
            'path.write_text(json.dumps(spots), encoding="utf-8")',
            'return None  # intentional demo bug: never persists'))
        (repo / ".jev-sm").mkdir()
        cfg = Settings(checks={"unit": Check(argv=[sys.executable, "check.py"], parser="json",
            report_path=".jev-sm-output/checks.json", timeout_seconds=10)})
        (repo / ".jev-sm/config.yaml").write_text(yaml.safe_dump(cfg.model_dump(mode="json")))
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Demo fixture", "-c",
                        "user.email=demo@example.invalid", "commit", "-m", "Intentional demo baseline"],
                       check=True, capture_output=True)
        core = Core(Workspace(repo, base / "state"), authority=DemoApproval() if simulated else None)
        task = core.prepare("Replace a spot and persist it", "prepare-demo")["task_id"]
        def revision():
            return core.store.get(task)["revision"]
        core.submit_plan(task, json.loads((ROOT / "examples/plan.json").read_text()), revision(), "plan")
        assert not core.gate(task)["eligible"]
        core.approve_plan(task)
        core.start(task, revision(), "start")
        core.verify(task, revision(), "verify-broken")
        broken = core.gate(task)
        assert broken["criteria"]["AC-2"] == "FAIL"
        (repo / "app.py").write_text(original)
        core.verify(task, revision(), "verify-fixed")
        needs_review = core.gate(task)
        assert "INDEPENDENT_REVIEW_REQUIRED" in needs_review["issues"]
        core.human_attest(task, "review")
        done = core.complete(task, revision(), "complete")
        assert done["eligible"] and done["state"] == "DONE"
        complete_report = render(core, task)
        (repo / "app.py").write_text(original + "\n# subsequent uncommitted change\n")
        stale = core.gate(task)
        assert stale["exit_code"] == 3
        return {"approvals": "SIMULATED_DEMO_ONLY" if simulated else "interactive_tty",
                "jev_api_used": False, "host_llm_used": False,
                "steps": {"broken_persistence": broken["criteria"],
                          "fixed_but_review_required": needs_review["issues"],
                          "completed": done["state"], "after_uncommitted_change": stale["issues"]},
                "report": complete_report,
                "note": "Actual subprocess tests in disposable snapshots. Not an AI quality benchmark."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate-approvals", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    data = run(args.simulate_approvals)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    if args.result:
        args.result.write_text(content + "\n")
    print(content)
