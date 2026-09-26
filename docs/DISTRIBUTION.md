# Installation and distribution

[日本語](DISTRIBUTION.ja.md)

The GitHub repository is public. This is a source/Skill distribution, not our own npm or
PyPI release and not an official marketplace listing. Local packaging tests do not establish
that every coding agent can discover and execute the Skill.

## Agent Skills installer

Run in your development project's Git root:

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

The third-party `skills` CLI handles host selection and placement. Node/npm and registry access
are required. Review the source and installation choices. `-g` selects user scope; omit it for
project scope. Do not use blanket `--all` or approval-skipping flags by default.

| Host | Installer ID |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| Windsurf | `windsurf` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |
| OpenCode | `opencode` |
| Cline | `cline` |
| Roo Code | `roo` |
| Antigravity | `antigravity` |
| Kilo Code | `kilo` |
| Grok Build | `grok` |

These are documented installer targets, not a tested compatibility matrix. The host needs local
Skill and shell access to Git/Python. An example with a selected host:

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

The installer has its own telemetry. Set `DISABLE_TELEMETRY=1` to opt out according to its
[documentation](https://skills.sh/docs/cli). This setting does not control coding-host or Jev traffic.

## Claude Code repository marketplace

Inside Claude Code:

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

Reload as directed by the host. These are our repository's manifests; they do not indicate
Anthropic approval. The package does not add MCP, hooks, or expanded permissions.
See [upstream marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces).

## Codex marketplace option

```sh
codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

This registers a catalog; it is not itself proof of Skill installation or runtime support.
Follow the installed host's plugin interface to choose Jev Development Tools / Jev AI Scrum Master.
Upstream [plugin packaging instructions](https://developers.openai.com/plugins/build/plugins)
describe catalog setup and installation/testing through the supported desktop interface.
If unavailable in your version, use `npx skills ... -a codex` instead. This project's host integration
has not been smoke-tested end to end.

## First setup, updates, and removal

Use one channel per host. Ask the host to set up `jev-scrum-master`, review downloads, and
register real project checks. [Quickstart](QUICKSTART.md).

The Skill contains the CLI wheel, integrity manifest, launcher, and references. Do not copy
`SKILL.md` alone. Setup creates a dedicated runtime outside the project after consent.
Core requires Python 3.12+; the launcher accepts Python 3.9+ and can use an already installed uv
with download consent. No system tool, API key, permission, MCP, or hook is silently installed.

Updates use content/version-specific runtimes and preserve prior state. Local modifications
may be replaced by upstream updates: keep customizations in a fork or back them up first.
For a project-scope installation made with the Skills CLI, run in that project's Git root:

```sh
npx skills list
npx skills update jev-scrum-master
```

For a user-scope installation, add `-g` to the update command. Use the same channel and host
selection as the original installation. An older or manually copied installation may lack the
lock data needed for automatic update; back up local edits and re-add the full Skill from this
repository with the same host and scope. Marketplace installations use their host's plugin
update flow instead. Reload the host after updating, then ask it to set up the updated
`jev-scrum-master` runtime. A changed bundled wheel needs a new dedicated Python environment
and setup consent. Removing a Skill does not remove runtime environments, evidence, task
history, or separately stored credentials.

For a local checkout or fork, pass its directory instead of the GitHub shorthand:

```sh
npx skills add /ABS/PATH/TO/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

A local source still requires access to the installer if it is not already available.

## Runtime integrity and limits

The launcher checks the bundled wheel's version and SHA-256. These detect mismatch, not publisher
identity. Dependencies are constrained rather than fully locked. The dedicated Python environment
is not a security sandbox. Jev requires a separate SDK, API key, data review, and opt-in.
[Security](../SECURITY.md) · [Implementation status](IMPLEMENTATION_STATUS.md).

Maintainers should follow [release preparation](PUBLISHING.md). Version-specific raw validation
records describe historical tests, not the current remote installation status.
