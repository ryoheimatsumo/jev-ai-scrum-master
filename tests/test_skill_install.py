import json
from pathlib import Path

import pytest

from jev_sm.common import DomainError, canonical
from jev_sm.skill_install import MANIFEST, bundled_files, hashes, install


def test_bundle_is_short_and_contains_all_references():
    bundle = bundled_files()
    body = bundle["SKILL.md"].decode()
    assert len(body.splitlines()) < 80
    assert "MCP is optional" in body and "CLI" in body
    assert "sm_prepare_task" not in body
    for name in ["planning", "runtime", "verification", "retrospective", "cli", "optional-mcp"]:
        assert f"references/{name}.md" in bundle
    assert json.loads(bundle["assets/plan.example.json"])["criteria"]


def test_bundled_skill_describes_chat_plan_approval_without_terminal_only_claim():
    bundle = bundled_files()
    skill = bundle["SKILL.md"].decode()
    planning = bundle["references/planning.md"].decode()
    cli = bundle["references/cli.md"].decode()
    setup = bundle["references/setup.md"].decode()
    command = "approve plan TASK [--task SAME_OTHER] --delegated-chat --expected-hash HASH"
    assert command in skill and command in cli
    assert "approve plan TASK [--task SAME_OTHER_TASK] --delegated-chat --expected-hash HASH" in planning
    assert "Do not use raw JSON/YAML as the review artifact" in planning
    assert "the agent may use the delegated plan approval command" in setup
    assert "a Core receipt in this version" not in cli


def test_discoverable_mirror_equals_packaged_source():
    mirror = Path(__file__).resolve().parents[1] / "skills/jev-scrum-master"
    assert bundled_files() == {p.relative_to(mirror).as_posix(): p.read_bytes()
                               for p in mirror.rglob("*") if p.is_file() and "runtime" not in p.relative_to(mirror).parts
                               and "__pycache__" not in p.parts}


@pytest.mark.parametrize("host,folder", [("codex", ".agents"), ("claude", ".claude")])
def test_preview_then_install_preserves_user_instructions(core, host, folder):
    root = core.workspace.root
    (root / "AGENTS.md").write_text("user agents instructions")
    (root / "CLAUDE.md").write_text("user claude instructions")
    preview = install(root, host, "project")
    target = root / folder / "skills/jev-scrum-master"
    assert preview["preview"] and not target.exists()
    assert install(root, host, "project", write=True)["written"]
    assert (target / "SKILL.md").is_file()
    assert (root / "AGENTS.md").read_text() == "user agents instructions"
    assert (root / "CLAUDE.md").read_text() == "user claude instructions"
    assert not (root / ".mcp.json").exists()
    assert not (root / ".claude/settings.json").exists()
    assert not install(root, host, "project", write=True)["written"]


def test_user_scope_does_not_require_a_repo(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = install(tmp_path / "not-a-repo", "codex", "user", write=True, home=home)
    assert result["written"] and str(home) in result["target"]


def test_existing_unmanaged_skill_never_overwritten(core):
    target = core.workspace.root / ".agents/skills/jev-scrum-master"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom instructions")
    with pytest.raises(DomainError, match="unmanaged"):
        install(core.workspace.root, "codex", "project", write=True, update=True)
    assert (target / "SKILL.md").read_text() == "custom instructions"


@pytest.mark.parametrize("change", ["edit", "extra_file", "delete"])
def test_modified_managed_install_not_overwritten(core, change):
    result = install(core.workspace.root, "codex", "project", write=True)
    target = Path(result["target"])
    if change == "edit":
        (target / "SKILL.md").write_text("local customizations")
    elif change == "extra_file":
        (target / "local-note.md").write_text("keep this")
    else:
        (target / "references/cli.md").unlink()
    with pytest.raises(DomainError, match="modified"):
        install(core.workspace.root, "codex", "project", write=True, update=True)


def test_clean_managed_old_install_requires_explicit_update(core):
    result = install(core.workspace.root, "claude", "project", write=True)
    target = Path(result["target"])
    bundle = bundled_files()
    bundle["SKILL.md"] = b"old managed instructions"
    (target / "SKILL.md").write_bytes(bundle["SKILL.md"])
    (target / MANIFEST).write_text(canonical({"owner": "jev-ai-scrum-master", "schema_version": 1,
                                           "version": "old-test", "files": hashes(bundle)}))
    assert install(core.workspace.root, "claude", "project")["status"] == "update_available"
    with pytest.raises(DomainError, match="--update"):
        install(core.workspace.root, "claude", "project", write=True)
    assert install(core.workspace.root, "claude", "project", write=True, update=True)["written"]
    assert (target / "SKILL.md").read_bytes() == bundled_files()["SKILL.md"]


def test_symlink_parent_rejected_before_any_write(core, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (core.workspace.root / ".agents").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DomainError, match="symlink"):
        install(core.workspace.root, "codex", "project", write=True)
    assert not list(outside.iterdir())


def test_symlink_inside_existing_skill_rejected(core, tmp_path):
    result = install(core.workspace.root, "codex", "project", write=True)
    target = Path(result["target"])
    (target / "escape").symlink_to(tmp_path)
    with pytest.raises(DomainError, match="symlink"):
        install(core.workspace.root, "codex", "project", write=True, update=True)


def test_cooperative_install_lock_prevents_competing_write(core):
    target = core.workspace.root / ".agents/skills"
    target.mkdir(parents=True)
    (target / ".jev-scrum-master.install.lock").write_text("fixture lock")
    with pytest.raises(DomainError, match="lock"):
        install(core.workspace.root, "codex", "project", write=True)
    assert not (target / "jev-scrum-master").exists()
