from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

from jev_sm.common import now
from jev_sm.core import Core
from jev_sm.models import Check, Settings
from jev_sm.workspace import Workspace


class SimulatedHuman:
    """Explicit test fixture; never installed as a CLI/MCP approval provider."""
    def confirm(self, kind, content_hash, details):
        return {"id": "test-approval-" + uuid.uuid4().hex, "kind": kind,
                "content_hash": content_hash, "source": "TEST_ONLY",
                "actor": "simulated-human", "at": now()}


def git(root: Path, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture

def core(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    (repo / "app.py").write_text("VALUE = 1\n")
    (repo / "check.py").write_text('''import json
import sys
from pathlib import Path
from app import VALUE
passed = VALUE == 1
Path(".jev-sm-output").mkdir(exist_ok=True)
Path(".jev-sm-output/unit.json").write_text(json.dumps({
    "schema_version": 1,
    "cases": [{"id": "app::save", "status": "passed" if passed else "failed"}]
}))
sys.exit(0 if passed else 1)
''')
    (repo / ".jev-sm").mkdir()
    settings = Settings(checks={"unit": Check(argv=[sys.executable, "check.py"], parser="json",
                                               report_path=".jev-sm-output/unit.json", timeout_seconds=5)},
                        protected_globs=["check.py", "tests/*", ".jev-sm/*"])
    (repo / ".jev-sm/config.yaml").write_text(yaml.safe_dump(settings.model_dump(mode="json")))
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "test fixture")
    return Core(Workspace(repo, tmp_path / "state"), authority=SimulatedHuman())


def plan(**changes):
    base = {"title": "Save value", "kind": "feature", "goal": "Persist the selected value",
            "in_scope": ["write and read"], "out_of_scope": ["UI styling"],
            "criteria": [{"id": "AC-1", "given": "A value exists", "when": "Save and reload",
                          "then": "The saved value is returned", "method": "test",
                          "check_ids": ["unit"], "case_ids": {"unit": ["app::save"]}}]}
    base.update(changes)
    return base


def rev(core, task):
    return core.store.get(task)["revision"]


def new_task(core, content=None):
    task = core.prepare("Implement persistent state", uuid.uuid4().hex)["task_id"]
    core.submit_plan(task, content or plan(), rev(core, task), uuid.uuid4().hex)
    return task


def start(core, content=None):
    task = new_task(core, content)
    core.approve_plan(task)
    core.start(task, rev(core, task), uuid.uuid4().hex)
    return task


def verify(core, task):
    return core.verify(task, rev(core, task), uuid.uuid4().hex)


def finish(core, task):
    verify(core, task)
    core.human_attest(task, "review")
    return core.complete(task, rev(core, task), uuid.uuid4().hex)


def settings_update(core, **changes):
    value = core.workspace.settings().model_dump(mode="json")
    value.update(changes)
    core.workspace.config_path.write_text(yaml.safe_dump(value))


def case_script(core, cases, exit_code=0, extra=""):
    report = json.dumps({"schema_version": 1, "cases": cases})
    (core.workspace.root / "check.py").write_text(
        "from pathlib import Path\nimport sys\n" + extra + "\n" +
        f"Path('.jev-sm-output/unit.json').write_text({report!r})\nsys.exit({exit_code})\n")
