# Maintainer release guide

[日本語](PUBLISHING.ja.md)

The repository is already public. Normal changes use a branch, reviewed PR, passing checks, and
then an intentional merge. Tags, releases, package publication, and marketplace listing are separate
actions, not side effects of editing a README.

## Before a release

Run tests and documentation checks from the source checkout:

```sh
python -m pytest -q
python scripts/check_public_docs.py
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
```

When changing runtime code or canonical machine Skill assets, update versions deliberately and rebuild
before running the final distribution validation:

```sh
python scripts/build_marketplace.py
python scripts/validate_distribution.py
```

Review package metadata, plugin manifests, source/wheel parity, hashes, and the changelog in both
languages. Building a wheel changes distribution bytes; do not publish an unreviewed artifact.
A docs-only change need not rebuild the a3 wheel. Its embedded metadata remains the original
build's description, not the current website or current compatibility claim.

Test actual installation in a disposable project with a reviewed, available installer version.
The existing smoke helper requires explicit `--write --allow-downloads`; inspect its help and
selected version before executing. Placement checks, host execution, and live Jev evaluation
are separate tests. Never fill a missing result with an assumed success.

## Initial-publication helpers are historical

`scripts/publish-github.sh`, `scripts/publish_public.py`, and `PUBLICATION_MANIFEST.json` were
created for the initial upload. They reject existing repositories and are not a release/update path.
The manifest hashes describe the original publication snapshot, not the continually edited main
branch. Do not regenerate them simply to make a changed tree pass as the original snapshot.
Associated tests exercise that helper with local fixtures.

These helpers remain for reproducibility; no normal user should run them to install the Skill.
Any future removal must update the associated tests and historical references together.

## Public claims and privacy

Keep experimental-alpha status until actual release criteria are met. Distinguish CI, installer
placement, host integration, and measured quality/speed/token results. Do not claim official
marketplace approval, vendor endorsement, full isolation, or comprehensive security review.

Never publish API keys, private customer examples, local execution databases, or unreviewed logs.
Review credential and personal-data candidates without copying secret values into reports.
Do not force-push or rewrite public history as an ordinary release operation.

[Contributing](../CONTRIBUTING.md) · [Distribution](DISTRIBUTION.md) · [Security](../SECURITY.md).
