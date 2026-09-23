# Optional MCP adapter

Use only if the user already chose and configured the MCP adapter. The default Skill does
not require a server or the Python mcp extra. CLI and MCP call the same Core and SQLite state;
do not repeat a mutation through both transports with different idempotency keys.

| CLI function | MCP tool |
|---|---|
| prepare | sm_prepare_task |
| submit-plan | sm_submit_plan |
| start | sm_start_task |
| status | sm_get_status |
| evidence | sm_get_evidence |
| progress | sm_report_progress |
| verify | sm_verify_acceptance |
| complete | sm_request_completion |
| propose-improvement | sm_propose_improvement |
| advise readiness | sm_assess_readiness |
| advise playbook | sm_recommend_playbook |
| select-context | sm_select_context |
| advise evidence | sm_map_evidence |

MCP verify returns a job ID immediately; poll sm_get_status while that server remains alive.
CLI verify instead waits for its runner. Both use the same evidence and completion gates.
There is no MCP approval API. A server exposes capabilities, not interception of all edits,
exits or merges. No enforcement Hook is automatically installed by the Skill installer.
