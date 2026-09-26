# Implementation status

[日本語](IMPLEMENTATION_STATUS.ja.md)

Reviewed: 2026-09-26. Runtime: `0.1.0a5`, **experimental alpha / quality improvement unverified**.
The repository is public. Skill + CLI is the primary path; MCP and Jev are optional.

## Implemented

Versioned plans, a hash-bound agent-mediated plan approval after an explicit chat instruction,
other explicit local approvals, a single active task per worktree, registered command
execution, JUnit/JSON reports, evidence freshness, bounded fix cycles, completion checks, and
improvement proposals. Jev provides readiness/playbook/context/evidence advice and a persistent
advisory cache. Jev cannot independently approve completion.

The host generates plans and code. Standard tasks currently require a real person's substitute
review. The runtime is not a self-contained autonomous coding agent.

## Validation is scoped

The original a3 packaging run recorded **233 passed, 3 skipped**; publication-helper tests were
recorded separately. These counts are historical, not a claim about every later commit.
The merged documentation commit `fbf8159` has a successful GitHub Actions
[Tests run](https://github.com/ryoheimatsumo/jev-ai-scrum-master/actions/runs/35822543177).
A green workflow is not evidence of live model accuracy, real host operation, or installation
through every external channel. [Validation index](validation/INDEX.md).

The local demos explicitly simulate approval. Fixture providers do not measure Jev. Placement
tests do not run the target coding agent. Keep those distinctions in release notes.

## Not implemented or not demonstrated

| Area | Current limit |
|---|---|
| Independent review | Automatic isolated AI reviewer unavailable; human substitute required. |
| Recovery | Full recovery of hard-killed jobs/orphan processes unavailable. |
| Enforcement | No completed host-wide hook/CI enforcement integration. |
| Environment | Full dependency/remote-service fingerprint and artifact-deletion handling incomplete. |
| Jev experiments | Mutation testing, adaptive multi-plan search, and automatic question optimization not implemented. |
| Performance | Quality, speed, total cost, and host-token improvements not benchmarked. |
| Hosts | Actual end-to-end coding-agent compatibility and macOS operation unverified. |
| Platform | Native Windows unsupported. |
| Concurrency | Concurrent cold misses may duplicate calls; no atomic cross-process provider-budget reservation. |

A trusted-code copy is not a sandbox. Same-user tampering is outside the guarantee.
Never advertise complete implementation of the target spec or a percentage improvement without
corresponding results. [Backlog](BACKLOG.md) · [Target spec](spec/v1.0.ja.md) (Japanese design original).
