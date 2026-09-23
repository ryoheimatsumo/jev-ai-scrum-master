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
