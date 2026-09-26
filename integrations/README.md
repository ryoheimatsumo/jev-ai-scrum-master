# Host integration

[日本語](README.ja.md)

Use [Skill installation](../docs/DISTRIBUTION.md) and [quickstart](../docs/QUICKSTART.md) by default.
Install through one channel per host. Host-specific directory placement is not a guarantee that
the host can execute the workflow. A local shell, Git, and the CLI runtime are needed.

## Optional MCP

From a source checkout's environment:

```sh
python -m pip install -e '.[mcp]'
jev-sm --repo /ABS/PROJECT serve
```

Review [Codex's example](codex/config.example.toml) or [Claude Code's example](claude-code/mcp.example.json)
and replace every absolute-path placeholder. Do not insert secrets into committed configuration.
One server targets one local Git worktree; it is not a remote team service.

CLI and MCP share Core, SQLite, and the advisory cache. CLI verification waits; MCP returns a
job ID while its server owns the work. Do not replay state-changing operations with new keys or
switch state directories for the same task. No human approval tool is exposed through MCP.

Neither Skill nor MCP intercepts all host/Git actions. No automatic hooks, permission expansion,
or independent AI reviewer are installed. [Architecture](../docs/ARCHITECTURE.md) · [Security](../SECURITY.md).
