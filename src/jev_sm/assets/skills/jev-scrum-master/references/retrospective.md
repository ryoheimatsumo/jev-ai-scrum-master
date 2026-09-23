# Evidence-based retrospective

Use actual contract changes, failures, retries, human intervention and final results.
Never retrieve or store private hidden reasoning. Separate observed facts from causal hypotheses.
The goal is fewer repeated failures, not a generic reflection essay or extra ceremony.

Propose at most three small scoped lessons. A proposal includes title, hypothesis,
proposed_action, task_kinds, path_globs, evidence_ids, positive_example, negative_example and
an action_kind of planning_hint or verification_candidate. See:

```sh
jev-sm schema improvement
jev-sm propose-improvement TASK /outside/repo/proposal.json --revision REV --key retro-01
jev-sm rule list --task-id TASK
```

Use real evidence IDs belonging to this task. Examples are proposed examples, NOT completed
experiments unless they were actually run and recorded. Rules remain PROPOSED and nonbinding.
Only a human runs `jev-sm rule approve RULE_ID` or `jev-sm rule retire RULE_ID` after review.

In a future task, `rule candidates --kind KIND --path PATH` returns only scope-matched,
approved candidates. Include useful ones in the new human-approved plan; do not silently change
an existing contract. No lesson may execute arbitrary code, expand permissions, remove checks,
weaken acceptance criteria or rewrite Core. Automatic question optimization and mutation
experiments are not implemented. Failure to create a retrospective does not undo valid DONE.
