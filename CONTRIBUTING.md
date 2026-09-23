# Contributing

This is an experimental alpha. Improvements to reliability, honest documentation,
and reproducible tests take priority over new autonomous behavior.

Use Python 3.12+ in a virtual environment:

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
python scripts/check_public_content.py
```

MCP and TypeSafe extras are optional. Their contract tests require `.[mcp,jev]`;
live Jev tests also require explicit permission and credentials. Do not enable paid
API tests or paste credentials into issues/PRs. Fixture tests are not live-model benchmarks.

## Changes and releases

Open a focused branch and PR with test results and limitations. Use the
[maintainer guide](docs/PUBLISHING.ja.md) for versioned distribution changes.
Do not re-run the historical first-publication helper to update this repository.

Edit canonical Skill resources under `src/jev_sm/assets/skills/jev-scrum-master`,
then synchronize the discoverable mirror. Runtime/Skill changes require a new
versioned wheel and integrity checks; do not silently replace an existing release.
Do not duplicate approval or completion logic between CLI and MCP.

## Reporting and claims

Public examples must be synthetic. Review logs for credentials, customer data,
email addresses, machine paths, and hostnames before sharing. Sanitized reports
must say what was changed without altering test outcomes. Keep failed/skipped tests visible.

Security reports follow [SECURITY.md](SECURITY.md), not a public exploit report.
Claims about correctness, speed, cost, and tokens need matched end-to-end measurements.
Distribution support is not proof of host compatibility. A test copy is not a security sandbox.

The approved v1.0 specification is a design target, not a feature-completeness claim.
Preserve the current completion/approval gates and include regressions for changes to them.
