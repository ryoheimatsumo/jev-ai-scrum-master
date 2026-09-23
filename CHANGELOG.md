# Changelog

## 0.1.0a3 — 2026-09-23

- Self-contained Skill: CLI wheel, integrity manifest, consent-based runtime bootstrap.
- Claude/Codex marketplace metadata and multi-agent `npx skills add` distribution.
- Generic host guidance, offline setup, version/content-specific environments.
- Distribution tests and opt-in real npx smoke workflow.
- Not remotely published; npx fetch, live agents/Jev, macOS remain unverified.


## 0.1.0a2 — 2026-09-23

Skill-first entry and installer; shared CLI/Core with optional MCP. Compact JSON, stdin payloads,
evidence/context/improvement CLI coverage, task/rule discovery, schema commands. Persistent bounded
SQLite advisory cache and explicit clear/status. Packaged Skill resources with on-demand references;
existing modified Skill files are protected. Separate-process CLI demonstration.

Compatibility: status defaults to compact (--full for prior diagnostic form); prepare no longer
returns a schema by default (--include-schema); init defaults to JSON (--yaml for YAML). New settings
defaults conservatively invalidate pre-a2 plan/config approvals; review and reapprove. No performance
claims or live host/Jev validation. Existing alpha restrictions remain.

## 0.1.0a1

Initial Core, managed verification, evidence gates, optional Jev/MCP adapters and local tests.
