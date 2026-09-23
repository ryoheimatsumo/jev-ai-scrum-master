# Jev AI Scrum Master

**AIコーディングを、計画から「検証済みの完成」まで支援するSkill。**

AI coding agents are good at writing code. Jev AI Scrum Master helps them define what “done” means, verify it with evidence, and improve the next iteration.

> **Skill-first, local-first. MCP is optional.**

**Status:** `0.1.0a3` / experimental alpha. The core workflow is implemented and the repository is public, but live host compatibility and Jev-driven quality, speed, and token savings are not yet benchmarked.

## Why

Coding agents can report “done” before the important behavior has actually been verified.

Jev AI Scrum Master adds a lightweight development loop around your existing coding agent:

```text
Plan  →  Implement  →  Verify  →  Improve
```

It does **not** replace your coding agent. The host LLM still plans and writes code. The local Core manages registered checks, approvals, evidence freshness, and the completion gate.

## What it does

| Stage | What happens |
|---|---|
| **Plan** | Clarify the outcome, acceptance criteria, verification method, and unresolved decisions |
| **Implement** | Let your existing coding agent work within the approved task |
| **Verify** | Run registered checks and bind evidence to acceptance criteria |
| **Complete** | Refuse DONE when required evidence is missing, stale, skipped, or still needs review |
| **Improve** | Capture bounded lessons that can be proposed for similar future tasks |

The unit of work is a **development task**, not a simulated Scrum ceremony.

## Install

### Agent Skills / npx

Use the standard Agent Skills installer:

```bash
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Target a specific coding agent when needed:

```bash
# Cursor
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor

# OpenCode
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a opencode

# Codex
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a codex

# Claude Code
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a claude-code
```

Other installer-supported agent IDs include `windsurf`, `github-copilot`, `gemini-cli`, `cline`, `roo`, `antigravity`, `kilo`, and `grok`.

> These IDs describe targets supported by the upstream `skills` installer. They are **not** a claim that this project has been end-to-end tested on every host.

### Claude Code marketplace

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

### Codex marketplace

```bash
codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

If the marketplace feature is unavailable in your Codex version, use the `npx skills` route above.

See the full [distribution guide](docs/DISTRIBUTION.ja.md) for project/global scope, updates, and local-fork installation.

## First setup

After installing the Skill, ask your coding agent:

> **Use jev-scrum-master and help me set it up for this repository.**

The Skill includes the CLI payload and a bootstrap launcher. Setup is explicit: it does not silently install host permissions, MCP, hooks, API keys, or project dependencies.

Requirements for the Core:

- Git
- Python 3.12+
- Node/npm only when using the `npx skills` installer

Jev itself is **optional and disabled by default**. Enabling it requires a TypeSafe API key and explicit configuration after reviewing what data may leave the machine.

## Configure verification

The Core only runs checks you register. Example:

```yaml
schema_version: 1
checks:
  unit:
    argv: [python, -m, pytest, -q, --junitxml=.jev-sm-output/unit.xml]
    kind: test
    parser: junit
    report_path: .jev-sm-output/unit.xml
    timeout_seconds: 600
    min_tests: 1
    output_limit_bytes: 262144
dod_check_ids: []
jev_enabled: false
```

The runner executes registered commands against copied inputs with minimized credentials. It is **not** an OS or network sandbox.

## Typical workflow

The Skill guides the host through the CLI. A typical flow is:

```bash
jev-sm prepare 'Implement one observable outcome' --key create-01
jev-sm submit-plan TASK /OUTSIDE/REPO/plan.json --revision REV --key plan-01

# Human approval happens in the person's own terminal.

jev-sm start TASK --revision REV --key start-01

# Coding agent implements the approved work.

jev-sm verify TASK --revision REV --key verify-01
jev-sm status TASK
jev-sm evidence TASK EVIDENCE_ID
jev-sm gate TASK
jev-sm complete TASK --revision REV --key complete-01
```

Important behavior:

- An agent claim such as “all tests passed” is not trusted evidence by itself.
- Exit code 0 from a generic command does not automatically mean the acceptance criteria passed.
- Evidence becomes stale when relevant code, contract, or verification inputs change.
- The host cannot self-approve human-only approvals through a flag such as `--yes` or `actor=human`.
- `DONE` means the current task satisfies this tool's completion contract; it does not imply merge, deploy, or Jira completion.

See the [CLI reference](skills/jev-scrum-master/references/cli.md) for the full command contract.

## How Jev is used

Jev is used for **bounded advisory decisions**, not for generating code or granting PASS.

When enabled, the current implementation uses Jev for tasks such as:

- **Readiness:** identify whether a planning gap likely needs repository lookup, a technical probe, a product decision, or more information.
- **Playbook selection:** choose a useful next investigation path when the implementation is stuck or unclear.
- **Context selection:** reduce obviously unrelated context before handing material to a more expensive LLM, while preserving mandatory or uncertain information.
- **Evidence relation:** assess whether a piece of evidence is a direct, partial, contradictory, or unrelated candidate for an acceptance criterion.

Jev results are cached only as advisory decisions. They do not cache approvals, test evidence, or completion.

The default Skill workflow calls the CLI directly. **MCP is optional** and exposes the same Core for clients that prefer tool-based integration.

## Architecture

```text
Coding agent / host LLM
        │
        │ follows Skill
        ▼
   jev-sm CLI
        │
        ▼
   Python Core
   ├─ task / contract state
   ├─ approvals
   ├─ registered runner
   ├─ evidence freshness
   ├─ completion gate
   └─ optional Jev judgments

Optional: MCP → same Core
```

The design deliberately keeps final permissions and completion policy in deterministic code rather than delegating them to Jev or the coding model.

## Alpha limitations

This is an experimental alpha. In particular:

- Live Codex / Claude Code / other-host compatibility is not yet exhaustively smoke-tested.
- Live Jev accuracy, latency improvement, total cost reduction, and token savings are not yet benchmarked for this project.
- Automatic independent AI review is not implemented; standard tasks currently require a real person's substitute review.
- Hard-crash job recovery, enforcement hooks, mutation testing, and automatic question optimization remain future work.
- The local runner is intended for trusted repositories; same-user malicious processes are outside the security boundary.

See [implementation status](docs/IMPLEMENTATION_STATUS.ja.md), [backlog](docs/BACKLOG.md), and [security](SECURITY.md).

## Development

From a source checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/sync_skill_assets.py --check
```

Optional Jev SDK support:

```bash
python -m pip install -e '.[jev]'
```

Optional MCP support:

```bash
python -m pip install -e '.[mcp]'
jev-sm --repo /ABS/PROJECT serve
```

## Documentation

- [Distribution / install guide](docs/DISTRIBUTION.ja.md)
- [Quickstart](docs/QUICKSTART.ja.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.ja.md)
- [Architecture decision: Skill-first CLI](docs/adr/002-skill-first-cli.md)
- [Architecture decision: marketplace and npx](docs/adr/003-marketplace-and-npx.md)
- [Original v1.0 specification](docs/spec/v1.0.ja.md)
- [Changelog](CHANGELOG.md)

## License

Apache-2.0.

No external telemetry is enabled by this project by default. Jev and coding hosts are external services, not bundled models.
