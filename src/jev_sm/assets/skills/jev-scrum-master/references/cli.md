# CLI contract (0.1.0a4)

Global options precede the command: `jev-sm --repo /ABS/REPO --state-dir /ABS/STATE COMMAND`.
Do not alternate state directories for the same task. The state parent must be outside the repo.
JSON is the default on stdout, one object per operation; errors are JSON on stderr with exit 4.
`report` is explicitly Markdown; `init --yaml` and `--help` are human-readable exceptions.
Argument-parser usage errors exit 2. Ctrl-C exits 130. Never interpret generic exit 0 as PASS.

| Intent | Command |
|---|---|
| Diagnose | `doctor` |
| Create config | `init` (preview), then `init --write` with setup consent |
| Discover tasks | `tasks --limit 20 --offset 0` |
| Read schema | `schema contract`, `schema context`, `schema improvement`, `schema settings` |
| Create task | `prepare 'request' --key KEY` or `prepare --request-file FILE --key KEY` |
| Submit contract | `submit-plan TASK FILE --revision REV --key KEY` |
| Preview plan approval | `approval-preview plan TASK [--task OTHER_TASK ...]` |
| Approve displayed plan in chat | `approve plan TASK [--task SAME_OTHER_TASKS ...] --delegated-chat --expected-hash HASH` after explicit user reply |
| Approve in a terminal | `approve plan TASK [--task OTHER_TASK ...] --version VERSION` (human runs it) |
| Start | `start TASK --revision REV --key KEY` |
| Report progress | `progress TASK 'observation' --revision REV --key KEY` |
| Compact status | `status TASK` (optional `--job-id JOB`; `--full` for diagnostics) |
| Run checks | `verify TASK --revision REV --key KEY` (synchronous) |
| Read evidence | `evidence TASK EV [--artifact NAME --offset N --max-chars N]` |
| Select context | `select-context TASK --input FILE` |
| Bounded advice | `advise readiness TASK`, `advise evidence TASK`, `advise playbook TASK --observation TEXT` |
| Current eligibility | `gate TASK` (0 eligible, 2 unmet, 3 stale, 4 error) |
| Complete | `complete TASK --revision REV --key KEY` |
| Human report | `report TASK` |
| Propose lesson | `propose-improvement TASK FILE --revision REV --key KEY` |
| Find lessons | `rule list --task-id TASK`, `rule candidates --kind feature --path src/file.py` |
| Inspect cache | `cache stats`; `cache clear` previews, `cache clear --write` clears only cache |

FILE can be `-` for stdin on submit-plan, propose-improvement, select-context, --request-file,
and --observation-file. JSON inputs must be objects with unique keys and finite numbers;
unknown fields are rejected. Input byte limits apply before parsing. Read schemas on demand.

Prepare no longer returns the entire schema unless --include-schema is set. Status no longer
returns the entire state unless --full is set. Other a1 command shapes remain available.

Human-only: approve review/protected/criterion/strict, rule approve/retire, and resume confirmation.
Plan approval may use `approval-preview plan TASK [--task OTHER]` followed by exactly one
`approve plan TASK [--task SAME_OTHER] --delegated-chat --expected-hash HASH` after explicit
user chat authorization.
The receipt is agent-mediated chat authorization, not a local TTY or authenticated human receipt.
Ordinary final review remains human-only and may still require the terminal approval path.
There is no --yes, approved=true, actor=human, or DONE override. Existing host sandbox permissions apply.
Prepare one delivery contract for the user's requested Change or milestone when its user stories,
acceptance criteria and checks can be frozen together. Implement and verify small value slices
inside that approved envelope; do not ask for approval after each slice. If separate submitted
plans are intentionally kept, a human can add explicit `--task` values to approve a frozen set
together. The prompt remains readable prose with exact hashes, criteria and case IDs so the
selected scope is reviewable.
The same explicit `--task` selection is available for grouped human `review` approval after
verification. Show one copyable single-line command for terminal-only approvals and wait for
their recorded result; do not poll unchanged approval status or call pending approval a blocked
task. A chat reply authorizes the agent to record the displayed plan only through the delegated
command with the preview hash and identical task selection.
