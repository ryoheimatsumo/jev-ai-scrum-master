# ADR-002: Skill-first entry, shared CLI/Core, optional MCP

Date: 2026-09-23. Status: implemented in 0.1.0a2, host/runtime performance unverified.
The user approved this interface change after the initial alpha. Preserve docs/spec/v1.0.ja.md
as the original design record; this ADR supersedes its MCP-first distribution emphasis.

## Decision

- Skill is the primary workflow entry. CLI is the default invocation adapter. Core is unchanged
  as the authority for contracts, approvals, Runner evidence and completion.
- Keep the 13-tool MCP adapter as an optional dependency/path, not mandatory setup.
- Complete CLI coverage: compact status, registered evidence reads, context selection,
  improvement proposals, rule discovery, schemas, task discovery and bounded stdin JSON.
- Keep the Skill short. Split stage references and ship them in both the wheel and a checked
  repository mirror. Installer previews, preserves foreign/customized files, and never edits
  user AGENTS.md, CLAUDE.md, settings, MCP configuration, hooks or permissions.
- Use a workspace/task-scoped SQLite advisory cache with pinned-model keys, input/question/
  contract/config binding, TTL, size bound, integrity checks and explicit clearing. Never cache
  acceptance evidence or approval. Failures are not cached; disabled provider consent is checked
  before cache lookup. No cross-project sharing, raw prompts or provider secrets in cache.

## Compatibility

prepare defaults to a compact response; --include-schema retains the earlier form. status
uses compact_status by default; --full retains diagnostic state. init defaults to JSON; --yaml
retains YAML output. Existing commands, gate exit codes, approvals and MCP tools remain.
New Settings defaults alter config_hash for pre-a2 tasks, conservatively requiring reapproval.
Database migration adds a cache table without changing existing tasks/evidence.

## Limits

Installation tests prove file placement and protection, not actual host Skill recognition.
An installed Skill is not an interception boundary. No auto-hook or model approval surface.
No live provider benchmark, independent host reviewer or crash recovery is claimed. Parallel
cold cache misses can still call the provider twice; provider budgets are not atomically reserved
across OS processes. Same-user tampering is outside the security boundary.

## Primary references consulted (2026-09-23)

- https://developers.openai.com/codex/skills/ (redirects to ChatGPT Learn build-skills):
  SKILL.md, optional references/assets and .agents/skills project/user locations.
- https://code.claude.com/docs/en/skills : .claude/skills project/user locations and on-demand references.
- https://code.claude.com/docs/en/plugins-reference : optional plugin root and skills/ layout.

These support adapter layout, not claims of validated runtime compatibility or model gains.
