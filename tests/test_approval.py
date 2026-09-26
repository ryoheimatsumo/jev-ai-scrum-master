from jev_sm.approval import _readable_details


def test_readable_details_includes_material_for_each_human_approval_kind():
    contract = {"title": "Safe change", "goal": "Keep behavior", "in_scope": ["core"],
                "criteria": [{"id": "AC-1", "given": "input", "when": "run", "then": "passes"}]}
    for kind in ("review", "criterion", "strict"):
        text = _readable_details(kind, {"kind": kind, "contract": contract, "ac_id": "AC-1",
                                        "binding": "b" * 64, "gate": {"criteria": {"AC-1": "PASS"}, "issues": []},
                                        "evidence": [{"check_id": "unit", "outcome": "PASS",
                                                      "cases": [{"id": "case-1"}]}],
                                        "instructions": "Inspect behavior"})
        assert "Safe change" in text and "AC-1" in text and "case-1" in text


def test_group_review_details_show_each_task_gate_and_evidence():
    contract = {"title": "Safe change", "goal": "Keep behavior", "in_scope": ["core"],
                "criteria": [{"id": "AC-1", "given": "input", "when": "run", "then": "passes"}]}
    text = _readable_details("review", {"kind": "review", "plans": [
        {"task_id": "task-a", "contract": contract},
        {"task_id": "task-b", "contract": contract}],
        "gates": [{"criteria": {"AC-1": "PASS"}, "issues": []},
                  {"criteria": {"AC-1": "NEEDS_REVIEW"}, "issues": ["INDEPENDENT_REVIEW_REQUIRED"]}],
        "evidence_sets": [[{"check_id": "unit-a", "outcome": "PASS", "cases": [{"id": "case-a"}]}],
                          [{"check_id": "unit-b", "outcome": "PASS", "cases": [{"id": "case-b"}]}]]})
    assert "task-a" in text and "task-b" in text
    assert "unit-a" in text and "unit-b" in text and "case-a" in text and "case-b" in text
    assert "INDEPENDENT_REVIEW_REQUIRED" in text


def test_readable_details_includes_protected_material_and_removes_controls():
    text = _readable_details("protected", {"protected_hash": "h" * 64,
                                             "files": {"tests/test.py": "f" * 64},
                                             "warning": "Review\x1b[31m assertions"})
    assert "tests/test.py" in text and "Review [31m assertions" in text
    assert "\x1b" not in text


def test_readable_details_covers_plan_resume_and_rule_material():
    plan_text = _readable_details("plan", {"plans": [{"task_id": "task-a", "contract_version": 2,
        "contract_hash": "c" * 64, "contract": {"title": "Feature", "goal": "Ship it",
        "kind": "feature", "review_profile": "standard", "in_scope": ["core"],
        "dependencies": ["task-parent"], "parent_id": "task-root", "source_refs": ["spec.md"],
        "criteria": []}}], "config_hash": "g" * 64, "input_hash": "i" * 64,
        "protected_hash": "p" * 64})
    assert "Kind: feature" in plan_text and "task-parent" in plan_text and "spec.md" in plan_text
    assert "Checks/config hash" in plan_text and "Protected input hash" in plan_text
    text = _readable_details("resume", {"task_id": "task-a", "action": "inspect"})
    assert "task-a" in text and "inspect" in text and "Title:" not in text
    for kind in ("approve_rule", "retire_rule"):
        text = _readable_details(kind, {"task_id": "task-a", "action": "inspect", "rule_id": "rule-a"})
        assert "task-a" in text and "rule-a" in text and "Title:" not in text
