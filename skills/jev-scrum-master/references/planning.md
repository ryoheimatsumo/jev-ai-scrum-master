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

Ask the human to run (do NOT run it yourself):

```sh
jev-sm approve plan TASK --version VERSION
```

Read `status` again, then `start TASK --revision REV --key start-01`. Any goal/scope/AC/check/
configuration change requires reapproval. Standard is the default. Light is restricted to
human-approved nonbehavioral docs; strict requires additional human acceptance. A high Jev
confidence cannot downgrade review or remove checks.

Optional prior lessons: `jev-sm rule candidates --kind feature --path src/file.py`.
Present only related approved hints in the plan. A proposed or irrelevant lesson is not a rule.
