# Distribution entry points (0.1.0a3)

Use [the current distribution guide](../docs/DISTRIBUTION.ja.md). Claude/Codex have repo
marketplace manifests; other local coding agents use standard `npx skills add`. No MCP
configuration is needed. Do not install the same Skill through two channels in one host.
All hosts use the same runtime; actual host compatibility remains unverified.

## Legacy direct install / optional MCP notes

# Skill-first host integration (0.1.0a2)

## Standard: Skill + CLI, no MCP needed

Install the base package from source (`python -m pip install -e .`) in a virtual environment.
Use its absolute executable path if your coding host does not inherit that environment's PATH.
Point --repo at the existing development project's Git root.

```sh
jev-sm --repo /ABS/PROJECT skill install --host codex          # preview
jev-sm --repo /ABS/PROJECT skill install --host codex --write
# Claude Code: replace codex with claude.
```

Project targets: `.agents/skills/jev-scrum-master` for Codex and
`.claude/skills/jev-scrum-master` for Claude Code. `--scope user` uses the corresponding directory
under HOME and can be invoked outside Git. Install before task approval. No existing
AGENTS.md/CLAUDE.md or host settings/MCP configuration is changed. Unmanaged/modified Skills
are never overwritten. `--update --write` updates only an unchanged installer-owned Skill.

After installation, reload/restart the host as appropriate for its version and explicitly
request the jev-scrum-master Skill. Local installer tests do not verify host discovery or use.
Python/Git/CLI and registered project test dependencies must be installed separately.

Configure `.jev-sm/config.yaml` using init and your reviewed test commands, then follow the
Skill. Human approvals are outside model tools. No automatic review or Hook is installed.

## Optional Claude Code plugin packaging

The source root contains `.claude-plugin/plugin.json` and `skills/`. It may be loaded as a local
plugin using the host's documented plugin-directory mechanism AFTER installing the CLI.
Do not also install the same project/user Skill in that host. The manifest contains no MCP
server, Hook, permission expansion or dependency-install command. Actual host loading has not
been smoke-tested. Plugin packaging is not an alternative Python runtime.

## Optional MCP

Install `python -m pip install -e '.[mcp]'` and manually review the example in codex/ or
claude-code/. Replace every /ABS/... placeholder with the appropriate absolute path. The
server is one explicitly selected local Git worktree, not a shared multi-project service.

The 13-tool adapter reuses Core, SQLite and the persistent advisory cache. Task/contract/revision/
key semantics are the same as CLI. Do not replay a mutation through a different interface with
new keys. CLI verify waits; MCP verify returns job_id and runs while its server remains alive.
No approval tools exist. Neither MCP nor Skill intercepts every host action or Git operation.

Official layout references checked on 2026-09-23:
https://developers.openai.com/codex/skills/
https://code.claude.com/docs/en/skills
https://code.claude.com/docs/en/plugins-reference
