# Jev AI Scrum Master

**English** | [日本語](README.ja.md)

**Define what done means. Verify it with evidence. Learn from the task.**

A Skill for your existing coding agent, backed by a local CLI. The agent plans and writes code;
the Core manages approved checks, evidence freshness, and the task's completion conditions.
**MCP is optional.**

**Experimental alpha — `0.1.0a4`.** This independent community project is intended for trusted
local repositories. Live coding-agent compatibility and improvements in quality, speed, cost, or
token use have not been demonstrated for this project; these are not measured results. Standard
tasks currently require a person's review; an independent AI reviewer is not implemented. See
[current status](docs/IMPLEMENTATION_STATUS.md).

## What it does

| Stage | Support |
|---|---|
| Plan | Make the outcome, acceptance criteria, checks, and open decisions explicit. |
| Implement | Let your coding agent work within the approved scope. |
| Verify | Run registered checks; keep results tied to the code and criteria being checked. |
| Complete | Require current evidence and approvals before recording DONE. |
| Improve | Propose lessons for similar tasks; adoption requires human approval. |

For example, a task to change an item and persist it should verify both the change and a fresh
read after saving. A claim that the screen changed is not evidence that persistence works.
The tool helps track that distinction; it does not prove the absence of bugs.

For a larger change, the agent presents the full set of user stories and acceptance criteria
as a readable plan card. After you explicitly approve that current card in chat, the agent can
record a hash-bound plan approval and work through small value slices without asking again for
each slice. Material changes to the approved scope or criteria require a new review. Standard
tasks still require a person's final substitute review.

## Install

From the Git root of the project you want to work on:

```bash
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Select your agent interactively, or append `-a codex`, `-a claude-code`, or `-a cursor`.
Installation targets are not a tested-host compatibility guarantee.
[Other agents, marketplaces, and updates](docs/DISTRIBUTION.md).

For Claude Code's repository marketplace:

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

Use one installation channel per host. This is an independent repository marketplace,
not an official directory listing or endorsement.

## Get started

Ask your agent:

> Use jev-scrum-master and help me set it up for this repository.

Review the proposed setup, register your actual test commands, and then request one task.
The Skill includes a launcher for a dedicated CLI environment. Setup downloads require consent;
project test dependencies and task approvals are separate.

**Requirements:** Git and Python 3.12+ for the Core; Node/npm for `npx`. Linux is locally tested,
macOS is unverified, and native Windows is unsupported in this alpha.

Jev is **disabled by default**. Enabling it requires the optional SDK, a `TYPESAFE_API_KEY`
environment variable, and reviewed configuration. Never paste credentials into chat or commit them.
[Quickstart](docs/QUICKSTART.md) · [Jev setup and usage](docs/JEV.md).

## How Jev is used

Jev supplies bounded advice about planning gaps, the next investigation method, relevant context,
and how evidence relates to an acceptance criterion. It does not write the implementation or
approve tests, permissions, or completion. Unknown or unavailable advice does not waive review.
The host must invoke the workflow; the Skill is not an always-on supervisor.

## Safety and limitations

Registered tests execute code. A disposable copy and a reduced environment are **not an OS/network sandbox**.
Use trusted repositories and non-production data. Same-user processes can access
files outside the copy and can tamper with local state. [Security model](SECURITY.md).

DONE applies only to this tool's current task contract. It is not a guarantee of correctness,
independent certification, merge, deployment, or Jira completion. Automatic independent AI review,
crash recovery, enforcement hooks, and mutation testing are not yet implemented.

The Core adds no automatic external telemetry. Your coding host, installer, package registries,
and an enabled Jev API have separate network behavior and policies. To opt out of the third-party
Skills installer's telemetry, set `DISABLE_TELEMETRY=1`. See [data handling](SECURITY.md).

## Documentation and contributing

[Documentation index](docs/README.md) · [Contributing](CONTRIBUTING.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Backlog](docs/BACKLOG.md) · [Changelog](CHANGELOG.md) ·
[Publication audit](docs/reviews/2026-09-23-publication-audit.md).

Human-facing guides are available in English and Japanese. Executable Skill instructions,
CLI identifiers, and raw test reports remain in their original format; see the documentation index.

## License

[Apache-2.0](LICENSE). Jev and coding hosts are external services, not bundled models.
This is an independent project; it does not claim endorsement by TypeSafe, OpenAI, Anthropic, or Vercel.
