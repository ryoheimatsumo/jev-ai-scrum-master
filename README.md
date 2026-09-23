# Jev AI Scrum Master

**Skillとして使い始め、CLIとCoreが開発の証拠・検証・完了条件を管理する。MCPは任意。**

Skill-first, local-first development support distributed to local Agent Skills hosts. The host LLM plans
and implements. Python owns registered test execution, approvals, evidence freshness and the
completion gate. Optional Jev supplies bounded, batched advisory judgments, not final PASS.

**Version: `0.1.0a3` / experimental alpha.** Host runtime compatibility, live Jev accuracy, speedup and token savings remain
unverified. This is a source/Skill distribution, not an npm or PyPI package release. See
[implementation status](docs/IMPLEMENTATION_STATUS.ja.md) and [validation](docs/validation/marketplace/README.md).

## Marketplace and npx distribution

**Distribution:** the canonical GitHub destination is `ryoheimatsumo/jev-ai-scrum-master`.
Remote commands below require this snapshot to be present on its public `main` branch.
An offline ZIP or an unmerged PR alone does not activate these commands. This is a
self-hosted repository marketplace, not acceptance into an official directory.
For maintainers: [publish the reviewed snapshot](docs/PUBLISHING.ja.md).

### Other agents (also works as the skills-only route for Codex/Claude)

```sh
# AFTER publication: interactive host selection
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master

# Target one or more agents
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a windsurf -a opencode
```

Other documented IDs: `github-copilot`, `gemini-cli`, `cline`, `roo`, `antigravity`,
`kilo`, `grok`, `codex`, `claude-code`. Add `-g` for user scope; omit it for project scope.
Do not use `--all` by default. It targets unneeded hosts and skips confirmation.

**Use the delivered local archive before publication:** from your development project's
Git root (not this distribution's directory), replace the path and run:

```sh
npx skills add /absolute/path/to/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

Node/npm is required by npx. `skills` is a third-party installer from Vercel, not our
package. Its telemetry can be disabled with `DISABLE_TELEMETRY=1`. Inspect the trusted
source before installing. Installation and update behavior belongs to that CLI.

### Claude Code marketplace

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

Before publication, use `/plugin marketplace add /absolute/path/to/jev-ai-scrum-master`.
Restart/reload as required by your host. This is our repo marketplace, not approval by
the official Anthropic directory.

### Codex local/repo marketplace

```sh
codex plugin marketplace add /absolute/path/to/jev-ai-scrum-master
# AFTER publication: codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

Use the supported plugin browser to select **Jev Development Tools → Jev AI Scrum Master**.
The `.agents/plugins/marketplace.json` and portable `plugin.json` are included. This does not
claim submission/acceptance in the universal public directory. If that marketplace feature
is unavailable in your host/version, use `npx skills ... -a codex` instead.

### After install: one setup conversation

Ask your host: **Use jev-scrum-master and help me set it up for this repository.**
The self-contained Skill includes the exact CLI wheel and a stdlib bootstrap launcher.
After setup consent it creates a dedicated runtime outside the project; no manual clone,
venv activation, MCP registration, or global pip install is necessary on a suitable machine.
Core still needs Git and Python 3.12+. The launcher runs on Python 3.9+ and can use an
already installed uv to obtain newer Python after consent. It does not silently install
Node, Python, uv, or host settings. Package downloads, project initialization, actual test
commands, the Jev API key and sending code to Jev are separate reviewed setup steps.
The API key never belongs in chat, the Skill, or version control.

A Skill update uses a new content/version-specific runtime after setup consent. Existing
runtimes and task state are preserved. Choose ONE channel per host; don't install both a
marketplace plugin and a skills.sh copy. See [Japanese guide](docs/DISTRIBUTION.ja.md).

A Skill teaches the host how to work; it is not an always-on monitor or a security boundary.
The Core, approval and evidence gates remain unchanged. Read [ADR-003](docs/adr/003-marketplace-and-npx.md).
The original [v1.0 specification](docs/spec/v1.0.ja.md) stays unchanged.

## What changed in a3

- Self-contained marketplace Skill: bundled wheel, integrity manifest and consent-based launcher.
- Native Claude/Codex marketplace metadata plus standard `npx skills add` distribution.
- Host-neutral workflow, absolute Skill-root discovery, separate SDK installation/API opt-in.
- Version-specific isolated runtimes, offline wheelhouse option, copy/symlink portability.
- Offline consistency/bootstrap tests and explicit opt-in npx distribution smoke workflow.

## Install from this source archive

Python **3.12+**, Git and POSIX (Linux/macOS) are required. Local validation uses Linux/Python
3.13. macOS and actual host applications have not been smoke-tested. Windows is unsupported.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .             # Core + CLI + packaged Skill; no MCP or Jev SDK needed
# Optional, only when you intend to enable Jev:
python -m pip install -e '.[jev]'
```

The commands below target **your development project's Git root**, not necessarily this tool's
source directory. Use the absolute `jev-sm` executable from this virtual environment when your
host does not inherit its PATH. No published package is assumed.

```bash
jev-sm --repo /ABS/YOUR/PROJECT skill install --host codex            # preview only
jev-sm --repo /ABS/YOUR/PROJECT skill install --host codex --write    # explicit write
# For Claude Code choose --host claude instead.
# For all your local projects choose --scope user (no project Git repo needed for installation).
jev-sm --repo /ABS/YOUR/PROJECT init                                # configuration preview
jev-sm --repo /ABS/YOUR/PROJECT init --write
jev-sm --repo /ABS/YOUR/PROJECT doctor
```

Install before approving a task, because a project Skill is part of that worktree's inputs.
The installer writes only the selected `jev-scrum-master` Skill directory. It does not set
permissions, enable Jev, register MCP, install dependencies, or change AGENTS.md/CLAUDE.md.
Existing unmanaged or edited Skills are preserved. An unchanged managed old version can be
updated with `skill install --host HOST --update --write`. Run `skill status --host HOST` to inspect.
Do not combine manual Skill installation and the optional plugin packaging in the same host.

Reload/restart your host according to its version, then explicitly request the
**jev-scrum-master** Skill. Actual discovery/execution in Codex/Claude still needs a host smoke
test. Read [host integration](integrations/README.md) and [Japanese quickstart](docs/QUICKSTART.ja.md).

## Configure checks, then use the Skill

Review `.jev-sm/config.yaml` and register commands you trust. Example:

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

Use an explicit environment's Python executable if needed. Dependencies must already exist;
the runner does not install them. Commands run in copied inputs with minimized credentials,
not an OS/network sandbox. Use trusted code and never production credentials/data.

The Skill guides the host through these real CLI operations:

```bash
jev-sm prepare 'Implement one observable outcome' --key create-01
jev-sm schema contract                  # on demand, not in every response
jev-sm submit-plan TASK /OUTSIDE/REPO/plan.json --revision REV --key plan-01
# The person runs approve plan TASK --version VERSION in their own terminal.
jev-sm status TASK
jev-sm start TASK --revision REV --key start-01
# The coding host implements the approved work.
jev-sm verify TASK --revision REV --key verify-01
jev-sm status TASK
jev-sm evidence TASK EVIDENCE_ID
# The person inspects the assertions/evidence and performs required review approvals.
jev-sm gate TASK
jev-sm complete TASK --revision REV --key complete-01
```

`TASK`, `REV`, evidence IDs and versions come from real outputs. The host must never run human
approval commands on the person's behalf. There is no --yes, actor=human or PASS/DONE override.
Same-UID malicious processes are outside the security boundary; see [SECURITY.md](SECURITY.md).

`verify` waits synchronously and owns its runner. General CLI exit 0 means the operation
returned a result, **not that all criteria passed**. `gate` is 0=eligible, 2=unmet/waiting,
3=stale and 4=input/execution error. `report` emits Markdown. `status --full` is explicitly
verbose diagnostics. `tasks` lists history; recheck status/gate before relying on DONE.

JSON payload files may be `-` for stdin. Keep temporary plans/logs outside the source worktree,
so they do not invalidate verification. Reuse both key and exact request/revision for a retry;
new operations get new keys. See [full CLI reference](skills/jev-scrum-master/references/cli.md).

## Deeper Jev paths without MCP

After inspecting what input may leave the machine, install the jev extra, export
`TYPESAFE_API_KEY`, and set `jev_enabled: true` in the reviewed config. Settings changes require
reapproval of existing tasks. No API key is intentionally inherited by test subprocesses.

```bash
jev-sm advise readiness TASK
jev-sm advise playbook TASK --observation-file /OUTSIDE/REPO/observed.txt
jev-sm select-context TASK --input /OUTSIDE/REPO/context.json
jev-sm advise evidence TASK
jev-sm cache stats
```

Jev does not grant PASS. Unknown/unavailable judgments retain information and required review.
Mark AC, constraints and critical failures as mandatory=true and keep originals for re-expansion.
Counts are characters, not tokens. No host-level usage savings have been measured.

The cache default is 86,400 seconds and at most 512 entries per workspace. Only explicit
`jev-X.Y.Z` model versions are cacheable; aliases are not. Keys include task, contract, config,
input (hashed original plus redacted input), question version/content and backend. Failed calls
are not cached. Reuse is advisory and records zero new provider calls, not a new verification.

Set `jev_cache_ttl_seconds: 0` or `jev_cache_max_entries: 0` to disable. `cache clear` previews;
`cache clear --write` clears cached results without deleting evidence/decision history. Concurrent
cold misses can still duplicate calls; atomic cross-process provider-budget reservation remains
future work. Cache migration is additive, but new defaults change the normalized settings hash:
**review and reapprove pre-a2 tasks instead of reusing old approvals blindly**.

## Reproduce local behavior

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/sync_skill_assets.py --check
python scripts/demo_cli.py --simulate-approvals
```

The demo creates a disposable Git repo and uses separate real CLI processes, no MCP server. It
checks a broken persistence feature, fixes it, requires review, completes it, proposes a lesson,
and invalidates evidence after another edit. `--simulate-approvals` is an explicit **test fixture**,
not actual human or independent AI review. Without the flag the demo asks for real TTY approval.
No Jev or host LLM is called. It is not an end-to-end AI quality benchmark.

## Optional integrations and remaining scope

For MCP only: install `.[mcp]`, then use `jev-sm --repo /ABS/PROJECT serve`. The existing 13 tools
remain; CLI and MCP share the same Core. MCP verification returns a job ID rather than waiting.
[Integration examples](integrations/README.md) are optional and never auto-installed.

Automatic independent AI review, hard-crash job recovery, enforcement hooks, complete external
environment fingerprints, mutation testing and question optimization remain unimplemented.
Standard tasks still require a real person's substitute review. Jev/host integration and SDK
wire tests are separate from local Core tests. See [backlog](docs/BACKLOG.md).

## Publish this alpha snapshot to GitHub

The publication helper defaults to an offline preview and includes only files matching
`PUBLICATION_MANIFEST.json`. It refuses a different GitHub account, existing repositories,
modified files and symlinks. The explicitly requested public upload creates a fresh
`main` commit containing the latest source, top-level Skill and marketplace manifests.
It does not upload the old development history or create an unmerged publication PR.

```bash
bash scripts/publish-github.sh            # offline preview only
# After authenticating GitHub CLI as ryoheimatsumo:
bash scripts/publish-github.sh --public   # NEW public repository + main push
```

Python 3.9+, Git and authenticated GitHub CLI are required for this publication helper.
Use a new, unmodified extraction of the publication archive. It leaves the working
snapshot untouched and retains the new local checkout. It never force-pushes, overwrites,
changes an existing repository's visibility, merges PRs or publishes npm/PyPI packages.
See [publishing guide](docs/PUBLISHING.ja.md) for authentication and partial-failure recovery.
Hashes detect accidental edits; they are not signatures or a substitute for a security audit.

Apache-2.0. No external telemetry by default. Jev/coding hosts are external services, not bundled
models. Canonical Skill assets live under src/jev_sm/assets/skills; the top-level skills/ mirror
is generated with scripts/sync_skill_assets.py and checked in tests.
