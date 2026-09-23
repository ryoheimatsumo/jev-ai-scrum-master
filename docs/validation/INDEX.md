# Validation records

[日本語](INDEX.ja.md)

This index distinguishes historical evidence from current status. Raw JSON/XML/text is intentionally
not translated or rewritten: altering an execution record would obscure what was actually measured.
Paths and machine identifiers in old records are disposable test-environment metadata, not credentials.
Review any new log before publication.

| Record | What it measured | Original language |
|---|---|---|
| [a1](README.md) | 104 passed, 3 skipped, in two shards; simulated-approval demo. | English |
| [Skill-first a2](skill-first/README.md) | 167 passed, 3 skipped; separate CLI processes and fixture cache. | English |
| [Distribution a3](marketplace/README.md) | 233 passed, 3 skipped; local bundle/bootstrap; npm retrieval failed. | Japanese |
| [Initial publication helper](publication/README.md) | 18 focused local tests; fake GitHub and a local bare Git remote. | English |

The skipped original tests required optional SDKs or explicitly authorized live Jev access.
Those historical reports do not assert the state of current SDK availability, GitHub publication,
or every later CI run. Statements about the author's then-current tool access are not product restrictions.

The main commit `fbf8159` has a successful [GitHub Tests run](https://github.com/ryoheimatsumo/jev-ai-scrum-master/actions/runs/35822543177).
No installer-host end-to-end or Jev-quality benchmark follows from that fact. Consult
[current status](../IMPLEMENTATION_STATUS.md) and a PR's actual checks separately.

Simulated approvals, fake providers, local package fixtures, and installer placement must never
be described as genuine human approval, actual model performance, official dependency downloads,
or successful execution inside a coding agent.
