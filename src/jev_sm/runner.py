"""Managed, credential-minimized check execution. A copy is NOT a security sandbox."""
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
import threading
import uuid
from pathlib import Path

from defusedxml import ElementTree

from .common import DomainError, digest, file_hash, inside, now, redact
from .models import Case, Check, TestReport
from .workspace import Workspace


def parse_report(path: Path, parser: str) -> TestReport:
    if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Missing or oversized report")
    if parser == "json":
        return TestReport.model_validate_json(path.read_text(encoding="utf-8"))
    root = ElementTree.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Expected a JUnit test suite")
    cases = []
    for case in root.iter("testcase"):
        classname = case.get("classname", "")
        name = case.get("name", "")
        if not name:
            raise ValueError("JUnit case has no name")
        identity = f"{classname}::{name}" if classname else name
        status = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        cases.append(Case(id=identity, status=status))
    # Root/suite setup errors with no failing test must not disappear in the case count.
    if list(root.iter("error")) and not any(c.status == "failed" for c in cases):
        raise ValueError("Suite-level error without test evidence")
    return TestReport(cases=cases)


def clean_environment(output_dir: Path, home: Path) -> dict[str, str]:
    # No wholesale inheritance: specifically exclude API keys, cloud auth and PYTHONPATH.
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TZ", "SYSTEMROOT") if k in os.environ}
    home.mkdir(parents=True, exist_ok=True)
    env.update({"HOME": str(home), "TMPDIR": str(output_dir), "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "NO_COLOR": "1", "CI": "1"})
    return env


class ProcessRegistry:
    """Track only processes this Core started; support graceful MCP shutdown."""
    def __init__(self):
        self.lock = threading.Lock()
        self.active = set()
        self.stopped = False

    def add(self, process):
        with self.lock:
            if self.stopped:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.active.add(process)

    def remove(self, process):
        with self.lock:
            self.active.discard(process)

    def stop_all(self):
        with self.lock:
            self.stopped = True
            for process in self.active:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def bounded_process(argv: list[str], cwd: Path, env: dict[str, str], timeout: float, cap: int, registry: ProcessRegistry | None = None) -> dict:
    start = time.monotonic()
    timed_out = limited = False
    chunks, captured = [], 0
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True, shell=False)
    except OSError as exc:
        return {"exit_code": None, "error": type(exc).__name__, "stdout": "",
                "timeout": False, "output_limited": False, "seconds": time.monotonic() - start}
    assert proc.stdout is not None
    if registry:
        registry.add(proc)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() - start > timeout:
                    timed_out = True
                    break
                ready = selector.select(timeout=min(0.05, timeout))
                for key, _ in ready:
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    keep = min(len(data), max(0, cap - captured))
                    if keep:
                        chunks.append(data[:keep])
                        captured += keep
                    if len(data) > keep:
                        limited = True
                        break
                if limited:
                    break
        remaining = max(0.01, timeout - (time.monotonic() - start))
        if not (limited or timed_out):
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        # Reap child processes from the test group; never leave a server behind.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
        proc.stdout.close()
        if registry:
            registry.remove(proc)
    return {"exit_code": proc.returncode, "error": "CANCELLED" if registry and registry.stopped else None,
            "stdout": b"".join(chunks).decode("utf-8", errors="replace"),
            "timeout": timed_out, "output_limited": limited, "seconds": time.monotonic() - start}


class Runner:
    def __init__(self, workspace: Workspace, registry: ProcessRegistry | None = None):
        self.workspace = workspace
        self.registry = registry

    def run(self, run_id: str, snapshot: dict, check_id: str, check: Check, contract_hash: str) -> dict:
        started = now()
        root = Path(snapshot["path"])
        cwd = inside(root, check.cwd, must_exist=True)
        output = root / ".jev-sm-output"
        output.mkdir(exist_ok=True)
        report_path = inside(root, check.report_path) if check.report_path else None
        if report_path:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.unlink(missing_ok=True)  # Never accept a pre-existing report.
        record = bounded_process(check.argv, cwd, clean_environment(output, output / "home"),
                                 check.timeout_seconds, check.output_limit_bytes, self.registry)
        report, error = None, record["error"]
        if check.parser != "exit":
            try:
                report = parse_report(inside(root, check.report_path, must_exist=True), check.parser)
            except Exception as exc:
                error = f"REPORT_INVALID:{type(exc).__name__}"
        cases = [c.model_dump() for c in report.cases] if report else []
        failed = sum(c["status"] == "failed" for c in cases)
        skipped = sum(c["status"] == "skipped" for c in cases)
        if record["timeout"] or record["output_limited"] or error:
            outcome = "BLOCKED"
        elif record["exit_code"] != 0 or failed:
            outcome = "FAIL"
        elif check.kind == "test" and (len(cases) < check.min_tests or skipped):
            outcome = "NEEDS_REVIEW"
        else:
            outcome = "PASS"
        if not self.workspace.snapshot_unchanged(snapshot):
            outcome = "STALE"
        artifacts = self.workspace.state_dir / "artifacts" / run_id
        artifacts.mkdir(parents=True, exist_ok=True, mode=0o700)
        log = artifacts / f"{check_id}.log"
        log.write_text(redact(record["stdout"]), encoding="utf-8")
        files = {str(log): file_hash(log)}
        if report is not None:
            target = artifacts / f"{check_id}.report.json"
            target.write_text(report.model_dump_json(), encoding="utf-8")
            files[str(target)] = file_hash(target)
        return {"id": "ev-" + uuid.uuid4().hex[:16], "run_id": run_id, "check_id": check_id,
                "trust": "managed_runner", "contract_hash": contract_hash,
                "snapshot_hash": snapshot["hash"], "config_hash": snapshot["config_hash"],
                "environment_hash": snapshot["environment_hash"], "head": snapshot["head"],
                "check_hash": digest(check), "argv": check.argv, "cwd": check.cwd,
                "started_at": started, "ended_at": now(), "outcome": outcome,
                "exit_code": record["exit_code"], "timeout": record["timeout"],
                "output_limited": record["output_limited"], "error": error,
                "seconds": record["seconds"], "cases": cases,
                "counts": {"total": len(cases), "failed": failed, "skipped": skipped} if report else None,
                "artifact_hashes": files, "cost_usd": None,
                "cost_note": "Host and test infrastructure cost not observable"}
