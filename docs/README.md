# Documentation

[日本語](README.ja.md)

User-facing and maintainer guides are paired. Use the language link at the top of each page;
English navigation leads to English guides and Japanese navigation to Japanese guides.

| Guide | English | 日本語 |
|---|---|---|
| Overview | [Read](../README.md) | [読む](../README.ja.md) |
| Quickstart | [Read](QUICKSTART.md) | [読む](QUICKSTART.ja.md) |
| Installation / updates | [Read](DISTRIBUTION.md) | [読む](DISTRIBUTION.ja.md) |
| Jev configuration | [Read](JEV.md) | [読む](JEV.ja.md) |
| Architecture | [Read](ARCHITECTURE.md) | [読む](ARCHITECTURE.ja.md) |
| Implementation status | [Read](IMPLEMENTATION_STATUS.md) | [読む](IMPLEMENTATION_STATUS.ja.md) |
| Backlog | [Read](BACKLOG.md) | [読む](BACKLOG.ja.md) |
| Security | [Read](../SECURITY.md) | [読む](../SECURITY.ja.md) |
| Contributing | [Read](../CONTRIBUTING.md) | [読む](../CONTRIBUTING.ja.md) |
| Maintainer releases | [Read](PUBLISHING.md) | [読む](PUBLISHING.ja.md) |
| Host integration | [Read](../integrations/README.md) | [読む](../integrations/README.ja.md) |
| Changelog | [Read](../CHANGELOG.md) | [読む](../CHANGELOG.ja.md) |
| Validation context | [Read](validation/INDEX.md) | [読む](validation/INDEX.ja.md) |
| Public-content review | [Read](PUBLICATION_REVIEW.md) | [読む](PUBLICATION_REVIEW.ja.md) |
| Pull request guidance | [Read](PULL_REQUEST.md) | [読む](PULL_REQUEST.ja.md) |

## Deliberately single-source records

The [original v1.0 specification](spec/v1.0.ja.md) is a frozen Japanese design record, not a current
feature claim. It is not a translated user guide. English readers should start with architecture,
current status, and the backlog above. [ADR-001](adr/001-initial-slice-and-jev-efficiency.md),
[ADR-002](adr/002-skill-first-cli.md), and [ADR-003](adr/003-marketplace-and-npx.md) remain historical
English decisions; their current implications are covered by both architecture guides.

The executable [Skill](../skills/jev-scrum-master/SKILL.md), its [CLI contract](../skills/jev-scrum-master/references/cli.md),
source identifiers, and raw JSON/XML/text reports keep their original English/machine format.
They are not two alternative implementations. Historical test evidence is not edited or translated
as if it were a new run. The [LICENSE](../LICENSE) remains the authoritative Apache-2.0 text.

## Keeping the guides aligned

Use `.md` for English and `.ja.md` for Japanese; register pairs in `languages.json`.
Changes to instructions, safety, defaults, or maturity must update both. Run
`python scripts/check_public_docs.py` from the repository root. Automated link/language checks
cannot verify semantic equivalence; maintainers must review the actual translations.
