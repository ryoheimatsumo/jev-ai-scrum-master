# Implementation backlog

## Completed in 0.1.0a2

Skill-first CLI coverage, safe packaged Skill installation, compact/stdin JSON interfaces,
persistent advisory cache, and separate-process CLI demo. See ADR-002 and current validation.


## Release-blocking

1. Install and pin tested official MCP/TypeSafe SDK versions; run actual stdio and live Jev
   schema/timeout/retry/usage tests with authorized credentials. Keep raw requested/resolved IDs.
2. Add separate read-only Codex/Claude verifier adapters with strict result schemas, recursive-MCP
   prevention, limited credentials and actual host smoke tests. Preserve human fallback.
3. Implement verifier worker leases and crash recovery (PID reuse, orphan groups, queued/running
   jobs, restart), with human confirmation and no replay of unfinished side effects.
4. Reproducible dependency/environment fingerprint and stale detection for test dependencies;
   explicit external-test environments and expiry; implement artifact deletion invalidation.
5. Per-workspace/task atomic model-budget reservation across processes; actual retry metadata
   if the SDK exposes it; version migrations, retention, interrupted-run diagnostics.
6. Complete P-01..P-28 target-spec matrix, including child-task integration and protected assertion
   weakening review. Harden model-content injection tests and adversarial file TOCTOU scenarios.

## Deeper Jev experiments (opt-in, not implemented)

7. Candidate evidence line-ID selection with independent confirmation of sufficiency.
8. Acceptance-directed mutation/counterexample testing in a sandbox, with clean baseline,
   equivalence/compile-failure handling and explicit execution budget.
9. Compare multiple story/plan candidates; preserve human product decisions and all original AC.
10. Semantic evaluation for LLM output claims grounded in actual supplied data.
11. Retrospective question-set optimization against labeled historical and held-out tasks;
    human promotion, contradiction handling and rollback.

## Demonstrate value, not just calls

Compare baseline coding agent, same managed loop without Jev, and the loop with Jev using equal
budgets and test conditions. Record false-DONE, accepted-task rate, total cost/wall time/human
minutes, unnecessary interventions, regressions and repeated failures. Do not replace required
checks to make latency or token measurements look better. Report unknown quantities explicitly.
