"""The model never owns state transitions, authorization, or completion."""
from __future__ import annotations

import fnmatch
import json
import uuid
from pathlib import Path

from .approval import Authority, TerminalAuthority
from .common import DomainError, canonical, digest, file_hash, inside, now, redact
from .models import Contract, Improvement, Status
from .runner import ProcessRegistry, Runner
from .store import Store
from .workspace import Workspace


class Core:
    def __init__(self, workspace: Workspace, *, authority: Authority | None = None):
        self.workspace = workspace
        self.store = Store(workspace.state_dir / "state.sqlite3")
        self.authority = authority or TerminalAuthority()
        self.processes = ProcessRegistry()

    def prepare(self, request: str, key: str, source_refs: list[str] | None = None) -> dict:
        if not request.strip() or len(request) > 12000:
            raise DomainError("INVALID_REQUEST", "Provide a request of 1..12000 characters")
        refs = source_refs or []
        for value in refs:
            inside(self.workspace.root, value, must_exist=True)
        task = {"id": "task-" + uuid.uuid4().hex[:16], "revision": 0,
                "workspace_id": self.workspace.id, "request": request, "source_refs": refs,
                "state": Status.PLANNING.value, "created_at": now(), "updated_at": now(),
                "contract": None, "contract_version": 0, "contract_hash": None,
                "approval": None, "source_hashes": {}, "baseline_manifest": {},
                "baseline_recorded": False, "protected_approval": None,
                "reviews": [], "manual_acceptances": [], "strict_acceptances": [],
                "jobs": [], "completions": [], "started": False,
                "rounds": 0, "unchanged_failures": 0, "last_failure": None,
                "retrospective_status": "pending"}
        result = self.store.create(task, key, {"operation": "prepare", "request": request, "refs": refs})
        return result | {"plan_schema": Contract.model_json_schema(), "next_action": "submit_plan"}

    def _check_plan(self, plan: Contract):
        settings = self.workspace.settings()
        for c in plan.criteria:
            for check_id in c.check_ids:
                if check_id not in settings.checks:
                    raise DomainError("CHECK_NOT_APPROVED", f"Check is not registered: {check_id}")
                if c.method != settings.checks[check_id].kind:
                    raise DomainError("CHECK_TYPE_MISMATCH", "Process checks cannot prove behavioral criteria")
        if plan.blockers:
            raise DomainError("READINESS_GAPS", "Resolve the declared blockers before submitting a ready plan")
        for path in plan.source_refs:
            if self.workspace.secret_path(path):
                raise DomainError("SECRET_SOURCE", "Secret files cannot be specification source references")
            inside(self.workspace.root, path, must_exist=True)

    def submit_plan(self, task_id: str, plan: dict, revision: int, key: str) -> dict:
        contract = Contract.model_validate(plan)
        self._check_plan(contract)
        content = contract.model_dump(mode="json")
        source_hashes = {path: file_hash(inside(self.workspace.root, path, must_exist=True)) for path in contract.source_refs}
        contract_hash = digest({"plan": content, "source_hashes": source_hashes})
        def action(task, con):
            if task["state"] in {Status.VERIFYING, Status.CANCELLED}:
                raise DomainError("INVALID_STATE", "Cannot replace a plan during verification or after cancellation")
            if task_id in contract.dependencies or task_id == contract.parent_id:
                raise DomainError("DEPENDENCY_CYCLE", "A task cannot depend on itself")
            def visit(other: str, seen: set[str]):
                if other == task_id:
                    raise DomainError("DEPENDENCY_CYCLE", "Dependency cycle detected")
                if other in seen:
                    return
                seen.add(other)
                data = Store.load(con, other)
                for dep in (data.get("contract") or {}).get("dependencies", []):
                    visit(dep, seen)
            for dep in contract.dependencies:
                visit(dep, set())
            if contract.parent_id:
                Store.load(con, contract.parent_id)
            if contract_hash == task["contract_hash"]:
                return {"contract_hash": task["contract_hash"], "contract_version": task["contract_version"]}
            task["contract"] = content
            task["contract_version"] += 1
            task["contract_hash"] = contract_hash
            task["source_hashes"] = source_hashes
            task["approval"] = None
            task["state"] = Status.WAITING_USER.value
            return {"contract_hash": task["contract_hash"], "contract_version": task["contract_version"],
                    "next_action": "approve_plan_in_terminal"}
        return self.store.mutate(task_id, revision, key, "submit_plan", {"plan": content, "source_hashes": source_hashes}, action)

    def _approval_current(self, task: dict) -> bool:
        approval = task.get("approval") or {}
        for path, expected in task.get("source_hashes", {}).items():
            try:
                if file_hash(inside(self.workspace.root, path, must_exist=True)) != expected:
                    return False
            except (DomainError, OSError):
                return False
        if approval.get("contract_hash") != task["contract_hash"] or approval.get("config_hash") != self.workspace.config_hash():
            return False
        selected = approval.get("selected_task_ids", [task["id"]])
        frozen = approval.get("selected_plans", {})
        if list(selected) != list(dict.fromkeys(selected)) or task["id"] not in selected:
            return False
        for selected_id in selected:
            try:
                other = self.store.get(selected_id)
            except DomainError:
                return False
            expected = frozen.get(selected_id)
            other_approval = other.get("approval") or {}
            for path, expected_hash in expected.get("source_hashes", {}).items() if expected else []:
                try:
                    if file_hash(inside(self.workspace.root, path, must_exist=True)) != expected_hash:
                        return False
                except (DomainError, OSError):
                    return False
            if (not expected or other_approval.get("group_hash") != approval.get("group_hash") or
                    other["contract_hash"] != expected.get("contract_hash") or
                    other["contract_version"] != expected.get("contract_version") or
                    other.get("source_hashes", {}) != expected.get("source_hashes", {}) or
                    other_approval.get("selected_task_ids") != selected):
                return False
        return True

    def approve_plan(self, task_id: str, selected_task_ids: list[str] | None = None) -> dict:
        details, tasks, config_hash, manifest, protected_hash, group_hash = self._plan_approval_preview(task_id, selected_task_ids)
        task = self.store.get(task_id)
        receipt = self.authority.confirm("plan", group_hash, details)
        return self._record_plan_approval(task_id, task, details, tasks, config_hash, manifest,
                                           protected_hash, group_hash, receipt)

    def plan_approval_preview(self, task_id: str, selected_task_ids: list[str] | None = None) -> dict:
        """Return the exact plan card content and hash reviewed by a chat user."""
        details, _tasks, _config_hash, _manifest, _protected_hash, group_hash = self._plan_approval_preview(
            task_id, selected_task_ids)
        return {"approval_hash": group_hash, "details": details,
                "next_action": "present_plan_card_then_wait_for_explicit_user_chat_authorization"}

    def approve_plan_delegated(self, task_id: str, selected_task_ids: list[str] | None,
                               expected_hash: str) -> dict:
        """Record an explicitly user-authorized chat approval bound to a preview hash."""
        if not expected_hash:
            raise DomainError("APPROVAL_HASH_REQUIRED", "Delegated approval requires the reviewed preview hash")
        details, tasks, config_hash, manifest, protected_hash, group_hash = self._plan_approval_preview(
            task_id, selected_task_ids)
        if expected_hash != group_hash:
            raise DomainError("APPROVAL_STALE", "The reviewed plan card is stale; present it again")
        for item in tasks:
            previous = item.get("protected_approval") or {}
            if previous.get("hash") and previous["hash"] != protected_hash:
                raise DomainError("PROTECTED_APPROVAL_REQUIRED",
                                  "Protected inputs changed; obtain explicit protected review before delegated plan approval")
        task = self.store.get(task_id)
        receipt = {"id": "approval-" + uuid.uuid4().hex, "kind": "plan",
                   "content_hash": group_hash, "actor": "agent",
                   "source": "agent-mediated-chat-authorization",
                   "authorization": "agent_asserted_user_chat_instruction", "at": now()}
        return self._record_plan_approval(task_id, task, details, tasks, config_hash,
                                          manifest, protected_hash, group_hash, receipt)

    def _plan_approval_preview(self, task_id: str, selected_task_ids: list[str] | None = None):
        task = self.store.get(task_id)
        if not task["contract"]:
            raise DomainError("NO_PLAN", "Submit a structured plan first")
        selected = list(dict.fromkeys(selected_task_ids or [task_id]))
        if task_id not in selected:
            raise DomainError("INVALID_INPUT", "The approving task must be included in the selection")
        tasks = []
        for selected_id in selected:
            current = self.store.get(selected_id)
            if not current.get("contract"):
                raise DomainError("NO_PLAN", "Every selected task needs a structured plan")
            if current["state"] in {Status.VERIFYING, Status.CANCELLED, Status.DONE}:
                raise DomainError("INVALID_STATE", "Plan approval is not allowed for a selected task")
            self._check_plan(Contract.model_validate(current["contract"]))
            for path, expected in current.get("source_hashes", {}).items():
                if file_hash(inside(self.workspace.root, path, must_exist=True)) != expected:
                    raise DomainError("SOURCE_CHANGED", "Resubmit the plan after specification source changes")
            tasks.append(current)
        config_hash = self.workspace.config_hash()
        manifest = self.workspace.manifest()
        protected_hash = digest(self.workspace.protected_manifest(manifest))
        frozen = {item["id"]: {"contract_hash": item["contract_hash"],
                                "contract_version": item["contract_version"],
                                "source_hashes": item.get("source_hashes", {})} for item in tasks}
        details = {"plans": [{"task_id": item["id"], "contract": item["contract"],
                              "contract_version": item["contract_version"],
                              "contract_hash": item["contract_hash"]} for item in tasks],
                   "selected_task_ids": selected,
                   "settings": self.workspace.settings().model_dump(mode="json"),
                   "contract_hash": task["contract_hash"], "config_hash": config_hash,
                   "input_hash": digest(manifest), "protected_hash": protected_hash}
        group_hash = digest(details)
        return details, tasks, config_hash, manifest, protected_hash, group_hash

    def _record_plan_approval(self, task_id, task, details, tasks, config_hash, manifest,
                              protected_hash, group_hash, receipt):
        frozen = {item["id"]: {"contract_hash": item["contract_hash"],
                                "contract_version": item["contract_version"],
                                "source_hashes": item.get("source_hashes", {})} for item in tasks}
        def action(current, con):
            if self.workspace.config_hash() != config_hash or self.workspace.manifest() != manifest:
                raise DomainError("APPROVAL_STALE", "Configuration or inputs changed during confirmation")
            for item in tasks:
                latest = Store.load(con, item["id"])
                if latest["contract_hash"] != item["contract_hash"] or latest["contract_version"] != item["contract_version"]:
                    raise DomainError("APPROVAL_STALE", "A selected plan changed during confirmation")
                for path, expected in item.get("source_hashes", {}).items():
                    try:
                        actual = file_hash(inside(self.workspace.root, path, must_exist=True))
                    except (DomainError, OSError) as exc:
                        raise DomainError("APPROVAL_STALE", "A selected source changed during confirmation") from exc
                    if actual != expected:
                        raise DomainError("APPROVAL_STALE", "A selected source changed during confirmation")
                baseline_recorded = latest.get("baseline_recorded")
                if baseline_recorded is None:
                    # Older state has no marker. An existing approval means its baseline
                    # was already recorded; a started task without a marker is unsafe.
                    baseline_recorded = bool(latest.get("approval") or latest.get("protected_approval"))
                prior_baseline_recorded = bool(baseline_recorded)
                if latest["started"]:
                    if not baseline_recorded:
                        raise DomainError("BASELINE_REQUIRED", "Started task is missing its original delivery baseline")
                    self._reserve(latest, con)
                if not baseline_recorded:
                    latest["baseline_manifest"] = manifest
                latest["baseline_recorded"] = True
                if prior_baseline_recorded or latest.get("approval") or latest["started"]:
                    if not latest.get("protected_approval"):
                        raise DomainError("PROTECTED_APPROVAL_REQUIRED", "Existing approval lacks a protected baseline")
                elif not latest.get("protected_approval"):
                    latest["protected_approval"] = {"hash": protected_hash, "receipt": receipt}
                latest["approval"] = receipt | {"contract_hash": latest["contract_hash"],
                                                 "config_hash": config_hash, "group_hash": group_hash,
                                                 "selected_task_ids": selected, "selected_plans": frozen}
                latest["state"] = Status.IN_PROGRESS.value if latest["started"] else Status.READY.value
                if latest["id"] == current["id"]:
                    current.update(latest)
                else:
                    latest["revision"] += 1
                    latest["updated_at"] = now()
                    con.execute("UPDATE tasks SET revision=?,data=? WHERE id=?", (latest["revision"], canonical(latest), latest["id"]))
                    Store.event(con, latest["id"], "approve_plan", {"approval_id": receipt["id"], "group_hash": group_hash})
            return {"approval_id": receipt["id"], "selected_task_ids": selected, "group_hash": group_hash}
        selected = details["selected_task_ids"]
        return self.store.mutate(task_id, task["revision"], receipt["id"], "approve_plan", details, action)

    @staticmethod
    def _reserve(task, con):
        for row in con.execute("SELECT data FROM tasks WHERE id<>?", (task["id"],)):
            other = json.loads(row[0])
            if other["started"] and other["state"] not in {Status.DONE, Status.CANCELLED}:
                raise DomainError("WORKSPACE_BUSY", "Another task already owns this worktree")

    def start(self, task_id: str, revision: int, key: str) -> dict:
        def action(task, con):
            if not self._approval_current(task):
                raise DomainError("APPROVAL_REQUIRED", "The current plan and check configuration need approval")
            if task["state"] not in {Status.READY, Status.NEEDS_FIX, Status.IN_PROGRESS}:
                raise DomainError("INVALID_STATE", "Task is not ready to start")
            for dependency in task["contract"]["dependencies"]:
                if Store.load(con, dependency)["state"] != Status.DONE or not self._gate(Store.load(con, dependency))["eligible"]:
                    raise DomainError("DEPENDENCY_NOT_DONE", "A dependency has not completed")
            self._reserve(task, con)
            task["started"], task["state"] = True, Status.IN_PROGRESS.value
            return {"next_action": "implement_with_existing_agent"}
        return self.store.mutate(task_id, revision, key, "start", {}, action)

    def progress(self, task_id: str, observation: str, revision: int, key: str) -> dict:
        if not observation.strip() or len(observation) > 12000:
            raise DomainError("INVALID_OBSERVATION", "Observation must be 1..12000 characters")
        def action(task, con):
            return {"trust": "agent_claim", "observation": redact(observation),
                    "note": "Progress claims never change criterion status or completion"}
        return self.store.mutate(task_id, revision, key, "progress", {"observation": observation}, action)

    def _required_checks(self, task: dict) -> list[str]:
        result = set(self.workspace.settings().dod_check_ids)
        for criterion in task["contract"]["criteria"]:
            result.update(criterion["check_ids"])
        return sorted(result)

    def begin_verification(self, task_id: str, revision: int, key: str,
                           check_ids: list[str] | None = None) -> dict:
        def action(task, con):
            if not self._approval_current(task):
                raise DomainError("APPROVAL_REQUIRED", "Current plan/configuration is not approved")
            if task["state"] not in {Status.IN_PROGRESS, Status.NEEDS_FIX, Status.WAITING_USER} or not task["started"]:
                raise DomainError("INVALID_STATE", "Start the task, or explicitly resume a blocked task")
            self._reserve(task, con)
            required = self._required_checks(task)
            selected = check_ids if check_ids is not None else required
            if sorted(selected) != required:
                raise DomainError("CHECK_NOT_APPROVED", "This alpha executes the complete approved verification set")
            settings = self.workspace.settings()
            if task["rounds"] >= settings.max_verification_rounds:
                raise DomainError("RETRY_BUDGET_EXCEEDED", "Human resume is required")
            run_id = "run-" + uuid.uuid4().hex[:16]
            job = {"id": run_id, "state": "QUEUED", "check_ids": required,
                   "contract_hash": task["contract_hash"], "config_hash": self.workspace.config_hash(),
                   "created_at": now(), "evidence": [], "snapshot": None}
            task["jobs"].append(job)
            task["state"] = Status.VERIFYING.value
            return {"job_id": run_id, "next_action": "poll_status"}
        return self.store.mutate(task_id, revision, key, "begin_verification",
                                 {"check_ids": check_ids}, action)

    def execute_verification(self, task_id: str, run_id: str) -> dict:
        # Claim the job atomically; replays and concurrent processes do not run it twice.
        with self.store.transaction() as con:
            task = Store.load(con, task_id)
            job = next((j for j in task["jobs"] if j["id"] == run_id), None)
            if job is None:
                raise DomainError("JOB_NOT_FOUND", "Unknown verification job")
            if job["state"] != "QUEUED":
                return {"job_id": run_id, "state": job["state"]}
            job["state"] = "RUNNING"
            con.execute("UPDATE tasks SET data=? WHERE id=?", (canonical(task), task_id))
            Store.event(con, task_id, "verification_started", {"job_id": run_id})
        evidence, snap, error = [], None, None
        try:
            if job["config_hash"] != self.workspace.config_hash():
                raise DomainError("APPROVAL_REQUIRED", "Configuration changed before execution")
            snap = self.workspace.snapshot(run_id)
            self.workspace.save_snapshot_metadata(run_id, snap)
            settings = self.workspace.settings()
            runner = Runner(self.workspace, self.processes)
            for check_id in job["check_ids"]:
                evidence.append(runner.run(run_id, snap, check_id, settings.checks[check_id], task["contract_hash"]))
            if self.workspace.content_hash() != snap["hash"] or not self.workspace.snapshot_unchanged(snap):
                for item in evidence:
                    item["outcome"] = "STALE"
                error = "EVIDENCE_STALE"
        except Exception as exc:
            error = exc.code if isinstance(exc, DomainError) else type(exc).__name__
        with self.store.transaction() as con:
            task = Store.load(con, task_id)
            target = next(j for j in task["jobs"] if j["id"] == run_id)
            target.update({"state": "FINISHED", "finished_at": now(), "snapshot": snap,
                           "evidence": evidence, "error": error})
            # An operator may have recovered/cancelled during execution; never overwrite it.
            if task["state"] == Status.VERIFYING:
                if error or any(e["outcome"] in {"BLOCKED", "STALE"} for e in evidence):
                    task["state"] = Status.BLOCKED.value
                else:
                    task["rounds"] += 1
                    failed = [e for e in evidence if e["outcome"] != "PASS"]
                    if failed:
                        fingerprint = digest({"snapshot": snap["hash"], "failures": [
                            {"check": e["check_id"], "outcome": e["outcome"], "cases": e["cases"]} for e in failed]})
                        task["unchanged_failures"] = task["unchanged_failures"] + 1 if task["last_failure"] == fingerprint else 1
                        task["last_failure"] = fingerprint
                        cfg = self.workspace.settings()
                        reached = (task["rounds"] >= cfg.max_verification_rounds or
                                   task["unchanged_failures"] >= cfg.max_unchanged_failures)
                        task["state"] = Status.BLOCKED.value if reached else Status.NEEDS_FIX.value
                    else:
                        task["unchanged_failures"] = 0
                        task["state"] = Status.WAITING_USER.value
            task["revision"] += 1
            con.execute("UPDATE tasks SET revision=?,data=? WHERE id=?", (task["revision"], canonical(task), task_id))
            Store.event(con, task_id, "verification_finished", {"job_id": run_id, "error": error,
                                                                "outcomes": [e["outcome"] for e in evidence]})
            return {"job_id": run_id, "state": target["state"], "task_state": task["state"],
                    "revision": task["revision"], "error": error}

    def verify(self, task_id: str, revision: int, key: str) -> dict:
        result = self.begin_verification(task_id, revision, key)
        return self.execute_verification(task_id, result["job_id"])

    @staticmethod
    def _review_binding(task: dict, snap: dict, evidence: list[dict]) -> str:
        return digest({"contract": task["contract_hash"], "snapshot": snap["hash"],
                       "config": snap["config_hash"], "environment": snap["environment_hash"],
                       "evidence": evidence})

    def gate(self, task_id: str) -> dict:
        return self._gate(self.store.get(task_id))

    def _gate(self, task: dict) -> dict:
        issues, criteria = [], {}
        if not task["contract"]:
            return {"eligible": False, "exit_code": 2, "issues": ["NO_PLAN"], "criteria": {}}
        if not self._approval_current(task):
            issues.append("APPROVAL_REQUIRED")
        if task["state"] in {Status.CANCELLED, Status.BLOCKED, Status.VERIFYING}:
            issues.append("TASK_" + task["state"])
        content_hash = self.workspace.content_hash()
        jobs = task["jobs"]
        job = jobs[-1] if jobs else None
        snap = (job or {}).get("snapshot")
        evidence = (job or {}).get("evidence", [])
        checks = {e["check_id"]: e for e in evidence}
        stale = False
        if snap:
            stale = (snap["hash"] != content_hash or snap["config_hash"] != self.workspace.config_hash()
                     or snap["environment_hash"] != self.workspace.environment_hash()
                     or job["contract_hash"] != task["contract_hash"])
            for e in evidence:
                if e["outcome"] == "STALE":
                    stale = True
                for name, expected in e["artifact_hashes"].items():
                    path = Path(name)
                    try:
                        if not path.is_relative_to(self.workspace.state_dir) or not path.is_file() or file_hash(path) != expected:
                            stale = True
                    except OSError:
                        stale = True
            if not self.workspace.snapshot_unchanged(snap):
                stale = True
        elif job:
            issues.append("VERIFICATION_UNAVAILABLE")
        if stale:
            issues.append("EVIDENCE_STALE")
        if job and job.get("error"):
            issues.append(job["error"])
        binding = self._review_binding(task, snap, evidence) if snap else None
        reviewed = bool(binding and any(r["binding"] == binding for r in task["reviews"]))
        for c in task["contract"]["criteria"]:
            outcome = "NOT_RUN"
            if c["method"] == "manual":
                approved = any(a["ac_id"] == c["id"] and a["binding"] == binding
                               for a in task["manual_acceptances"]) if binding else False
                outcome = "PASS" if approved else "NEEDS_REVIEW"
            elif all(cid in checks for cid in c["check_ids"]):
                outcomes = [checks[cid]["outcome"] for cid in c["check_ids"]]
                outcome = next((s for s in ["STALE", "BLOCKED", "FAIL", "NEEDS_REVIEW"] if s in outcomes), "PASS")
                if outcome == "FAIL" and c["method"] == "test":
                    # A different failing test in the same command is not evidence
                    # that this criterion was observed to fail. Keep it unverified.
                    own_statuses = [case["status"] for cid, ids in c["case_ids"].items()
                                    for case in checks[cid]["cases"] if case["id"] in ids]
                    if "failed" not in own_statuses:
                        outcome = "NEEDS_REVIEW"
                if outcome == "PASS" and c["method"] == "test":
                    for cid, ids in c["case_ids"].items():
                        cases = {case["id"]: case["status"] for case in checks[cid]["cases"]}
                        if any(cases.get(identity) != "passed" for identity in ids):
                            outcome = "NEEDS_REVIEW"
                if outcome == "PASS" and task["contract"]["review_profile"] != "light" and not reviewed:
                    outcome = "NEEDS_REVIEW"
            criteria[c["id"]] = "STALE" if stale else outcome
        for check_id in self.workspace.settings().dod_check_ids:
            if check_id not in checks or checks[check_id]["outcome"] != "PASS":
                issues.append("DOD_NOT_PASSED:" + check_id)
        if task["contract"]["review_profile"] != "light" and not reviewed:
            issues.append("INDEPENDENT_REVIEW_REQUIRED")
        if task["contract"]["review_profile"] == "strict":
            if not binding or not any(r["binding"] == binding for r in task["strict_acceptances"]):
                issues.append("STRICT_ACCEPTANCE_REQUIRED")
        protected = task.get("protected_approval") or {}
        if protected.get("hash") != self.workspace.protected_hash():
            issues.append("PROTECTED_INPUTS_CHANGED")
        current = self.workspace.manifest()
        changed = [p for p in set(current) | set(task["baseline_manifest"])
                   if current.get(p) != task["baseline_manifest"].get(p)]
        cfg = self.workspace.settings()
        if task["contract"]["review_profile"] != "strict" and any(
            fnmatch.fnmatch(p, pattern) for p in changed for pattern in cfg.strict_globs
        ):
            issues.append("STRICT_PROFILE_REQUIRED")
        if task["contract"]["review_profile"] == "light" and any(
            not (p.endswith((".md", ".rst", ".txt")) or p.startswith("docs/")) for p in changed
        ):
            issues.append("LIGHT_SCOPE_EXCEEDED")
        for c_id, outcome in criteria.items():
            if outcome != "PASS":
                issues.append(f"{c_id}:{outcome}")
        if not snap:
            issues.append("NO_VERIFICATION_SNAPSHOT")
        if self.workspace.content_hash() != content_hash:
            issues.append("EVIDENCE_STALE")
        return {"eligible": not issues, "exit_code": 3 if "EVIDENCE_STALE" in issues else (2 if issues else 0),
                "issues": sorted(set(issues)), "criteria": criteria, "content_hash": content_hash,
                "review_binding": binding, "next_action": "complete" if not issues else "resolve_gate_issues"}

    def complete(self, task_id: str, revision: int, key: str) -> dict:
        def action(task, con):
            gate = self._gate(task)
            if gate["eligible"]:
                if task["state"] != Status.DONE:
                    task["completions"].append({"at": now(), "contract_hash": task["contract_hash"],
                                                "snapshot_hash": gate["content_hash"], "binding": gate["review_binding"]})
                task["state"] = Status.DONE.value
            return gate
        return self.store.mutate(task_id, revision, key, "request_completion", {}, action)

    def human_attest(self, task_id: str, kind: str, *, ac_id: str | None = None,
                     selected_task_ids: list[str] | None = None) -> dict:
        task = self.store.get(task_id)
        selected = list(dict.fromkeys(selected_task_ids or [task_id]))
        if task_id not in selected:
            raise DomainError("INVALID_INPUT", "The approving task must be included in the selection")
        if kind != "review" and selected != [task_id]:
            raise DomainError("INVALID_INPUT", "Only review approvals can cover multiple tasks")
        tasks, gates = [], []
        for selected_id in selected:
            current = self.store.get(selected_id)
            if current["state"] == Status.VERIFYING:
                raise DomainError("INVALID_STATE", "Wait for verification to finish")
            current_gate = self._gate(current)
            if kind != "protected" and (not current_gate["review_binding"] or "EVIDENCE_STALE" in current_gate["issues"]):
                raise DomainError("EVIDENCE_STALE", "Run verification against the current contract first")
            tasks.append(current)
            gates.append(current_gate)
        gate = gates[0]
        if kind == "protected":
            binding = self.workspace.protected_hash()
            details = {"protected_hash": binding, "files": self.workspace.protected_manifest(),
                       "warning": "Review every protected test/config change, including weakened assertions"}
        else:
            binding = gate["review_binding"]
            if kind == "criterion":
                criterion = next((c for c in task["contract"]["criteria"] if c["id"] == ac_id), None)
                if criterion is None or criterion["method"] != "manual":
                    raise DomainError("INVALID_CRITERION", "Human criterion approval is only for manual criteria")
            elif kind not in {"review", "strict"}:
                raise DomainError("INVALID_APPROVAL_KIND", "Unsupported confirmation")
            details = {"kind": kind, "ac_id": ac_id, "selected_task_ids": selected,
                       "plans": [{"task_id": item["id"], "contract": item["contract"],
                                  "contract_version": item["contract_version"],
                                  "contract_hash": item["contract_hash"]} for item in tasks],
                       "contract": task["contract"], "binding": binding, "gate": gate,
                       "gates": gates, "evidence": task["jobs"][-1]["evidence"],
                       "evidence_sets": [item["jobs"][-1]["evidence"] for item in tasks],
                       "instructions": "Inspect assertions, required cases, and actual behavior; approval cannot waive failed checks"}
        approval_hash = digest(details)
        receipt = self.authority.confirm(kind, approval_hash, details)
        def action(current, con):
            if kind == "protected":
                if self.workspace.protected_hash() != binding:
                    raise DomainError("APPROVAL_STALE", "Protected inputs changed during confirmation")
                current["protected_approval"] = {"hash": binding, "receipt": receipt}
            else:
                for item_task, expected_gate in zip(tasks, gates):
                    latest = Store.load(con, item_task["id"])
                    check = self._gate(latest)
                    if check["review_binding"] != expected_gate["review_binding"] or "EVIDENCE_STALE" in check["issues"]:
                        raise DomainError("APPROVAL_STALE", "Evidence changed during confirmation")
                    item = {"receipt": receipt, "binding": expected_gate["review_binding"]}
                    if kind == "review":
                        latest["reviews"].append(item | {"reviewer": "human_substitute"})
                    elif kind == "strict":
                        latest["strict_acceptances"].append(item)
                    else:
                        latest["manual_acceptances"].append(item | {"ac_id": ac_id})
                    if latest["id"] == current["id"]:
                        current.update(latest)
                    else:
                        latest["revision"] += 1
                        latest["updated_at"] = now()
                        con.execute("UPDATE tasks SET revision=?,data=? WHERE id=?", (latest["revision"], canonical(latest), latest["id"]))
                        Store.event(con, latest["id"], "human_attestation", {"approval_id": receipt["id"], "kind": kind})
            return {"approval_id": receipt["id"], "kind": kind}
        return self.store.mutate(task_id, task["revision"], receipt["id"], "human_attestation", details, action)

    def resume(self, task_id: str) -> dict:
        task = self.store.get(task_id)
        if task["state"] == Status.CANCELLED:
            raise DomainError("INVALID_STATE", "Cancelled tasks require a new task")
        if task["state"] == Status.VERIFYING:
            raise DomainError("RUNNING_JOB", "Use recovery only after confirming the old process has stopped")
        details = {"task_id": task_id, "revision": task["revision"], "gate": self._gate(task),
                   "action": "reset bounded verification budget; retain all evidence"}
        receipt = self.authority.confirm("resume", digest(details), details)
        def action(current, con):
            if not self._approval_current(current):
                raise DomainError("APPROVAL_REQUIRED", "Reapprove the current contract first")
            self._reserve(current, con)
            current.update(state=Status.IN_PROGRESS.value, rounds=0, unchanged_failures=0, started=True)
            return {"previous_completions_retained": len(current["completions"])}
        return self.store.mutate(task_id, task["revision"], receipt["id"], "resume", details, action)

    def cancel(self, task_id: str, reason: str, revision: int, key: str) -> dict:
        def action(task, con):
            if task["state"] == Status.VERIFYING:
                raise DomainError("RUNNING_JOB", "Stop the hosting process before recovering a running job")
            task["state"] = Status.CANCELLED.value
            return {"reason": redact(reason)}
        return self.store.mutate(task_id, revision, key, "cancel", {"reason": reason}, action)

    def status(self, task_id: str) -> dict:
        task = self.store.get(task_id)
        gate = self._gate(task)
        return {"task": task, "gate": gate, "current_completion_valid": task["state"] == Status.DONE and gate["eligible"],
                "decisions": self.store.decisions(task_id), "host_cost_usd": None,
                "cost_note": "Host/LLM usage is not observable through these adapters"}

    def compact_status(self, task_id: str, job_id: str | None = None) -> dict:
        """Bound hot CLI/MCP responses; full local state is an explicit diagnostic option."""
        task = self.store.get(task_id)
        gate = self._gate(task)
        jobs = task["jobs"][-4:]
        if job_id:
            jobs = [j for j in task["jobs"] if j["id"] == job_id]
            if not jobs:
                raise DomainError("JOB_NOT_FOUND", "Unknown job for this task")
        summaries = [{"id": j["id"], "state": j["state"], "error": j.get("error"),
                      "snapshot_hash": (j.get("snapshot") or {}).get("hash"),
                      "evidence": [{"id": e["id"], "check_id": e["check_id"],
                                    "outcome": e["outcome"], "counts": e["counts"]}
                                   for e in j["evidence"]]} for j in jobs]
        result = {"task": {k: task[k] for k in
                            ("id", "revision", "state", "contract_version", "contract_hash", "rounds")},
                  "title": (task["contract"] or {}).get("title"), "gate": gate,
                  "current_completion_valid": task["state"] == Status.DONE and gate["eligible"],
                  "jobs": summaries, "total_jobs": len(task["jobs"]),
                  "detail_tool": "sm_get_evidence", "detail_command": "evidence", "host_cost_usd": None}
        if job_id:
            result["job"] = summaries[0]
        return result

    def evidence_detail(self, task_id: str, evidence_id: str, artifact: str | None = None,
                        offset: int = 0, max_chars: int = 6000) -> dict:
        """Read only registered, integrity-checked evidence with bounded pagination."""
        if offset < 0 or not 1 <= max_chars <= 24000:
            raise DomainError("INVALID_RANGE", "Use a nonnegative offset and 1..24000 characters")
        task = self.store.get(task_id)
        found = next((e for j in task["jobs"] for e in j["evidence"] if e["id"] == evidence_id), None)
        if found is None:
            raise DomainError("EVIDENCE_NOT_FOUND", "No such evidence in this task")
        available = {Path(name).name: (name, sha) for name, sha in found["artifact_hashes"].items()}
        metadata = {k: found[k] for k in ("id", "run_id", "check_id", "outcome", "counts",
                                         "snapshot_hash", "contract_hash", "exit_code", "error")}
        if artifact is None:
            return metadata | {"artifacts": sorted(available),
                               "note": "Read an artifact by name; historical evidence is not current completion proof"}
        if artifact not in available:
            raise DomainError("ARTIFACT_NOT_FOUND", "Select an artifact name returned for this evidence")
        name, expected = available[artifact]
        try:
            rel = Path(name).relative_to(self.workspace.state_dir).as_posix()
            path = inside(self.workspace.state_dir, rel, must_exist=True)
        except (ValueError, DomainError) as exc:
            raise DomainError("EVIDENCE_STALE", "Artifact is unavailable or outside local state") from exc
        if file_hash(path) != expected:
            raise DomainError("EVIDENCE_STALE", "Artifact integrity check failed")
        text = redact(path.read_text(encoding="utf-8"))
        end = min(offset + max_chars, len(text))
        return metadata | {"artifact": artifact, "text": text[offset:end], "offset": offset,
                           "total_chars": len(text), "next_offset": end if end < len(text) else None,
                           "units": "characters, not tokens"}

    def propose_improvement(self, task_id: str, proposal: dict, revision: int, key: str) -> dict:
        parsed = Improvement.model_validate(proposal)
        def action(task, con):
            known = {e["id"] for j in task["jobs"] for e in j["evidence"]}
            if set(parsed.evidence_ids) - known:
                raise DomainError("UNKNOWN_EVIDENCE", "Improvement references must belong to this task")
            rows = con.execute("SELECT data FROM rules").fetchall()
            if sum(json.loads(r[0])["task_id"] == task_id for r in rows) >= 3:
                raise DomainError("RULE_LIMIT", "At most three proposals per task")
            rule_id = "rule-" + uuid.uuid4().hex[:16]
            rule = {"id": rule_id, "task_id": task_id, "status": "PROPOSED",
                    "proposal": parsed.model_dump(), "validation": "human_review_required"}
            con.execute("INSERT INTO rules VALUES(?,?)", (rule_id, canonical(rule)))
            task["retrospective_status"] = "proposed"
            return {"rule_id": rule_id, "rule_status": "PROPOSED"}
        return self.store.mutate(task_id, revision, key, "propose_improvement", parsed.model_dump(), action)

    def approve_rule(self, rule_id: str, retire: bool = False) -> dict:
        with self.store.connect() as con:
            row = con.execute("SELECT data FROM rules WHERE id=?", (rule_id,)).fetchone()
        if not row:
            raise DomainError("RULE_NOT_FOUND", "Unknown rule")
        rule = json.loads(row[0])
        receipt = self.authority.confirm("retire_rule" if retire else "approve_rule", digest(rule), rule)
        with self.store.transaction() as con:
            current = json.loads(con.execute("SELECT data FROM rules WHERE id=?", (rule_id,)).fetchone()[0])
            if digest(current) != digest(rule):
                raise DomainError("REVISION_CONFLICT", "Rule changed during confirmation")
            rule.update(status="RETIRED" if retire else "APPROVED", receipt=receipt)
            con.execute("UPDATE rules SET data=? WHERE id=?", (canonical(rule), rule_id))
            Store.event(con, rule["task_id"], "rule_status_changed", {"rule_id": rule_id, "status": rule["status"]})
        return rule

    def rule_candidates(self, kind: str, paths: list[str]) -> list[dict]:
        with self.store.connect() as con:
            rules = [json.loads(x[0]) for x in con.execute("SELECT data FROM rules")]
        return [r for r in rules if r["status"] == "APPROVED" and kind in r["proposal"]["task_kinds"]
                and any(fnmatch.fnmatch(p, g) for p in paths for g in r["proposal"]["path_globs"])]
