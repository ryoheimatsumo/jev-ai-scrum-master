# Changelog

[日本語](CHANGELOG.ja.md)

## Unreleased — documentation and public-content review

- Add matching English/Japanese user and maintainer guides with reciprocal navigation.
- Replace stale installation placeholders and distinguish initial-upload history from current use.
- Clarify trusted-code execution, optional external services, human review, and unmeasured benefits.
- Add repeatable documentation checks. Runtime code, executable Skill payload, and a3 wheel are unchanged.

## 0.1.0a3 — 2026-09-23

Self-contained Skill with CLI wheel, integrity manifest, consent-based bootstrap, marketplace
metadata, and standard `npx skills add` distribution. Added copy/link/bootstrap tests and an
opt-in installer smoke workflow. The repository was subsequently published on GitHub; package
registry publication and official directory acceptance are separate and have not been claimed.
Initial a3 validation could not complete npm retrieval and did not run live agents/Jev or macOS.

## 0.1.0a2 — 2026-09-23

Skill-first CLI/Core with optional MCP; compact JSON and stdin payloads; evidence/context/improvement
commands; task/rule/schema discovery; persistent SQLite advisory cache; protected local Skill
installation; separate-process CLI demo. `status --full`, `prepare --include-schema`, and `init --yaml`
retain detailed/earlier forms. New defaults require pre-a2 plan/config approvals to be revisited.
No live host/model or performance claim.

## 0.1.0a1

Initial Core, managed verification, evidence gates, optional Jev/MCP adapters, and local tests.
