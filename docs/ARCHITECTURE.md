# Architecture

[日本語](ARCHITECTURE.ja.md)

This describes the implemented alpha, not every feature in the target specification.

## Responsibilities

| Component | Responsibility |
|---|---|
| Skill / host LLM | Discover project context; draft the plan, implementation, and improvement proposals. |
| CLI | Structured input/output for the host and explicit local human operations. |
| Core / SQLite | Contracts, revisions, approvals, bounded retries, evidence freshness, and DONE eligibility. |
| Runner | Execute registered checks against copied inputs and retain bounded reports. |
| Jev adapter | Optional, narrow advisory classifications with versioned questions and caching. |
| MCP adapter | Alternative access to the same Core, not a separate source of policy. |

The Skill is not an independent always-on agent. The host chooses when to invoke it. A Core
completion gate is not a hook over every host exit or Git operation. No automatic hooks are installed.

## Verification

A task has a versioned contract with acceptance criteria and check/case mappings. A person approves
the current contract. The agent implements; the Runner executes the approved checks. Test results
are tied to the contract and content snapshot, including dirty and untracked inputs.

Required zero-test, skipped, missing, stale, or unreviewed results do not qualify as completion.
A command's successful exit is not sufficient evidence for arbitrary behavior. Standard tasks
currently need a person to review the assertion/evidence mapping. Automatic read-only AI reviewers
are a target feature, not an implemented capability.

Jev may suggest relevant evidence but cannot change PASS, permission, or approval. The final gate
recomputes eligibility. DONE means this tool's current contract has been satisfied, not proof
that all possible bugs are absent.

## State and confidentiality

State is outside the project: on Linux beneath `XDG_STATE_HOME` (or `~/.local/state`), and on macOS
beneath `~/Library/Application Support`, in a workspace-specific `jev-sm` directory. Use `doctor`
to inspect the actual location. Keep plans/log payloads outside verification inputs.

SQLite records revisions and idempotent requests. The advisory cache survives CLI process exits
and is separate from approvals and execution evidence. No raw prompts are retained in that cache.
Unknown usage is reported as unknown, not zero. It does not meter all activity in the host.

A copied worktree and credential-minimized subprocess are not an OS/network sandbox. Full dependency
fingerprints, hostile same-user isolation, and crash recovery remain limited. [Security](../SECURITY.md).

## Distribution and languages

Canonical machine Skill assets live in `src/jev_sm/assets/skills/jev-scrum-master` and are mirrored
to `skills/jev-scrum-master`. The top-level Skill additionally contains a wheel and integrity manifest.
Do not create competing English/Japanese executable Skills: human documentation is bilingual,
while the execution contract and IDs have one source of truth.

Human docs are listed in [the documentation index](README.md). The target spec and ADRs record
historical design decisions; [current implementation status](IMPLEMENTATION_STATUS.md) governs
what users can rely on today. A docs-only update does not upgrade the alpha runtime or validate a host.
