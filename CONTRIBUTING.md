# Contributing

[日本語](CONTRIBUTING.ja.md)

Contributions to reliability, documentation, and reproducible tests are welcome. This is an
experimental alpha; do not present the target specification as a completed implementation.
Read [current status](docs/IMPLEMENTATION_STATUS.md) and [security](SECURITY.md) first.

## Local development

Use Python 3.12+ and a virtual environment in a source checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m compileall -q src tests
python -m pytest -q
python scripts/check_public_docs.py
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
```

Install `.[dev,mcp,jev]` only when testing optional SDK integrations. Live Jev tests need separate
explicit authorization and credentials; SDK installation is not consent to paid calls.

`python scripts/demo_cli.py --simulate-approvals` runs a disposable demo. Its approvals are
fixtures, not actual human review. Production must never acquire a fake-human approval option.

## Changes and generated assets

Work on a separate branch and open a PR. Include tests, known limitations, and any security
implications. Never weaken required checks, permit model-written PASS/DONE overrides, or silently
expand outbound data or execution permissions. Do not change the repository name as part of docs work.

Edit canonical machine Skill assets under `src/jev_sm/assets/skills/jev-scrum-master`; do not edit
only the `skills/` mirror. Use the [release guide](docs/PUBLISHING.md) when source/Skill changes
require a rebuilt wheel. Keep CLI and MCP on the same Core. Preserve user instruction files.

## English and Japanese documentation

Update both language versions in the same PR. Use English in `README.md` and matching `.md` guides,
Japanese in `.ja.md`, and reciprocal links near the title. Match behavior, warnings, defaults,
commands, and the maturity level; do not quietly describe planned features as implemented.

Register human-facing pairs in `docs/languages.json`. Automated checks validate links, pair
presence, and selected obsolete wording; they do not prove translation accuracy. Review meaning.
Executable Skill contracts and raw logs are not duplicated for localization. Original design and
historical records are clearly labeled from the [documentation index](docs/README.md).

Do not publish secrets, personal/customer data, or raw unreviewed logs in issues or PRs.
Use only redacted minimal examples. See [vulnerability reporting](SECURITY.md).
