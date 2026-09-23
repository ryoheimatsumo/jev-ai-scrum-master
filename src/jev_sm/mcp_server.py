"""Official FastMCP adapter. No approval, arbitrary shell, or PASS-setting tools."""
from __future__ import annotations

import asyncio
import functools
from contextlib import asynccontextmanager

from pydantic import ValidationError

from .common import DomainError, canonical
from .judgment import Assistant


def create_server(core, *, server_class=None):
    # server_class is dependency injection for local registration tests only.
    if server_class is None:
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError as exc:
            raise DomainError("SDK_UNAVAILABLE", 'Install with: pip install -e ".[mcp]"') from exc
        server_class = FastMCP
    jobs: set[asyncio.Task] = set()
    assistant = Assistant(core)

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield {}
        finally:
            core.processes.stop_all()
            if jobs:
                await asyncio.gather(*list(jobs), return_exceptions=True)

    server = server_class("Jev AI Scrum Master", lifespan=lifespan)

    def tool(func):
        @functools.wraps(func)
        async def guarded(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except DomainError as exc:
                # FastMCP converts an exception into a protocol tool error.
                raise ValueError(canonical(exc.as_dict())) from exc
            except ValidationError as exc:
                # Do not echo rejected input (which may contain secrets).
                raise ValueError(canonical({"code": "INVALID_INPUT", "message": "Input schema validation failed"})) from exc
        return server.tool()(guarded)

    @tool
    async def sm_prepare_task(request: str, idempotency_key: str, source_refs: list[str] | None = None) -> dict:
        """Create PLANNING. The host prepares a structured plan; it cannot approve it."""
        return await asyncio.to_thread(core.prepare, request, idempotency_key, source_refs)

    @tool
    async def sm_submit_plan(task_id: str, plan: dict, expected_revision: int, idempotency_key: str) -> dict:
        """Store a contract revision and return the hash requiring human approval."""
        return await asyncio.to_thread(core.submit_plan, task_id, plan, expected_revision, idempotency_key)

    @tool
    async def sm_start_task(task_id: str, expected_revision: int, idempotency_key: str) -> dict:
        """Start only an approved task and reserve its worktree."""
        return await asyncio.to_thread(core.start, task_id, expected_revision, idempotency_key)

    @tool
    async def sm_get_status(task_id: str, job_id: str | None = None) -> dict:
        """Return current gate state. Historical DONE is not current proof."""
        return await asyncio.to_thread(core.compact_status, task_id, job_id)

    @tool
    async def sm_get_evidence(task_id: str, evidence_id: str, artifact: str | None = None,
                              offset: int = 0, max_chars: int = 6000) -> dict:
        """Progressively read integrity-checked evidence. Never accepts a filesystem path."""
        return await asyncio.to_thread(core.evidence_detail, task_id, evidence_id, artifact, offset, max_chars)

    @tool
    async def sm_report_progress(task_id: str, observation: str, expected_revision: int, idempotency_key: str) -> dict:
        """Record an untrusted progress claim without updating acceptance status."""
        return await asyncio.to_thread(core.progress, task_id, observation, expected_revision, idempotency_key)

    @tool
    async def sm_verify_acceptance(task_id: str, expected_revision: int, idempotency_key: str,
                                   approved_check_ids: list[str] | None = None) -> dict:
        """Execute the complete approved check set, return a job id, then poll status."""
        result = await asyncio.to_thread(core.begin_verification, task_id, expected_revision,
                                         idempotency_key, approved_check_ids)
        job = asyncio.create_task(asyncio.to_thread(core.execute_verification, task_id, result["job_id"]))
        jobs.add(job)
        def finished(task):
            jobs.discard(task)
            if not task.cancelled():
                task.exception()  # Retrieve an exception; core records execution failures.
        job.add_done_callback(finished)
        return result

    @tool
    async def sm_request_completion(task_id: str, expected_revision: int, idempotency_key: str) -> dict:
        """Compute completion from current evidence; no done or override input exists."""
        return await asyncio.to_thread(core.complete, task_id, expected_revision, idempotency_key)

    @tool
    async def sm_propose_improvement(task_id: str, proposal: dict, expected_revision: int, idempotency_key: str) -> dict:
        """Create a proposed, evidence-linked planning hint. Does not adopt or execute it."""
        return await asyncio.to_thread(core.propose_improvement, task_id, proposal, expected_revision, idempotency_key)

    @tool
    async def sm_assess_readiness(task_id: str) -> dict:
        """Batch independent Jev readiness questions; advisory and consent-gated."""
        return await asyncio.to_thread(assistant.readiness, task_id)

    @tool
    async def sm_recommend_playbook(task_id: str, observation: str) -> dict:
        """Suggest a bounded troubleshooting playbook or CONTINUE/UNKNOWN. No execution."""
        return await asyncio.to_thread(assistant.recommend_playbook, task_id, observation)

    @tool
    async def sm_select_context(task_id: str, query: str, snippets: list[dict], max_chars: int = 8000) -> dict:
        """Select relevant snippet IDs before host inference; retain mandatory/uncertain input."""
        return await asyncio.to_thread(assistant.select_context, task_id, query, snippets, max_chars)

    @tool
    async def sm_map_evidence(task_id: str) -> dict:
        """Map acceptance criteria to evidence candidates, never final PASS."""
        return await asyncio.to_thread(assistant.map_evidence, task_id)

    return server
