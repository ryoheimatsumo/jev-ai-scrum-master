# Implement and investigate

Use the existing host's permissions to implement the approved plan. Core does not code for you.
`jev-sm progress TASK 'Observed result, not a claim of PASS' --revision REV --key progress-01`
records an untrusted observation. Read status for the current revision after each mutation.

Only when useful, choose a bounded troubleshooting playbook:

```sh
jev-sm advise playbook TASK --observation 'Save returns success; a fresh read has the old value'
```

Alternatively use `--observation-file FILE` or `-` for stdin. CONTINUE means no extra process;
UNKNOWN means investigate instead of forcing a cause. Advice never executes a command.
Do not repeat calls whose inputs are unchanged just to obtain a preferred judgment.

## Select context BEFORE expensive inference

```sh
jev-sm schema context
jev-sm select-context TASK --input /outside/repo/context.json
```

The JSON object contains query, snippets (id/text/mandatory), and optional max_chars.
Mark required acceptance criteria, constraints and critical failures mandatory=true (a real
JSON boolean, not a string). Original snippets remain at the caller so parked IDs can be
expanded. Core retains mandatory/uncertain input, even over budget; it never silently truncates
these snippets. Character counts are not token counts. A disabled/unavailable Jev does not
remove context. Keep raw logs outside the source worktree and do not send secrets.

Jev uses a workspace/task-local SQLite cache for pinned model versions only. Input, contract,
settings, question or model changes produce a different key. TTL/entry limits apply; outages are
not cached. Cached advice is NOT fresh acceptance evidence. No host token or accuracy benefit
has been measured. `jev-sm cache stats` shows entry counts; cache clearing requires --write and
does not delete evidence or the decision audit trail.

Respect Core's finite correction rounds and no-progress stops. Do not retry indefinitely, reset
counters, forge evidence, or relax tests. On a hard interruption, inspect status; this alpha
cannot automatically recover every orphaned RUNNING job. Tell the human rather than modifying
SQLite or replaying unknown side effects. Do not run human-only resume confirmations yourself.
