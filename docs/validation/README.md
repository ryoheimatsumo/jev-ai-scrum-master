# Validation records and provenance

These are **historical, version-scoped test records**, not a statement of current
publication status. Counts and failures/skips describe their original execution.
A record saying “not published” or “SDK unavailable” is not changed retroactively
when GitHub publication or another environment's CI later succeeds.

Current status is in [IMPLEMENTATION_STATUS.ja.md](../IMPLEMENTATION_STATUS.ja.md).
Linux CI for commit `fbf81592248216bcc7e1fc2f4f81d3773b96e4cb` succeeded in
[run #3](https://github.com/ryoheimatsumo/jev-ai-scrum-master/actions/runs/35822543177).
This is not a live Jev, coding-agent, or performance benchmark.

## Public-copy sanitization — 2026-09-23

Selected records have machine-specific directory prefixes and temporary hostnames
replaced with visible placeholders. Test counts, outcomes, skipped reasons, durations,
versions, and original timestamps are preserved. These are no longer byte-identical
raw captures and must not be presented as signed evidence.
See [sanitization.json](sanitization.json) for affected files and content digests.
Old commits retain the original copies; this cleanup does not rewrite Git history.

## Original a1 validation note

# Actual local validation

Report date: 2026-09-23. Version: 0.1.0a1.

**104 passed; 3 skipped; 0 failed, 0 errors (107 collected).** The complete set was executed
in two shards to fit the tool execution limit, with third-party pytest plugin autoload disabled.
Core: 50 passed. Interfaces/judgments/runner: 54 passed, 3 skipped. See the XML and text files.

Skips: official MCP stdio transport and official TypeSafe question schema (SDKs unavailable),
and live Jev (paid call opt-in/key absent). Provider behavior is unit-tested with explicit fakes;
that does not validate real model accuracy. No host Codex/Claude smoke test or GitHub CI ran.

`demo.json` records actual Python test subprocesses in a temporary Git repository: deliberately
broken save, repair, review gate, completion, then stale evidence after an uncommitted change.
Approvals in that recorded demo are explicitly simulated, not real human/AI review.

The wheel built offline successfully. It was installed with --no-deps into a separate target,
and `python -m jev_sm --version/--help` ran with the environment's existing dependencies. This
validates packaged source import/CLI boot, not clean network dependency resolution. A separate
venv without those dependencies could not import PyYAML; no dependency-download success is claimed.
`compileall` and `bash -n scripts/publish-github.sh` succeeded. Ruff was unavailable and not run.

The GitHub publishing script is supplied for execution with the user's authenticated GitHub CLI.
No actual repository, push, PR or GitHub Actions run was created in this environment.
