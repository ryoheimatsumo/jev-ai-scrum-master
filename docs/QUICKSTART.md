# Quickstart

[日本語](QUICKSTART.ja.md)

This guide targets `0.1.0a3`. Use a trusted local Git repository, Git, and Python 3.12+.
Linux has local tests; macOS and actual agent sessions remain unverified. Native Windows is unsupported.

## 1. Install the Skill

In the Git root of the project you want to develop:

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Choose your host. Node/npm and registry access are needed for this installer.
Use only one installation channel per host. [Distribution options](DISTRIBUTION.md).

## 2. Ask for setup

Reload the host if needed, then ask:

> Use jev-scrum-master and help me set it up for this repository.

The Skill locates its own launcher, previews setup, and asks before downloading dependencies.
It prepares a dedicated environment outside your project. Core requires Python 3.12+;
the launcher can start with Python 3.9+ and use an already installed uv to obtain a newer
Python only with download consent. It does not silently install system tools or change host permissions.

Jev remains disabled unless separately configured. API keys never belong in chat or committed files.
Setup consent is not approval of a development task.

## 3. Register real checks

Review `.jev-sm/config.yaml`. For a project that already uses pytest, a check can look like this:

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

This is an example, not a command suitable for every repository. Use the correct Python executable
and already-installed project dependencies. The runner does not install test dependencies.
Assign checks and exact case IDs to the acceptance criteria; defining a check alone does not
make it evidence for every criterion. Register common required checks in `dod_check_ids`.

## 4. Request one observable outcome

> Use jev-scrum-master to let a user update an item, save it, and see the saved value after reopening it.

The agent drafts a plan and asks about unresolved product choices. Inspect the scope, criteria,
checks, and side effects. Perform plan approval in your own terminal as directed by the CLI.
Do not ask the agent to approve for you or simulate a human terminal.

The agent implements, runs checks, and examines missing evidence. In this alpha, standard tasks
also require a real person's substitute review. You must inspect assertions and evidence rather
than approve solely on the agent's claim. Automatic independent AI review is not implemented.

## 5. Check completion and resume

The following are CLI forms, not a ready-to-run transcript. Replace TASK with a real returned ID;
use the actual launcher or executable selected during setup.

```sh
jev-sm --repo /ABS/PROJECT status TASK
jev-sm --repo /ABS/PROJECT gate TASK
jev-sm --repo /ABS/PROJECT report TASK
```

`gate`: 0 means eligible, 2 unmet or waiting, 3 stale evidence, 4 an error.
A generic command's exit 0 only means a result was returned. It is not a test PASS.
DONE is local verification against the current task contract, not merge, deploy, or a correctness guarantee.
After code/config/criteria changes, recheck status and reapprove or reverify as required.

Use `tasks` to discover prior task IDs. If a process was killed during verification, preserve
its records; do not edit the database or reset counters to manufacture completion. See [known limits](IMPLEMENTATION_STATUS.md).

## Optional: source installation

For contributors or a manually managed CLI, clone the repository and install into a virtual environment:

```sh
git clone https://github.com/ryoheimatsumo/jev-ai-scrum-master.git
cd jev-ai-scrum-master
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
jev-sm --repo /ABS/PROJECT skill install --host codex
jev-sm --repo /ABS/PROJECT skill install --host codex --write
jev-sm --repo /ABS/PROJECT init --write
jev-sm --repo /ABS/PROJECT doctor
```

For the local installer, Claude Code uses `--host claude` (unlike the upstream installer's
`-a claude-code`). The first Skill command previews; `--write` applies. Use an absolute CLI path
if the agent cannot inherit your environment. Do not layer this installer over a skills-managed installation.
`--scope user` selects user scope; `--update --write` only updates unchanged installer-owned files.

[Jev options](JEV.md) · [CLI contract](../skills/jev-scrum-master/references/cli.md) · [Security](../SECURITY.md).
