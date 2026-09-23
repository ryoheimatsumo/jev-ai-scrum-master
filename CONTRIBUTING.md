# Contributing

Use Python 3.12+ and a virtual environment. Install editable source with `pip install -e '.[dev,mcp,jev]'`.
Run `python -m compileall -q src tests`, `python -m pytest -q`, and
`python scripts/demo.py --simulate-approvals`. CI additionally installs the optional official SDKs
and tests their contracts and stdio handshake. Live model tests require explicit paid API opt-in.

The release is an initial alpha. Security/reliability fixes and host adapter tests take priority
over adding autonomous behavior. Include tests, threat-model implications, and a truthful update
to implementation status. Do not merge unvalidated generated rules into runtime policy.

Proposed next work is in docs/BACKLOG.md. Open a separate branch/PR. Do not auto-merge the initial
implementation PR or create public releases from this scaffold without completing the beta gates.

## Skill-first changes

The primary setup is `python -m pip install -e '.[dev]'`; MCP/TypeSafe extras are optional.
Edit canonical Skill resources in `src/jev_sm/assets/skills/jev-scrum-master`, then run
`python scripts/sync_skill_assets.py`. CI tests the discoverable mirror and wheel resources.
Do not duplicate domain/approval logic between CLI and MCP. Read ADR-002 before changing
response defaults or installer behavior. Reproduce the CLI flow with
`python scripts/demo_cli.py --simulate-approvals`; simulated approvals must remain confined
to tests and disposable demos. No production fake-human switch may be introduced.
