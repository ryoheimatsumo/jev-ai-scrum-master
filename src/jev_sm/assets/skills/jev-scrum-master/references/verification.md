# Verify, then request completion

```sh
jev-sm status TASK
jev-sm verify TASK --revision REV --key verify-01
jev-sm status TASK
```

`verify` is synchronous and runs all registered checks required by the approved contract and
DoD. It exits when the owned runner finishes. A CLI exit 0 means the operation returned a
result, NOT that tests passed. Inspect the returned gate and criterion statuses.

Status is compact and lists evidence IDs. Fetch only the relevant detail:

```sh
jev-sm evidence TASK EVIDENCE_ID
jev-sm evidence TASK EVIDENCE_ID --artifact NAME_FROM_METADATA --offset 0 --max-chars 6000
```

Use next_offset for more. Artifact names must come from metadata, not invented paths. Reads
verify hashes. A historical report is not proof about current code. Avoid `status --full`
unless explicitly debugging local state. `report TASK` emits Markdown for a human.

`advise evidence TASK` is optional Jev relationship analysis, not a correctness certificate.
Test names do not prove assertions; verify the actual assertions and observations. Do not infer
real persistence from a mocked call or stable UI. Zero tests, missing reports, required skips,
wrong case IDs, failed checks or stale snapshots cannot pass. Changes after tests require fresh
verification, including uncommitted and relevant untracked inputs.

The alpha has no automatic independent Codex/Claude reviewer. After passing checks, give a
real person the report, source/assertions and required approval commands returned by gate.
Examples of human-only commands (NEVER simulate or execute these on their behalf):

```sh
jev-sm approve protected TASK  # only if gate requires protected-change review
jev-sm approve review TASK
jev-sm approve criterion TASK --ac AC_ID  # manual criteria only
jev-sm approve strict TASK    # only for strict tasks
```

Once those are recorded, read status and run:

```sh
jev-sm gate TASK
jev-sm complete TASK --revision REV --key complete-01
```

Gate exit codes: 0=eligible, 2=unmet/waiting, 3=stale, 4=execution/input error.
Only complete with state DONE and eligible=true represents this tool's completion. Any code
change can invalidate it again. Never equate DONE with merging, deploying or no unknown defects.
If blocked, return exact unmet criteria and preserve the evidence. Do not weaken the contract.
