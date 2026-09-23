"""Skill-first CLI. JSON by default; human approval remains a separate TTY action."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

import yaml
from pydantic import ValidationError

from . import __version__
from .common import DomainError, canonical, redact
from .core import Core
from .judgment import Assistant
from .models import ContextRequest, Contract, Improvement, Settings
from .report import render
from .workspace import Workspace

MAX_INPUT_BYTES = 1_048_576


def read_input(source: str, *, limit: int = MAX_INPUT_BYTES) -> str:
    """Bound file/stdin input. Do not echo input or exception values on errors."""
    if source == "-":
        text = sys.stdin.read(limit + 1)
    else:
        path = Path(source)
        if not path.is_file():
            raise DomainError("INVALID_INPUT", "Input must be a regular UTF-8 file or '-' for stdin")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise DomainError("INPUT_TOO_LARGE", "Input exceeds the byte limit")
        text = data.decode("utf-8")
    if len(text.encode("utf-8")) > limit:
        raise DomainError("INPUT_TOO_LARGE", "Input exceeds the byte limit")
    return text


def read_json(source: str) -> dict:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-finite JSON number")

    try:
        result = json.loads(read_input(source), object_pairs_hook=unique_pairs,
                            parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise DomainError("INVALID_INPUT", "Provide valid UTF-8 JSON with unique keys and finite numbers") from exc
    if not isinstance(result, dict):
        raise DomainError("INVALID_INPUT", "Top-level JSON must be an object")
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jev-sm")
    p.add_argument("--repo", type=Path, default=Path.cwd(), help="Git worktree root")
    p.add_argument("--state-dir", type=Path, help="State parent outside the repository")
    p.add_argument("--version", action="version", version=__version__)
    subs = p.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init", help="Preview config as JSON; writes only with --write")
    init.add_argument("--write", action="store_true")
    init.add_argument("--yaml", action="store_true", help="Legacy YAML display instead of JSON")
    subs.add_parser("doctor")
    subs.add_parser("serve", help="Optional stdio MCP adapter; requires the mcp extra")
    schema = subs.add_parser("schema", help="Read a schema without creating workspace state")
    schema.add_argument("kind", choices=["contract", "context", "improvement", "settings"])
    skills = subs.add_parser("skill", help="Install reviewed Skill resources; no MCP settings changes")
    skill_sub = skills.add_subparsers(dest="skill_action", required=True)
    for action in ("install", "status"):
        item = skill_sub.add_parser(action)
        item.add_argument("--host", choices=["codex", "claude"], required=True)
        item.add_argument("--scope", choices=["project", "user"], default="project")
        if action == "install":
            item.add_argument("--write", action="store_true", help="Write after reviewing the preview")
            item.add_argument("--update", action="store_true", help="Update only an unchanged managed install")
    tasks = subs.add_parser("tasks", help="List resumable tasks without logs or manifests")
    tasks.add_argument("--limit", type=int, default=20)
    tasks.add_argument("--offset", type=int, default=0)
    prepare = subs.add_parser("prepare")
    prepare.add_argument("request", nargs="?")
    prepare.add_argument("--request-file", help="UTF-8 request file, or '-' for stdin")
    prepare.add_argument("--source", action="append", default=[])
    prepare.add_argument("--include-schema", action="store_true")
    prepare.add_argument("--key")
    submit = subs.add_parser("submit-plan")
    submit.add_argument("task_id")
    submit.add_argument("plan", help="JSON file, or '-' for stdin")
    submit.add_argument("--revision", type=int, required=True)
    submit.add_argument("--key")
    for name in ("start", "verify", "complete"):
        command = subs.add_parser(name)
        command.add_argument("task_id")
        command.add_argument("--revision", type=int, required=True)
        command.add_argument("--key")
    status = subs.add_parser("status", help="Compact by default; full state is opt-in")
    status.add_argument("task_id")
    status.add_argument("--full", action="store_true")
    status.add_argument("--job-id")
    for name in ("gate", "report", "resume"):
        command = subs.add_parser(name)
        command.add_argument("task_id")
    progress = subs.add_parser("progress")
    progress.add_argument("task_id")
    progress.add_argument("observation")
    progress.add_argument("--revision", type=int, required=True)
    progress.add_argument("--key")
    cancel = subs.add_parser("cancel")
    cancel.add_argument("task_id")
    cancel.add_argument("--reason", required=True)
    cancel.add_argument("--revision", type=int, required=True)
    cancel.add_argument("--key")
    approve = subs.add_parser("approve", help="Human only; never run or simulate approval on their behalf")
    approve.add_argument("kind", choices=["plan", "review", "protected", "criterion", "strict"])
    approve.add_argument("task_id")
    approve.add_argument("--version", type=int)
    approve.add_argument("--ac")
    rules = subs.add_parser("rule")
    rule_sub = rules.add_subparsers(dest="rule_action", required=True)
    for name in ("approve", "retire"):
        cmd = rule_sub.add_parser(name)
        cmd.add_argument("rule_id")
    listing = rule_sub.add_parser("list")
    listing.add_argument("--task-id")
    candidates = rule_sub.add_parser("candidates")
    candidates.add_argument("--kind", required=True)
    candidates.add_argument("--path", action="append", required=True)
    propose = subs.add_parser("propose-improvement")
    propose.add_argument("task_id")
    propose.add_argument("proposal", help="JSON file, or '-' for stdin")
    propose.add_argument("--revision", type=int, required=True)
    propose.add_argument("--key")
    evidence = subs.add_parser("evidence", help="Fetch a registered, hash-verified artifact by ID")
    evidence.add_argument("task_id")
    evidence.add_argument("evidence_id")
    evidence.add_argument("--artifact")
    evidence.add_argument("--offset", type=int, default=0)
    evidence.add_argument("--max-chars", type=int, default=6000)
    context = subs.add_parser("select-context", help="Filter before inference; originals must remain available")
    context.add_argument("task_id")
    context.add_argument("--input", required=True, help="ContextRequest JSON file or '-' for stdin")
    advise = subs.add_parser("advise")
    advise.add_argument("kind", choices=["readiness", "playbook", "evidence"])
    advise.add_argument("task_id")
    observation = advise.add_mutually_exclusive_group()
    observation.add_argument("--observation", default="")
    observation.add_argument("--observation-file", help="UTF-8 file or '-' for stdin")
    cache = subs.add_parser("cache", help="Workspace-local advisory cache; never acceptance evidence")
    cache_sub = cache.add_subparsers(dest="cache_action", required=True)
    cache_sub.add_parser("stats")
    clear = cache_sub.add_parser("clear")
    clear.add_argument("--write", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    core = None
    try:
        command = args.command
        if command == "schema":
            model = {"contract": Contract, "context": ContextRequest,
                     "improvement": Improvement, "settings": Settings}[args.kind]
            print(canonical(model.model_json_schema()))
            return 0
        if command == "skill":
            from .skill_install import install
            result = install(args.repo, args.host, args.scope,
                             write=getattr(args, "write", False), update=getattr(args, "update", False))
            print(canonical(result))
            return 0
        workspace = Workspace(args.repo, args.state_dir)
        if command == "init":
            config = Settings().model_dump(mode="json")
            if workspace.config_path.exists():
                raise DomainError("CONFIG_EXISTS", "Existing configuration is never overwritten")
            text = yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
            if args.write:
                workspace.config_path.parent.mkdir(parents=True, exist_ok=True)
                with workspace.config_path.open("x", encoding="utf-8") as target:
                    target.write(text)
            if args.yaml:
                print(text, end="")
            else:
                print(canonical({"config": config, "path": str(workspace.config_path),
                                 "written": args.write, "next_action": "register_checks_then_approve_plan"
                                 if args.write else "review_then_rerun_with_write"}))
            return 0
        if command == "doctor":
            cfg = workspace.settings() if workspace.config_path.exists() else None
            print(canonical({"version": __version__, "repo": str(workspace.root),
                "state_dir": str(workspace.state_dir), "configured": cfg is not None,
                "primary_interface": "skill+cli", "mcp_required": False,
                "mcp_sdk_installed": importlib.util.find_spec("mcp") is not None,
                "jev_sdk_installed": importlib.util.find_spec("typesafe_sdk") is not None,
                "jev_key_configured": bool(os.environ.get("TYPESAFE_API_KEY")),
                "external_jev_enabled": bool(cfg and cfg.jev_enabled),
                "cache": {"backend": "sqlite", "ttl_seconds": cfg.jev_cache_ttl_seconds if cfg else None},
                "host_runtime_smoke_tested": False,
                "sandbox": "copy isolation and credential minimization; not an OS sandbox"}))
            return 0
        core = Core(workspace)
        key = getattr(args, "key", None) or "cli-" + uuid.uuid4().hex
        if command == "serve":
            from .mcp_server import create_server
            create_server(core).run(transport="stdio")
            return 0
        if command == "tasks":
            if not 1 <= args.limit <= 100 or args.offset < 0:
                raise DomainError("INVALID_RANGE", "Use a limit of 1..100 and a nonnegative offset")
            all_tasks = core.store.all_tasks()[::-1]
            end = args.offset + args.limit
            result = {"tasks": [{k: t[k] for k in ("id", "request", "state", "revision", "updated_at")}
                                for t in all_tasks[args.offset:end]],
                      "total": len(all_tasks), "next_offset": end if end < len(all_tasks) else None,
                      "note": "Historical states only; run status/gate before relying on completion"}
        elif command == "prepare":
            if bool(args.request) == bool(args.request_file):
                raise DomainError("INVALID_INPUT", "Provide either request text or --request-file, not both")
            request = read_input(args.request_file, limit=48000) if args.request_file else args.request
            result = core.prepare(request, key, args.source)
            if not args.include_schema:
                result.pop("plan_schema", None)
                result["schema_command"] = "jev-sm schema contract"
        elif command == "submit-plan":
            result = core.submit_plan(args.task_id, read_json(args.plan), args.revision, key)
        elif command == "start":
            result = core.start(args.task_id, args.revision, key)
        elif command == "verify":
            # Synchronous: the command owns the runner until finished. No unowned background job.
            result = core.verify(args.task_id, args.revision, key)
        elif command == "complete":
            result = core.complete(args.task_id, args.revision, key)
        elif command == "status":
            if args.full and args.job_id:
                raise DomainError("INVALID_INPUT", "Choose --full or --job-id, not both")
            result = core.status(args.task_id) if args.full else core.compact_status(args.task_id, args.job_id)
        elif command == "gate":
            result = core.gate(args.task_id)
            print(canonical(result))
            return result["exit_code"]
        elif command == "report":
            print(render(core, args.task_id))
            return 0
        elif command == "approve":
            if args.version is not None and args.version != core.store.get(args.task_id)["contract_version"]:
                raise DomainError("APPROVAL_STALE", "Requested version is not current")
            result = (core.approve_plan(args.task_id) if args.kind == "plan"
                      else core.human_attest(args.task_id, args.kind, ac_id=args.ac))
        elif command == "resume":
            result = core.resume(args.task_id)
        elif command == "progress":
            result = core.progress(args.task_id, args.observation, args.revision, key)
        elif command == "cancel":
            result = core.cancel(args.task_id, args.reason, args.revision, key)
        elif command == "rule":
            if args.rule_action == "list":
                with core.store.connect() as con:
                    values = [json.loads(r[0]) for r in con.execute("SELECT data FROM rules ORDER BY rowid")]
                result = {"rules": [r for r in values if not args.task_id or r["task_id"] == args.task_id]}
            elif args.rule_action == "candidates":
                result = {"candidates": core.rule_candidates(args.kind, args.path),
                          "note": "Candidates only; include in a reviewed plan before applying"}
            else:
                result = core.approve_rule(args.rule_id, retire=args.rule_action == "retire")
        elif command == "propose-improvement":
            result = core.propose_improvement(args.task_id, read_json(args.proposal), args.revision, key)
        elif command == "evidence":
            result = core.evidence_detail(args.task_id, args.evidence_id, args.artifact,
                                          args.offset, args.max_chars)
        elif command == "select-context":
            request = ContextRequest.model_validate(read_json(args.input))
            result = Assistant(core).select_context(args.task_id, request.query,
                [s.model_dump() for s in request.snippets], request.max_chars)
        elif command == "advise":
            assistant = Assistant(core)
            if args.kind == "readiness":
                result = assistant.readiness(args.task_id)
            elif args.kind == "evidence":
                result = assistant.map_evidence(args.task_id)
            else:
                observation = read_input(args.observation_file) if args.observation_file else args.observation
                result = assistant.recommend_playbook(args.task_id, observation)
        elif command == "cache":
            if args.cache_action == "stats":
                result = core.store.cache_stats()
            elif args.write:
                result = core.store.clear_judgment_cache()
            else:
                result = core.store.cache_stats() | {"preview": True, "next_action": "rerun_with_write"}
        else:
            raise DomainError("UNKNOWN_COMMAND", "Unsupported command")
        print(canonical(result))
        return 0
    except DomainError as exc:
        print(canonical({"error": exc.as_dict()}), file=sys.stderr)
        return 4
    except ValidationError:
        print(canonical({"error": {"code": "INVALID_INPUT",
            "message": "Input failed schema validation; use jev-sm schema to inspect the expected shape"}}), file=sys.stderr)
        return 4
    except (ValueError, OSError, RecursionError) as exc:
        print(canonical({"error": {"code": "INVALID_INPUT", "message": redact(str(exc))}}), file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print(canonical({"error": {"code": "INTERRUPTED", "message": "Interrupted; inspect status before resuming"}}), file=sys.stderr)
        return 130
    finally:
        if core is not None:
            core.processes.stop_all()
