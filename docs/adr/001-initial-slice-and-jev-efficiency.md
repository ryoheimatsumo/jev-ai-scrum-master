# ADR-001: initial vertical slice and Jev efficiency layer

Status: initial implementation, 2026-09-23. The original v1.0 specification remains unchanged.

We implement evidence/approval/state invariants first and provide a usable CLI plus a stdio MCP
adapter. Planning and free-form improvements remain host-generated through schemas and a Skill.
The first release is 0.1.0a1, not the specification's complete beta.

Later discussion adds three advisory paths: context selection before host inference, batched
readiness/evidence judgments, and bounded playbook selection. Status is compact; integrity-checked
evidence is read on demand. A failed/uncertain Jev response never drops mandatory inputs or grants
completion. Context counts are characters; host tokens, total latency and dollar savings remain
unknown until measured. Repeated calls are cached only with pinned model/question/input versions.

The fallback reviewer is an explicit human TTY attestation; automatic Codex/Claude independent
review remains unfinished. This is a deliberate safe limitation, not simulated AI independence.

Mutation testing, plan candidate tournaments, semantic generated-output evaluations, and learning
better question sets are separate future experiments. They are not hidden additions to mandatory
work, and their benefits must be compared with the same process without Jev.

Boundaries: one worktree task; local trusted code; no network sandbox; no universal host hooks;
no remote action tools. Dead verifier job recovery and comprehensive environment hashes remain
release blockers. API failures and missing evidence must surface visibly rather than complete.
