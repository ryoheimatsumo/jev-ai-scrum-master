# Jev configuration and advisory commands

[日本語](JEV.ja.md)

The default Skill calls the CLI; no MCP server is required. Jev is an external API and is
optional. The Core still manages checks, reviews, evidence, and completion when Jev is disabled.

## Enable only after reviewing data

In a source installation, install the optional dependency in the same environment as the CLI:

```sh
python -m pip install -e '.[jev]'
```

For a bundled installation, ask the Skill to preview and set up Jev SDK support through its
launcher instead. Set `TYPESAFE_API_KEY` in your own environment, never in chat, Skill text,
version control, or project YAML. Review permitted code/log excerpts and set `jev_enabled: true`
in `.jev-sm/config.yaml`. SDK installation alone does not enable calls. Configuration changes
require existing task plans to be reviewed and reapproved.

The Core tries to redact known secret values before API submission; redaction is not complete
DLP. Your host's data handling is separate. See [security](../SECURITY.md).

## What each command does

These command forms require a real TASK ID. Run at the target Git root or pass `--repo` before
the subcommand. Keep payload files outside the tracked source snapshot.

```sh
jev-sm advise readiness TASK
jev-sm advise playbook TASK --observation-file /OUTSIDE/REPO/observed.txt
jev-sm select-context TASK --input /OUTSIDE/REPO/context.json
jev-sm advise evidence TASK
jev-sm cache stats
```

| Command | Meaning |
|---|---|
| `advise readiness` | Classify gaps and the observability of the proposed criteria. |
| `advise playbook` | Suggest continuing, investigating a minimal case/environment/persistence/contract, asking a person, or retaining uncertainty. |
| `select-context` | Suggest which input items are relevant; mandatory and uncertain material stays available. |
| `advise evidence` | Suggest relationships between registered evidence and acceptance criteria. |
| `cache stats` | Inspect the advisory cache, not test coverage or completion. |

Use `schema context` for the input format. Mark acceptance criteria, constraints, and critical
failures `mandatory: true`; retain original material for later expansion. Counts describe
characters, not measured model tokens. No accuracy, speedup, or host token savings are promised.
Jev chooses bounded categories; the host creates plans, explanations, and code.

## Failure and authority

Unknown, low-confidence, and unavailable judgments are advice states, not permission to skip
checks. A Jev response cannot grant PASS, approve a person-only action, weaken the plan, or
complete a task. A confidence value is not an observed correctness rate. Required reviews remain.

## Cache

Defaults: 86,400 seconds and at most 512 entries per workspace. Only explicit `jev-X.Y.Z` model
versions are cacheable; aliases such as `jev-latest` are not. Keys include task, contract,
configuration, backend/model, question version/content, and input hashes. Failures are not cached.
Original input is hashed rather than retained as a raw prompt in the cache.

A hit means no new provider call for that advice, not new verification. PASS, approvals, and
execution evidence are never substituted by cached advice. Concurrent cold misses may still
make duplicate calls; cross-process atomic provider-budget reservation is not implemented.

Set `jev_cache_ttl_seconds: 0` or `jev_cache_max_entries: 0` to disable caching.

```sh
jev-sm cache clear
jev-sm cache clear --write
```

The first command previews; the second clears advisory entries, not evidence or decision history.
Pre-a2 tasks need configuration review and reapproval because normalized defaults changed.

Experimental mutation testing and automatic question optimization are [backlog items](BACKLOG.md),
not features hidden behind these commands.
