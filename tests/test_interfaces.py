import asyncio
import inspect
import json
import os
import subprocess
import sys
import uuid

import pytest

from jev_sm.cli import main
from jev_sm.common import DomainError
from jev_sm.mcp_server import create_server
from conftest import new_task, rev


class RegistrationServer:
    """API registration fake, NOT an MCP wire-protocol implementation."""
    def __init__(self, name, **kwargs):
        self.name, self.functions, self.kwargs = name, {}, kwargs
    def tool(self):
        def register(func):
            self.functions[func.__name__] = func
            return func
        return register


def test_mcp_tools_registered_without_approval_surface(core):
    server = create_server(core, server_class=RegistrationServer)
    assert len(server.functions) == 13
    assert "sm_request_completion" in server.functions
    assert not any("approve" in name for name in server.functions)
    signature = inspect.signature(server.functions["sm_request_completion"])
    assert "done" not in signature.parameters and "actor" not in signature.parameters


def test_mcp_prepare_and_status_via_registered_tools(core):
    server = create_server(core, server_class=RegistrationServer)
    async def exercise():
        created = await server.functions["sm_prepare_task"]("Build a feature", "mcp-create")
        result = await server.functions["sm_get_status"](created["task_id"])
        assert result["task"]["state"] == "PLANNING"
        assert not result["gate"]["eligible"]
    asyncio.run(exercise())


def test_mcp_start_without_approval_is_tool_error(core):
    task = new_task(core)
    server = create_server(core, server_class=RegistrationServer)
    with pytest.raises(ValueError, match="APPROVAL_REQUIRED"):
        asyncio.run(server.functions["sm_start_task"](task, rev(core, task), "mcp-no-approval"))


def test_mcp_model_supplied_actor_rejected(core):
    server = create_server(core, server_class=RegistrationServer)
    with pytest.raises(TypeError):
        asyncio.run(server.functions["sm_prepare_task"]("x", "key", actor="human"))


def test_cli_gate_exit_two_when_unverified(core, capsys):
    task = new_task(core)
    result = main(["--repo", str(core.workspace.root), "--state-dir", str(core.workspace.state_dir.parent), "gate", task])
    assert result == 2
    assert not json.loads(capsys.readouterr().out)["eligible"]


def test_cli_init_never_overwrites(core, capsys):
    before = core.workspace.config_path.read_bytes()
    result = main(["--repo", str(core.workspace.root), "init", "--write"])
    assert result == 4
    assert before == core.workspace.config_path.read_bytes()


def test_cli_doctor_is_honest_about_host_testing(core, capsys):
    assert main(["--repo", str(core.workspace.root), "doctor"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["host_runtime_smoke_tested"] is False
    assert not data["external_jev_enabled"]


def test_cli_does_not_accept_yes_approval(core):
    with pytest.raises(SystemExit):
        main(["--repo", str(core.workspace.root), "approve", "plan", "task-x", "--yes"])


@pytest.mark.sdk

def test_official_mcp_stdio_handshake(core):
    pytest.importorskip("mcp", reason="Official MCP SDK is not installed in this offline environment")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "jev_sm", "--repo", str(core.workspace.root), "--state-dir",
              str(core.workspace.state_dir.parent), "serve"],
        env={**os.environ, "PYTHONPATH": str(__import__('pathlib').Path(__file__).resolve().parents[1] / "src")})
    async def exercise():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                assert len(result.tools) == 13
                response = await session.call_tool("sm_prepare_task", {"request": "SDK smoke", "idempotency_key": "sdk-smoke"})
                assert not response.isError
    asyncio.run(asyncio.wait_for(exercise(), timeout=30))


@pytest.mark.sdk

def test_official_typesafe_question_schema():
    sdk = pytest.importorskip("typesafe_sdk", reason="Official TypeSafe SDK is not installed in this offline environment")
    question = sdk.Choice(instructions="Is this a test?", criteria={"YES": None, "NO": None})
    assert question is not None


@pytest.mark.live

def test_live_jev_opt_in(core):
    if os.environ.get("JEV_SM_RUN_LIVE") != "1" or not os.environ.get("TYPESAFE_API_KEY"):
        pytest.skip("Explicit JEV_SM_RUN_LIVE=1 and an API key are required; never run a paid API by default")
    pytest.importorskip("typesafe_sdk")
    from jev_sm.judgment import JevBackend, Question
    result = JevBackend(core.workspace.settings().jev_model).evaluate(
        {"message": "This is a harmless test fixture."},
        {"test": Question("noul", "Does `message` explicitly call itself a test fixture?")})
    assert 0 <= result["answers"]["test"]["noul"] <= 1


def test_compact_mcp_status_does_not_dump_manifests(core):
    from conftest import start, verify
    task = start(core)
    verify(core, task)
    result = core.compact_status(task)
    assert "baseline_manifest" not in result["task"]
    assert "snapshot" not in result["jobs"][0]
    assert result["jobs"][0]["evidence"][0]["id"]


def test_evidence_progressive_disclosure_and_integrity(core):
    from conftest import start, verify
    from pathlib import Path
    task = start(core)
    verify(core, task)
    ev = core.store.get(task)["jobs"][-1]["evidence"][0]
    meta = core.evidence_detail(task, ev["id"])
    name = next(a for a in meta["artifacts"] if a.endswith(".json"))
    page = core.evidence_detail(task, ev["id"], name, max_chars=10)
    assert len(page["text"]) == 10 and page["next_offset"] == 10
    with pytest.raises(DomainError, match="artifact"):
        core.evidence_detail(task, ev["id"], "../../etc/passwd")
    path = next(Path(p) for p in ev["artifact_hashes"] if p.endswith(name))
    path.write_text("altered")
    with pytest.raises(DomainError, match="integrity"):
        core.evidence_detail(task, ev["id"], name)
