# Public-content review — 2026-09-23

[日本語](PUBLICATION_REVIEW.ja.md)

## Scope

Reviewed the main snapshot at `fbf81592248216bcc7e1fc2f4f81d3773b96e4cb`: 122 tracked files,
including source, tests, Skill instructions, manifests, CI, examples, documentation, and reports.
Also inspected 34 entries inside the bundled wheel. Source/Skill/script/test subtree hashes were
matched to the live repository; the latest public documentation and CI status were read separately.
This is a content/exposure review, not a penetration test, legal clearance, or exhaustive security audit.
It does not cover every historical commit, external fork/cache, issue, CI log, installed dependency,
or future execution.

## Findings and changes

- No actual credentials were identified by the applied patterns and manual review of matches.
  Checked representative private-key, GitHub token, AWS access-key, Google API-key, and model-key
  forms, committed secret/runtime paths, and email/path candidates. This is not proof that all
  secret formats are absent. Existing test email addresses use the reserved `example.invalid` domain.
- Quickstart still duplicated pre-publication material and used an unresolved owner placeholder.
  Replaced it with the real public install path and a task-oriented guide.
- Current instructions and historical validation were mixed. Current status now distinguishes
  verified GitHub CI from old local reports; historical evidence remains unmodified.
- Clarified that a copied workspace is not a sandbox, advisory Jev results cannot grant PASS,
  and standard tasks still need a person. Did not remove limitations to make the product appear mature.
- Distinguished this project's default telemetry behavior from the external installer/host/API.
  Added a clear independent-project statement without implying vendor endorsement.
- Added English/Japanese human-facing pairs and checks for missing pairs, broken local links,
  language drift, and selected obsolete onboarding phrases.

## Validation of this revision

Local full test suite: **264 passed, 3 skipped**. The skipped tests require the optional MCP
SDK, TypeSafe SDK, or explicitly authorized live Jev access. The 13 documentation regression
cases ran successfully. Language-pair checks, local links, Skill mirror consistency, and bundled
wheel/source validation also passed. No live host or paid model evaluation was performed.
Remote CI for this revision must be read from the PR checks; a local pass is not a remote CI result.

## Preserved boundaries

No runtime behavior, approval logic, executable Skill text, package version, binary wheel, or
historical test output is changed by this documentation revision. The bundled wheel's metadata
is build-time material. The initial-publication hash manifest is historical, not a current release
manifest. The original target specification is an archived design record, not a completion claim.

The review did not find a need to expose any sensitive value in a public finding. Future genuine
leaks require revocation/rotation and review of prior copies, not just deletion from the latest tree.
[Security reporting](../SECURITY.md) · [Language and scope policy](README.md).
