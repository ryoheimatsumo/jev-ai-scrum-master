# Skill-first local validation — 0.1.0a2

> Historical execution record. Publication and SDK availability statements describe that run only. See [current implementation status](../../IMPLEMENTATION_STATUS.ja.md) and [record provenance](../README.md).

2026-09-23 / Linux / Python 3.13.5. **167 passed, 3 skipped (170 total).**
The original tests remain and 63 new cases cover CLI/Skill/cache changes. Full-suite result is
in `tests.txt` and `tests.xml`; command/exit status in `test-process.json`. External pytest
plugins were disabled for a reproducible local run. The live API opt-in was unset.

## Recorded checks

- `tests.txt`, `tests.xml`: real complete pytest run, exit 0. Includes a separate-process
  cache test with a fixture provider and a complete real-CLI subprocess demo test.
- `cli-demo.json`: 28 real CLI subprocesses, no MCP server, for install/prepare/plan/test/
  evidence/complete/retrospective/staleness. Human confirmations explicitly simulated.
- `core-demo.json`: earlier Core demonstration rerun against a2, same explicit simulation.
- `wheel-smoke.json`: built and installed base wheel outside the source tree. Runtime
  dependencies reused from the preinstalled environment via a local .pth (offline), not a
  fresh online dependency-resolution test. Verified resource loading, 10 packaged Skill files,
  actual console command, Claude project Skill placement, init/doctor/prepare/status with no
  mcp or typesafe_sdk installed. Placement is not actual Claude host discovery/execution.
- `summary.json`: counts, groups, unchanged-original-spec check and outstanding validations.

## Skipped / not claimed

1. Official MCP stdio handshake: optional SDK unavailable locally.
2. Official TypeSafe SDK schema check: optional SDK unavailable locally.
3. Live Jev call: SDK/authorized key/explicit opt-in unavailable; no paid API call made.

No Codex/Claude runtime was launched. No independent AI review, performance benchmark or
GitHub CI run is claimed. The demos are actual CLI/Runner execution but **not** human approval
provenance, an actual AI coding task, Jev correctness, or quality/latency/token improvements.

## Reproduce

```sh
python -m pip install -e '.[dev]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --junitxml=test-results.xml
python scripts/sync_skill_assets.py --check
python scripts/demo_cli.py --simulate-approvals
python scripts/demo.py --simulate-approvals
```

Installing extras may make SDK tests runnable; keep live billing opt-in separate. Install
checks are intentionally preview-first and the smoke test modifies only a temporary project.
The stored wheel SHA identifies the built package; compare against the distributed wheel.
