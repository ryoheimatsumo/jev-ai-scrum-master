"""Human confirmation is deliberately absent from the MCP surface."""
from __future__ import annotations

import getpass
import re
import uuid
from typing import Protocol

from .common import DomainError, canonical, now


class Authority(Protocol):
    def confirm(self, kind: str, content_hash: str, details: dict) -> dict: ...


class TerminalAuthority:
    def confirm(self, kind: str, content_hash: str, details: dict) -> dict:
        try:
            with open("/dev/tty", "r+", encoding="utf-8", buffering=1) as tty:
                if not tty.isatty():
                    raise OSError("No terminal")
                tty.write("\n" + _readable_details(kind, details) + f"\nExact SHA256: {content_hash}\n")
                expected = f"approve {content_hash[:12]}"
                tty.write(f"Type exactly '{expected}' to approve (anything else cancels): ")
                answer = tty.readline().strip()
        except OSError as exc:
            raise DomainError("HUMAN_CONFIRMATION_REQUIRED", "Run this command in your own terminal") from exc
        if answer != expected:
            raise DomainError("APPROVAL_CANCELLED", "No approval was recorded")
        return {"id": "approval-" + uuid.uuid4().hex, "kind": kind,
                "content_hash": content_hash, "actor": getpass.getuser(),
                "source": "local_tty", "at": now()}


def _safe(value: object) -> str:
    """Keep untrusted plan text readable without allowing terminal control codes."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]", " ", str(value)).strip()


def _readable_details(kind: str, details: dict) -> str:
    lines = [f"Human approval: {_safe(kind)}"]

    def contract_block(label: str, index: int, plan: dict) -> None:
        contract = plan.get("contract", {})
        lines.extend([f"\n{label} {index} (task {_safe(plan.get('task_id', ''))})",
                      f"Title: {_safe(contract.get('title', ''))}",
                      f"Goal: {_safe(contract.get('goal', ''))}", "Scope:"])
        lines.extend(f"  - {_safe(item)}" for item in contract.get("in_scope", []))
        if contract.get("out_of_scope"):
            lines.append("Out of scope:")
            lines.extend(f"  - {_safe(item)}" for item in contract["out_of_scope"])
        lines.append("Criteria (Given / When / Then):")
        for criterion in contract.get("criteria", []):
            lines.append(f"  - {_safe(criterion.get('id'))}: Given {_safe(criterion.get('given'))}; "
                         f"When {_safe(criterion.get('when'))}; Then {_safe(criterion.get('then'))}")
            lines.append(f"    checks: {_safe(', '.join(criterion.get('check_ids', [])) or 'manual')}; "
                         f"case IDs: {_safe(criterion.get('case_ids', {}))}")
        lines.append(f"Contract version: {_safe(plan.get('contract_version'))}; contract hash: {_safe(plan.get('contract_hash'))}")
        lines.append(f"Kind: {_safe(contract.get('kind'))}; review profile: {_safe(contract.get('review_profile'))}")
        lines.append(f"Dependencies: {_safe(contract.get('dependencies', []))}; parent: {_safe(contract.get('parent_id'))}")
        lines.append(f"Source references: {_safe(contract.get('source_refs', []))}")

    if kind == "plan":
        for index, plan in enumerate(details.get("plans", []), 1):
            contract_block("Plan", index, plan)
    elif kind in {"review", "criterion", "strict"}:
        plans = details.get("plans") or [{"task_id": details.get("task_id"), "contract": details.get("contract", {})}]
        for index, plan in enumerate(plans, 1):
            contract_block("Review item", index, plan)
        if details.get("ac_id"):
            lines.append(f"Selected criterion: {_safe(details['ac_id'])}")
        for index, evidence in enumerate(details.get("evidence_sets") or [details.get("evidence", [])], 1):
            lines.append(f"Evidence for selected task {index}:")
            lines.extend(f"  - {_safe(item.get('check_id'))}: {_safe(item.get('outcome'))}; case IDs: {_safe([c.get('id') for c in item.get('cases', [])])}" for item in evidence)
        for index, gate in enumerate(details.get("gates") or [details.get("gate", {})], 1):
            lines.append(f"Gate for selected task {index}: criteria {_safe(gate.get('criteria', {}))}; issues {_safe(', '.join(gate.get('issues', [])) or 'none')}")
        lines.append(f"Evidence binding: {_safe(details.get('binding'))}")
        lines.append(f"Instructions: {_safe(details.get('instructions'))}")
    elif kind == "protected":
        lines.append(f"Protected input hash: {_safe(details.get('protected_hash'))}")
        lines.append("Protected files and hashes:")
        lines.extend(f"  - {_safe(path)}: {_safe(value)}" for path, value in details.get("files", {}).items())
        lines.append(f"Warning: {_safe(details.get('warning'))}")
    elif kind == "resume":
        lines.extend([f"Task: {_safe(details.get('task_id'))}", f"Revision: {_safe(details.get('revision'))}", f"Action: {_safe(details.get('action'))}", f"Gate: {_safe(details.get('gate'))}"])
    elif kind in {"approve_rule", "retire_rule"}:
        lines.append("Rule decision:")
        lines.extend(f"  - {_safe(name)}: {_safe(value)}" for name, value in details.items())
    else:
        lines.append("Details:")
        lines.extend(f"  - {_safe(name)}: {_safe(value)}" for name, value in details.items())

    for name in ("config_hash", "input_hash", "protected_hash"):
        if name in details:
            label = {"config_hash": "Checks/config hash", "input_hash": "Input hash", "protected_hash": "Protected input hash"}[name]
            lines.append(f"{label}: {_safe(details[name])}")
    settings = details.get("settings", {})
    if settings:
        lines.append("Registered checks:")
        for check_id, check in settings.get("checks", {}).items():
            lines.append(f"  - {_safe(check_id)}: {_safe(check.get('kind'))}, parser {_safe(check.get('parser'))}, argv {_safe(check.get('argv'))}, report {_safe(check.get('report_path'))}, timeout {_safe(check.get('timeout_seconds'))}s, minimum cases {_safe(check.get('min_tests'))}")
        lines.append(f"Required DoD checks: {_safe(settings.get('dod_check_ids', []))}")
    return "\n".join(lines)
