# Changelog

[日本語](CHANGELOG.ja.md)

## 0.1.0a5 — 2026-09-26

- Keep one discoverable `SKILL.md` in the repository so Skills CLI 1.7.0 can update existing
  installations without treating the packaged source as an ambiguous duplicate.
- Preserve the installed Skill name and byte-identical bundled output through template
  normalization, and document the direct tree URL workaround for a4 installations.

## 0.1.0a4 — 2026-09-26

- Plan one reviewed delivery goal with grouped user stories and acceptance criteria, then implement
  and verify small value slices within that approved scope.
- Allow an explicit chat instruction to authorize one hash-bound, agent-mediated plan approval.
  Changed plans or inputs invalidate it; independent final review and other human-only gates remain.
- Rebuild the bundled CLI wheel and document the update path for existing installations.
- Add matching English/Japanese guides, public-content checks, and clearer safety limits.

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
