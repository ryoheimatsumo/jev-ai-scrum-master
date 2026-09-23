"""Reports expose what was verified, and what remains unknown."""
from .common import redact


def render(core, task_id: str) -> str:
    status = core.status(task_id)
    task, gate = status["task"], status["gate"]
    lines = [f"# {task['contract']['title'] if task['contract'] else task['request']}", "",
             f"Task: `{task_id}` | recorded state: **{task['state']}**",
             f"Current completion valid: **{str(status['current_completion_valid']).lower()}**", "",
             "| Criterion | Current result |", "|---|---|"]
    lines += [f"| {key} | {value} |" for key, value in gate["criteria"].items()]
    lines += ["", "## Outstanding conditions", ""]
    lines += [f"- `{issue}`" for issue in gate["issues"]] or ["None within the configured verification scope."]
    lines += ["", "## Execution history", ""]
    for job in task["jobs"]:
        lines.append(f"### {job['id']} — {job['state']}")
        for evidence in job["evidence"]:
            lines.append(f"- `{evidence['check_id']}`: {evidence['outcome']}; evidence `{evidence['id']}`; {evidence['seconds']:.3f}s")
    decisions = status["decisions"]
    tokens = [d["usage"]["input_tokens"] for d in decisions]
    lines += ["", "## Measurement limits", "",
              f"Recorded judgment batches: {len(decisions)}",
              f"Reported Jev input tokens: {sum(tokens) if tokens and all(t is not None for t in tokens) else 'unknown'}",
              "Host model tokens and total cost: **unknown**.",
              "PASS means the approved check succeeded, not a proof that no defects exist.",
              "No merge, deployment, or Jira update is performed.", ""]
    return redact("\n".join(lines))
