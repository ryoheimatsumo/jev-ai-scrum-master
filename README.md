# Jev AI Scrum Master

**Help your coding agent define what “done” means — and check the evidence.**

Plan → Implement → Verify → Improve

A Skill for local coding agents, backed by a Python CLI that manages tasks,
registered checks, approvals, and verification evidence. Your existing agent still
plans and writes the code. MCP is an optional interface to the same Core.

**Experimental alpha (`0.1.0a3`).** Standard tasks currently require a real person
for the review step; an independent AI reviewer is not implemented. Performance
improvements are goals, not measured results. This is an independent community
project, not an official or endorsed product of TypeSafe, OpenAI, Anthropic, or Vercel.

[日本語クイックスタート](docs/QUICKSTART.ja.md) ·
[Installation details](docs/DISTRIBUTION.ja.md) ·
[Implementation status](docs/IMPLEMENTATION_STATUS.ja.md)

## What it does

| Stage | Support provided |
| --- | --- |
| Plan | Structure one observable outcome, acceptance criteria, and verification methods |
| Implement | Let the coding agent work within the approved task; offer optional investigation advice |
| Verify | Run registered checks and associate their results with acceptance criteria |
| Complete | Keep the task open when required evidence is missing, stale, failed, or awaiting review |
| Improve | Record evidence-linked improvement proposals for a person to approve |

An agent saying “all tests passed” is not execution evidence. A successful command
exit alone is not proof that a behavior was tested. DONE refers to this tool's
current task contract — not a merge, deployment, Jira update, or guarantee of bug-free software.

## Install

From your development project's Git root, use Vercel's Agent Skills installer:

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

To choose a target explicitly, append `-a codex`, `-a claude-code`, or `-a cursor`.
The [distribution guide](docs/DISTRIBUTION.ja.md) lists other installer targets.
Installer support does **not** mean this project has been tested end-to-end in that host.

Alternatively, in Claude Code:

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

This is a repository-hosted marketplace, not an official directory endorsement.
Use only one installation channel per host. The project itself is not published
as an npm or PyPI package; `npx` runs the third-party `skills` installer.

## First use

Reload your coding agent if needed, then ask:

> Use jev-scrum-master and help me set it up for this repository.

The Skill guides setup of its bundled CLI after your consent. Register your
project's actual test commands in `.jev-sm/config.yaml`; the runner does not
install project dependencies. Then request a small development task, for example:

> Use jev-scrum-master to add a saved preference and verify that it survives a reload.

The agent prepares a plan and verification criteria. You review the plan and run
the required approval commands yourself. After implementation, the CLI runs checks,
reports missing evidence, and requires the current review conditions before completion.
See the [quickstart](docs/QUICKSTART.ja.md) and [CLI reference](skills/jev-scrum-master/references/cli.md).

**Requirements:** Git and Python 3.12+ for the Core; Node/npm for `npx` installation.
The bundled launcher can run on Python 3.9+ and use an already installed `uv` to
obtain a suitable Python after download consent. Linux Core/SDK checks have run
in CI. macOS and live coding-agent workflows remain unverified; native Windows is unsupported.

## How Jev is used

Jev is optional and disabled by default. When enabled, it supplies bounded advice:

- **Readiness:** classify missing prerequisites in a proposed plan.
- **Next-step selection:** suggest an investigation playbook, without executing it.
- **Context selection:** identify clearly unrelated snippets while retaining mandatory or uncertain information.
- **Evidence relation:** suggest how test results relate to an acceptance criterion, not whether assertions prove it.

Jev does not generate code, approve a plan, grant PASS, or override completion rules.
Its cache stores advisory decisions, not fresh test results or approvals. Live Jev
accuracy, end-to-end speed, and token/cost savings have not been measured for this project.

## Data and safety

Task state and verification artifacts are stored locally. **This does not mean
all processing is offline:** your coding agent may send context to its model provider;
enabling Jev sends selected inputs to TypeSafe. Setup can contact package registries
and interpreter-download services after consent. Installer telemetry is governed
by the installer, separately from this project's defaults.

Never paste API keys into chat or commit them. Review permitted input before
setting `TYPESAFE_API_KEY` and enabling Jev. Redaction is best effort, not a guarantee.

Use trusted repositories only. Checks run in disposable copies with minimized
environment variables, **not an OS/network sandbox**. They can access files and
network resources available to the same OS user. Human approval gates prevent
workflow mistakes; they do not isolate a hostile same-user process.

See [SECURITY.md](SECURITY.md) for boundaries and vulnerability reporting.

## Development

From a source checkout with Python 3.12+:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
python scripts/check_public_content.py
```

Optional extras are `.[jev]` and `.[mcp]`. To run the MCP interface after installing
its extra, use `jev-sm --repo /ABS/PROJECT serve`.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) ·
[Backlog](docs/BACKLOG.md) · [Validation records](docs/validation/README.md)

## License

[Apache-2.0](LICENSE). External models, services, and dependencies have their own terms.
