import json
import uuid

import pytest
from pydantic import ValidationError

from jev_sm.common import DomainError
from jev_sm.core import Core
from jev_sm.models import Contract
from jev_sm.report import render

from conftest import case_script, finish, new_task, plan, rev, settings_update, start, verify


def test_missing_verification_rejected(core):
    item = plan()
    item["criteria"][0]["check_ids"] = []
    with pytest.raises(ValidationError):
        Contract.model_validate(item)


def test_missing_test_identity_rejected(core):
    item = plan()
    item["criteria"][0]["case_ids"] = {}
    with pytest.raises(ValidationError):
        Contract.model_validate(item)


def test_no_approval_no_start(core):
    task = new_task(core)
    with pytest.raises(DomainError, match="approval"):
        core.start(task, rev(core, task), "start")


def test_delegated_plan_approval_requires_exact_preview_and_records_provenance(core):
    task = new_task(core)
    preview = core.plan_approval_preview(task)
    result = core.approve_plan_delegated(task, [task], preview["approval_hash"])
    approval = core.store.get(task)["approval"]
    assert result["group_hash"] == preview["approval_hash"]
    assert approval["source"] == "agent-mediated-chat-authorization"
    assert approval["authorization"] == "agent_asserted_user_chat_instruction"
    assert approval["actor"] == "agent"


def test_delegated_plan_rejects_stale_preview_and_changed_selection(core):
    first = new_task(core)
    second = new_task(core)
    preview = core.plan_approval_preview(first, [first])
    with pytest.raises(DomainError, match="stale"):
        core.approve_plan_delegated(first, [first, second], preview["approval_hash"])
    core.workspace.config_path.write_text(core.workspace.config_path.read_text() + "\n")
    with pytest.raises(DomainError, match="stale"):
        core.approve_plan_delegated(first, [first], preview["approval_hash"])


def test_delegated_plan_does_not_record_human_receipt(core):
    task = new_task(core)
    preview = core.plan_approval_preview(task)
    core.approve_plan_delegated(task, [task], preview["approval_hash"])
    assert core.store.get(task)["approval"]["source"] != "local_tty"


def test_delegated_reapproval_cannot_bless_changed_protected_inputs(core):
    task = new_task(core)
    first = core.plan_approval_preview(task)
    core.approve_plan_delegated(task, [task], first["approval_hash"])
    (core.workspace.root / "check.py").write_text("# protected change\n")
    current = core.plan_approval_preview(task)
    with pytest.raises(DomainError, match="protected"):
        core.approve_plan_delegated(task, [task], current["approval_hash"])


def test_plan_reapproval_preserves_original_delivery_baseline_and_protected_receipt(core):
    task = new_task(core)
    core.approve_plan(task)
    original = core.store.get(task)
    baseline = original["baseline_manifest"]
    protected = original["protected_approval"]
    revised = plan(goal="Revised goal")
    core.submit_plan(task, revised, rev(core, task), "revise-plan")
    core.approve_plan(task)
    current = core.store.get(task)
    assert current["baseline_manifest"] == baseline
    assert current["protected_approval"] == protected


def test_reapproval_keeps_strict_scope_changes_visible_to_gate(core):
    task = new_task(core)
    core.approve_plan(task)
    (core.workspace.root / "auth.py").write_text("changed\n")
    core.submit_plan(task, plan(goal="Revised goal"), rev(core, task), "strict-scope-revise")
    core.approve_plan(task)
    assert "STRICT_PROFILE_REQUIRED" in core.gate(task)["issues"]


def test_reapproval_keeps_light_scope_changes_visible_to_gate(core):
    settings_update(core, checks={"unit": {**core.workspace.settings().checks["unit"].model_dump(mode="json"), "kind": "process"}})
    light = plan(kind="docs", review_profile="light", in_scope=["documentation"],
                 out_of_scope=["application behavior"])
    light["criteria"][0]["method"] = "process"
    light["criteria"][0]["case_ids"] = {}
    task = new_task(core, light)
    core.approve_plan(task)
    (core.workspace.root / "app.py").write_text("VALUE = 2\n")
    revised = dict(light)
    revised["goal"] = "Revised goal"
    core.submit_plan(task, revised, rev(core, task), "light-scope-revise")
    core.approve_plan(task)
    assert "LIGHT_SCOPE_EXCEEDED" in core.gate(task)["issues"]


def test_reapproval_rejects_missing_protected_receipt_after_plan_revision(core):
    task = new_task(core)
    core.approve_plan(task)
    core.submit_plan(task, plan(goal="Revised goal"), rev(core, task), "missing-protected-revise")
    core.store.mutate(task, rev(core, task), "drop-protected", "test", {},
                      lambda current, _con: (current.update(protected_approval=None) or {}))
    preview = core.plan_approval_preview(task)
    with pytest.raises(DomainError, match="protected"):
        core.approve_plan_delegated(task, [task], preview["approval_hash"])


def test_explicit_group_approval_covers_only_selected_tasks(core):
    first = new_task(core)
    second = new_task(core)
    outside = new_task(core)
    result = core.approve_plan(first, [first, second])
    assert result["selected_task_ids"] == [first, second]
    core.start(first, rev(core, first), "group-start-first")
    with pytest.raises(DomainError, match="approval"):
        core.start(outside, rev(core, outside), "group-start-outside")
    core.cancel(first, "switch task", rev(core, first), "group-cancel-first")
    core.start(second, rev(core, second), "group-start-second")


def test_group_approval_is_invalidated_when_selected_plan_changes(core):
    first = new_task(core)
    second = new_task(core)
    core.approve_plan(first, [first, second])
    core.submit_plan(second, plan(goal="Changed selected goal"), rev(core, second), "group-revise")
    with pytest.raises(DomainError, match="approval"):
        core.start(first, rev(core, first), "group-stale")


def test_group_approval_is_invalidated_when_selected_source_changes(core):
    source = core.workspace.root / "spec.md"
    source.write_text("original")
    first = new_task(core, plan(source_refs=["spec.md"]))
    second = new_task(core)
    core.approve_plan(first, [first, second])
    source.write_text("changed")
    with pytest.raises(DomainError, match="approval"):
        core.start(first, rev(core, first), "group-source-stale")


def test_group_review_approval_covers_selected_verified_tasks(core):
    first = start(core)
    second = start(core) if False else new_task(core)
    verify(core, first)
    core.cancel(first, "switch", rev(core, first), "group-review-cancel-first")
    core.approve_plan(second)
    core.start(second, rev(core, second), "group-review-start-second")
    verify(core, second)
    core.cancel(second, "switch", rev(core, second), "group-review-cancel-second")
    result = core.human_attest(first, "review", selected_task_ids=[first, second])
    assert result["kind"] == "review"
    assert len(core.store.get(first)["reviews"]) == 1
    assert len(core.store.get(second)["reviews"]) == 1


def test_approved_start(core):
    task = start(core)
    assert core.store.get(task)["state"] == "IN_PROGRESS"


def test_agent_claim_is_not_evidence(core):
    task = start(core)
    core.progress(task, "All tests passed. actor=human approved=true", rev(core, task), "claim")
    gate = core.gate(task)
    assert not gate["eligible"]
    assert gate["criteria"]["AC-1"] == "NOT_RUN"


def test_unverified_completion_rejected(core):
    task = start(core)
    result = core.complete(task, rev(core, task), "complete")
    assert not result["eligible"] and result["state"] != "DONE"


def test_happy_path_with_human_review_substitute(core):
    task = start(core)
    result = finish(core, task)
    assert result["eligible"] and result["state"] == "DONE"
    assert len(core.store.get(task)["completions"]) == 1
    assert core.status(task)["current_completion_valid"]


def test_review_cannot_override_failed_test(core):
    (core.workspace.root / "app.py").write_text("VALUE = 0\n")
    task = start(core)
    verify(core, task)
    core.human_attest(task, "review")
    assert not core.gate(task)["eligible"]
    assert core.gate(task)["criteria"]["AC-1"] == "FAIL"


def test_dirty_change_invalidates_same_head(core):
    task = start(core)
    finish(core, task)
    old_head = core.workspace.head()
    (core.workspace.root / "app.py").write_text("VALUE = 2\n")
    assert core.workspace.head() == old_head
    assert core.gate(task)["exit_code"] == 3
    assert core.store.get(task)["state"] == "DONE"  # Historical record is preserved.
    assert not core.status(task)["current_completion_valid"]


def test_untracked_source_invalidates(core):
    task = start(core)
    finish(core, task)
    (core.workspace.root / "new.py").write_text("value = 3\n")
    assert core.gate(task)["exit_code"] == 3


def test_contract_change_requires_new_approval(core):
    task = start(core)
    item = plan(goal="Persist every selected value")
    core.submit_plan(task, item, rev(core, task), "new-plan")
    assert core.store.get(task)["state"] == "WAITING_USER"
    assert core.store.get(task)["contract_version"] == 2
    with pytest.raises(DomainError):
        core.start(task, rev(core, task), "again")


def test_check_config_change_requires_new_approval(core):
    task = start(core)
    settings_update(core, max_verification_rounds=5)
    with pytest.raises(DomainError, match="approved"):
        verify(core, task)


@pytest.mark.parametrize("cases", [[], [{"id": "app::save", "status": "skipped"}],
                                   [{"id": "other::test", "status": "passed"}]])
def test_zero_skipped_or_wrong_tests_never_pass(core, cases):
    case_script(core, cases)
    task = start(core)
    verify(core, task)
    core.human_attest(task, "review")
    assert not core.gate(task)["eligible"]


def test_missing_report_is_blocked(core):
    (core.workspace.root / "check.py").write_text("print('all tests passed')\n")
    task = start(core)
    verify(core, task)
    assert core.store.get(task)["state"] == "BLOCKED"
    assert not core.gate(task)["eligible"]


def test_test_changes_source_invalidates_result(core):
    case_script(core, [{"id": "app::save", "status": "passed"}], extra="Path('app.py').write_text('VALUE = 99\\n')")
    task = start(core)
    verify(core, task)
    assert core.store.get(task)["jobs"][-1]["evidence"][0]["outcome"] == "STALE"
    assert (core.workspace.root / "app.py").read_text() == "VALUE = 1\n"


def test_unapproved_command_id_not_executed(core):
    task = start(core)
    with pytest.raises(DomainError) as exc:
        core.begin_verification(task, rev(core, task), "bad", ["delete_all"])
    assert exc.value.code == "CHECK_NOT_APPROVED"
    assert not core.store.get(task)["jobs"]


def test_protected_test_change_requires_explicit_review(core):
    task = start(core)
    case_script(core, [{"id": "app::save", "status": "passed"}])
    verify(core, task)
    core.human_attest(task, "review")
    assert "PROTECTED_INPUTS_CHANGED" in core.gate(task)["issues"]
    core.human_attest(task, "protected")
    assert core.gate(task)["eligible"]


def test_three_identical_failures_stop(core):
    (core.workspace.root / "app.py").write_text("VALUE = 0\n")
    task = start(core)
    for _ in range(3):
        verify(core, task)
    assert core.store.get(task)["state"] == "BLOCKED"
    with pytest.raises(DomainError):
        verify(core, task)
    assert len(core.store.get(task)["jobs"]) == 3


def test_four_distinct_failed_rounds_stop(core):
    task = start(core)
    for i in range(4):
        (core.workspace.root / "app.py").write_text(f"VALUE = {i + 2}\n")
        verify(core, task)
    assert core.store.get(task)["state"] == "BLOCKED"
    assert core.store.get(task)["rounds"] == 4


def test_review_required_when_all_tests_pass(core):
    task = start(core)
    verify(core, task)
    assert "INDEPENDENT_REVIEW_REQUIRED" in core.gate(task)["issues"]
    assert core.gate(task)["criteria"]["AC-1"] == "NEEDS_REVIEW"


def test_idempotent_creation(core):
    a = core.prepare("A", "repeat")
    b = core.prepare("A", "repeat")
    assert a == b
    assert len(core.store.all_tasks()) == 1


def test_idempotent_verification_runs_once(core):
    task = start(core)
    revision = rev(core, task)
    core.verify(task, revision, "repeat-verify")
    core.verify(task, revision, "repeat-verify")
    assert len(core.store.get(task)["jobs"]) == 1
    assert core.store.get(task)["rounds"] == 1


def test_idempotency_key_cannot_change_payload(core):
    core.prepare("A", "repeat")
    with pytest.raises(DomainError) as exc:
        core.prepare("B", "repeat")
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_idempotent_completion_does_not_duplicate_history(core):
    task = start(core)
    verify(core, task)
    core.human_attest(task, "review")
    revision = rev(core, task)
    a = core.complete(task, revision, "complete-once")
    b = core.complete(task, revision, "complete-once")
    assert a == b
    assert len(core.store.get(task)["completions"]) == 1


def test_old_revision_rejected(core):
    task = start(core)
    with pytest.raises(DomainError) as exc:
        core.progress(task, "test", 0, "old")
    assert exc.value.code == "REVISION_CONFLICT"


def test_persistence_across_core_instances(core):
    task = start(core)
    finish(core, task)
    restarted = Core(core.workspace)
    assert restarted.status(task)["current_completion_valid"]


def test_model_cannot_supply_approval_in_contract(core):
    with pytest.raises(ValidationError):
        Contract.model_validate(plan(approved=True, actor="human"))


def test_strict_requires_final_human_acceptance(core):
    task = start(core, plan(review_profile="strict"))
    verify(core, task)
    core.human_attest(task, "review")
    assert "STRICT_ACCEPTANCE_REQUIRED" in core.gate(task)["issues"]
    core.human_attest(task, "strict")
    assert core.gate(task)["eligible"]


def test_manual_criterion_requires_current_attestation(core):
    item = plan()
    item["criteria"].append({"id": "AC-2", "given": "UI visible", "when": "Inspect",
                             "then": "Text is readable", "method": "manual",
                             "manual_instructions": "Inspect at 200% zoom"})
    task = start(core, item)
    verify(core, task)
    core.human_attest(task, "review")
    assert core.gate(task)["criteria"]["AC-2"] == "NEEDS_REVIEW"
    core.human_attest(task, "criterion", ac_id="AC-2")
    assert core.gate(task)["eligible"]


def test_cannot_approve_automatic_criterion(core):
    task = start(core)
    verify(core, task)
    with pytest.raises(DomainError):
        core.human_attest(task, "criterion", ac_id="AC-1")


def test_one_started_task_per_workspace(core):
    start(core)
    second = new_task(core)
    core.approve_plan(second)
    with pytest.raises(DomainError) as exc:
        core.start(second, rev(core, second), "second")
    assert exc.value.code == "WORKSPACE_BUSY"


def test_completed_task_releases_workspace(core):
    first = start(core)
    finish(core, first)
    second = start(core)
    assert core.store.get(second)["state"] == "IN_PROGRESS"


def test_parent_not_automatically_completed(core):
    parent = new_task(core)
    child = start(core, plan(parent_id=parent))
    finish(core, child)
    assert core.store.get(parent)["state"] != "DONE"


def test_dependency_cycle_is_rejected(core):
    first = new_task(core)
    second = new_task(core, plan(dependencies=[first]))
    with pytest.raises(DomainError) as exc:
        core.submit_plan(first, plan(dependencies=[second]), rev(core, first), "cycle")
    assert exc.value.code == "DEPENDENCY_CYCLE"


def test_dod_cannot_be_skipped(core):
    settings = core.workspace.settings().model_dump(mode="json")
    settings["checks"]["build"] = {"argv": [__import__('sys').executable, "-c", "raise SystemExit(1)"],
                                    "kind": "process", "parser": "exit"}
    settings["dod_check_ids"] = ["build"]
    settings_update(core, **settings)
    task = start(core)
    verify(core, task)
    assert "DOD_NOT_PASSED:build" in core.gate(task)["issues"]


def test_artifact_tampering_invalidates(core):
    task = start(core)
    finish(core, task)
    e = core.store.get(task)["jobs"][-1]["evidence"][0]
    path = __import__('pathlib').Path(next(iter(e["artifact_hashes"])))
    path.write_text("altered")
    assert core.gate(task)["exit_code"] == 3


def test_deleted_artifact_invalidates(core):
    task = start(core)
    finish(core, task)
    e = core.store.get(task)["jobs"][-1]["evidence"][0]
    __import__('pathlib').Path(next(iter(e["artifact_hashes"]))).unlink()
    assert not core.gate(task)["eligible"]


def test_resume_retains_history(core):
    task = start(core)
    finish(core, task)
    (core.workspace.root / "app.py").write_text("VALUE = 1\n# another change\n")
    core.resume(task)
    assert len(core.store.get(task)["completions"]) == 1
    finish(core, task)
    assert len(core.store.get(task)["completions"]) == 2


def test_retro_failure_does_not_revoke_done(core):
    task = start(core)
    finish(core, task)
    with pytest.raises(ValidationError):
        core.propose_improvement(task, {}, rev(core, task), "bad-retro")
    assert core.store.get(task)["state"] == "DONE"
    assert core.store.get(task)["retrospective_status"] == "pending"


def test_unknown_cost_is_null(core):
    task = start(core)
    verify(core, task)
    data = core.status(task)
    assert data["host_cost_usd"] is None
    assert data["task"]["jobs"][-1]["evidence"][0]["cost_usd"] is None


def test_report_exposes_gate_and_unknown_cost(core):
    task = start(core)
    text = render(core, task)
    assert "NOT_RUN" in text and "unknown" in text


def proposal(core, task):
    evidence = core.store.get(task)["jobs"][-1]["evidence"][0]
    return {"title": "Check persistence", "hypothesis": "Independent reload detects missing writes",
            "proposed_action": "Suggest reload validation", "task_kinds": ["feature"],
            "path_globs": ["app.py"], "evidence_ids": [evidence["id"]],
            "positive_example": "A missing write", "negative_example": "A docs-only change",
            "action_kind": "verification_candidate"}


def test_proposed_rules_not_applied(core):
    task = start(core)
    verify(core, task)
    result = core.propose_improvement(task, proposal(core, task), rev(core, task), "rule")
    assert result["rule_status"] == "PROPOSED"
    assert core.rule_candidates("feature", ["app.py"]) == []


def test_approved_rule_only_suggested_in_scope(core):
    task = start(core)
    verify(core, task)
    result = core.propose_improvement(task, proposal(core, task), rev(core, task), "rule")
    core.approve_rule(result["rule_id"])
    assert len(core.rule_candidates("feature", ["app.py"])) == 1
    assert core.rule_candidates("docs", ["app.py"]) == []
    assert core.rule_candidates("feature", ["other.py"]) == []
    core.approve_rule(result["rule_id"], retire=True)
    assert core.rule_candidates("feature", ["app.py"]) == []


def test_rule_must_reference_real_evidence(core):
    task = start(core)
    verify(core, task)
    value = proposal(core, task)
    value["evidence_ids"] = ["imaginary"]
    with pytest.raises(DomainError):
        core.propose_improvement(task, value, rev(core, task), "fake")


def test_rule_cannot_gain_permissions(core):
    task = start(core)
    verify(core, task)
    value = proposal(core, task)
    value["action_kind"] = "disable_security"
    with pytest.raises(ValidationError):
        core.propose_improvement(task, value, rev(core, task), "unsafe")


def test_cancel_never_becomes_done(core):
    task = start(core)
    core.cancel(task, "User stopped", rev(core, task), "cancel")
    assert core.complete(task, rev(core, task), "try-complete")["state"] == "CANCELLED"


def test_specification_source_changed_requires_new_plan(core):
    path = core.workspace.root / "spec.md"
    path.write_text("Initial behavior")
    content = plan(source_refs=["spec.md"])
    task = new_task(core, content)
    core.approve_plan(task)
    path.write_text("New behavior")
    with pytest.raises(DomainError, match="approval"):
        core.start(task, rev(core, task), "source-changed")
    before = core.store.get(task)["contract_hash"]
    core.submit_plan(task, content, rev(core, task), "source-new-plan")
    assert core.store.get(task)["contract_hash"] != before
    assert core.store.get(task)["contract_version"] == 2


def test_source_cannot_change_between_submission_and_approval(core):
    path = core.workspace.root / "spec.md"
    path.write_text("Original")
    task = new_task(core, plan(source_refs=["spec.md"]))
    path.write_text("Changed")
    with pytest.raises(DomainError, match="Resubmit"):
        core.approve_plan(task)
