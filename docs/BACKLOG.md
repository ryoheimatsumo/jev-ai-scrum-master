# Backlog

[日本語](BACKLOG.ja.md)

These are planned tasks, not available features. [Current status](IMPLEMENTATION_STATUS.md).

## Reliability before a production beta

1. Pin tested SDK/host combinations and exercise authorized live Jev schema, timeout, retry,
   and usage behavior. Preserve requested/resolved model IDs and honest unknown quantities.
2. Add isolated, read-only Codex/Claude review adapters with strict output schemas, no recursive
   MCP, limited credentials, and host smoke tests. Preserve the human fallback.
3. Implement job leases and crash recovery, including orphan processes/PID reuse and queued or
   running jobs, without replaying unfinished side effects without approval.
4. Improve dependency/environment fingerprints, remote-test expiry, and evidence deletion handling.
5. Reserve model budgets atomically across processes; manage migrations, retention, and interrupted runs.
6. Complete the target P-01 through P-28 matrix, including child-task integration and protected
   assertion-weakening review. Add injection and concurrent-filesystem-race tests.

## Optional Jev experiments

Evidence line-ID selection with independent sufficiency review; acceptance-directed mutation
checks in isolated environments; multiple plan candidates; grounded semantic evaluation of LLM
outputs; question-set improvement on labeled history and held-out tasks. These experiments must
not silently add required work or relax current approvals, limits, or completion conditions.

## Measure value

Compare a baseline agent, the same managed loop without Jev, and the loop with Jev under matched
budgets and tasks. Measure false DONE, accepted tasks, total cost/time/human effort, unnecessary
interventions, regressions, and repeat failures. Include all trials and skipped checks.
Do not claim savings from character counts or measure only the successful examples.

## Documentation maintenance

Keep language pairs, live status, installation commands, and safety claims aligned. Historical
specifications and reports must be identifiable as historical, rather than rewritten as new results.
