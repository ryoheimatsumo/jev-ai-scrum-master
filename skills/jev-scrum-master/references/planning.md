# Planning

Run from the explicit Git worktree root. Initial configuration uses `jev-sm init` to preview
and `jev-sm init --write` after setup consent. Register checks in `.jev-sm/config.yaml` with
explicit argv, parser, report path and limits. Existing configuration is never overwritten.
Review the project's own instructions without rewriting AGENTS.md or CLAUDE.md.

```sh
jev-sm prepare 'Implement the requested observable behavior' --key task-create-01
jev-sm schema contract
# Read assets/plan.example.json only as a SHAPE example; its test IDs are not your tests.
jev-sm submit-plan TASK /outside/repo/plan.json --revision 0 --key plan-01
jev-sm advise readiness TASK
```

`prepare` returns task_id, revision and a schema command, not a long schema by default.
For longer requests use `prepare --request-file /outside/repo/request.txt` or `--request-file -`.
DoR means enough clarity to begin, not eliminating all uncertainty. Read code/specs to resolve
repo questions; make a small technical probe when needed; ask the human only unresolved
product choices. Keep the original requested outcomes. Do not invent API behavior, tests,
source paths, user preferences or a decision that was never made.

If a task is too large, suggest independently verifiable outcomes, preserving a mapping of all
original required criteria. A small task need not be split. Child completion does not complete
the parent; parent integration checks remain required. Implement one task at a time.

A contract has title, kind, goal, in_scope, out_of_scope, criteria and review_profile. Each
criterion defines Given/When/Then and a method. Tests require registered check_ids AND exact
case_ids; for pytest JUnit use `classname::name` from the XML. IDs may refer to tests explicitly
planned for implementation, but must not be presented as existing/passing until run. Process
checks prove only their stated deterministic condition. Subjective criteria are manual.

Prefer one approval envelope for the user's requested change or milestone when its scope,
acceptance criteria and check mappings can be stated and frozen. Keep implementation,
acceptance tests and fixes in small internal value slices without asking for approval for
every slice. A larger or narrower approval unit is always an explicit human choice. When
several already submitted tasks should be accepted together, select those exact task IDs
in one approval.

Keep structured JSON/YAML as the internal submission format. Show the human a concise plan
card instead: the full delivery goal, grouped user stories/value slices, scope and
exclusions, Given/When/Then acceptance criteria with verification, and material risks or
permissions. Do not use raw JSON/YAML as the review artifact.

Obtain the read-only `approval-preview` first and construct the displayed card from its exact
returned details and hash. Wait for the user's explicit reply approving that current card,
then invoke delegated plan approval exactly once with the same selected task IDs:

```sh
jev-sm approval-preview plan TASK [--task OTHER_TASK]
jev-sm approve plan TASK [--task SAME_OTHER_TASK] --delegated-chat --expected-hash HASH
```

If the user chooses terminal approval instead, ask them to run one concise command. Do not
run the terminal approval yourself:

```sh
jev-sm approve plan TASK --version VERSION [--task OTHER_TASK]
```

The terminal approval prompt presents each selected title, goal, scope, Given/When/Then
criteria, checks and case IDs as readable prose, followed by the exact SHA256 challenge.
The preview hash binds selected task IDs, current contracts and versions, sources, config,
full input manifest and protected inputs. A later change to any of these invalidates the
applicable approval. An unselected task still needs its own approval.
A stale hash must be rejected and the card shown again.

After asking for approval, wait for the user's explicit reply or recorded terminal result.
Do not poll unchanged approval status or classify an ordinary pending approval as blocked.
After approval, read `status` once, then `start TASK --revision REV --key start-01`.
Any goal/scope/AC/check/configuration change requires reapproval. Standard is the default.
Light is restricted to human-approved nonbehavioral docs; strict requires additional human
acceptance. A high Jev confidence cannot downgrade review or remove checks.

Review approval is sparse and normally covers the delivery envelope after verification;
it can use the same explicit selection when the human chooses a larger set:

```sh
jev-sm approve review TASK-A --task TASK-B
```

The receipt records agent-mediated chat authorization and never substitutes for protected, strict,
manual-criterion, rule, resume or ordinary independent review approval.

Optional prior lessons: `jev-sm rule candidates --kind feature --path src/file.py`.
Present only related approved hints in the plan. A proposed or irrelevant lesson is not a rule.
