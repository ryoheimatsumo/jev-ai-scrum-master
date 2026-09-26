# Security model

[日本語](SECURITY.ja.md)

This alpha manages evidence and workflow checks in **trusted local repositories**.
It is not a hostile-code execution sandbox, tamper-proof audit system, or certification of correctness.

## Execution and approval boundaries

Registered commands run in disposable copies with a reduced environment, a separate HOME,
time/output limits, and process-group cleanup. Copied code can still access the network and
files available to the OS user. It may read credentials from disk even when they are not
inherited as environment variables. Never use production data or credentials for these checks.

Human confirmations are deliberately absent from the MCP surface. For plan approval only, an
explicit chat instruction about the displayed current plan can authorize the agent to record a
hash-bound receipt. That receipt records the agent's assertion of the instruction; Core does not
authenticate the chat speaker. Other approvals still require a local terminal. A same-user
malicious process can emulate that terminal, alter Python/SQLite, or read state. There is no
general model-writable approval, PASS, or DONE override.
Use separately enforced OS users, containers/VMs, filesystem permissions, and network controls
for stronger isolation; this project does not configure them for you.

The Skill is workflow guidance, not enforcement of every host action. The completion gate controls
this tool's DONE state, not arbitrary Git merges, deployments, or commands issued elsewhere.

## Evidence and files

Runner-collected reports are not proof that tests are honest. A malicious test can forge output;
review assertions and the criteria-to-case mapping. Hashes detect changes, not authorship.
Path checks reject traversal and symlinks, XML uses defusedxml, and stale reports are removed before
managed runs. These controls do not fully isolate hostile same-user filesystem races.

Snapshots include dirty/untracked inputs and conservatively invalidate evidence after changes.
Gate checks are not a filesystem lock; recheck at a downstream operation boundary.
Environment fingerprints do not cover every installed dependency, dynamic library, environment
variable, or remote service. Reverify after changes outside the tracked fingerprint.

Known secret paths such as `.env` and private-key extensions are excluded from snapshots.
Exclusions and redaction are best effort, not a complete secret scanner. Tests depending on
excluded credentials, external files, or local editable packages are not fully reproducible.

## Data leaving the machine

Core does not automatically enable external telemetry or Jev. Enabling Jev sends selected
state to TypeSafe's service; obtain permission for that data first. Provider responses, model IDs,
usage, and hashes can be recorded. Provider policies and coding-host data handling are separate.

The third-party Skills installer and package downloads also make network requests.
See the [installer telemetry documentation](https://skills.sh/docs/cli); `DISABLE_TELEMETRY=1`
opts out of its telemetry only. Local-first is not a claim of fully offline inference.

Review logs before sharing them. They may contain source excerpts, personal data, paths, hostnames,
or secrets that heuristic masking missed. Do not publish raw reports, credentials, customer data,
internal URLs, or unredacted reproductions. No cross-project lesson sharing is enabled by default.

## Installation, cache, and recovery

The bundled wheel is checked by version/hash, not a publisher signature. Dependencies are not fully
locked. Install only a reviewed source. The local Skill installer preserves unmanaged/edited files
and does not change host permissions, instructions, MCP, or hooks. Upstream installers have their
own update behavior. Do not mix installation channels.

The advisory cache is task/workspace scoped and keyed by input/contract/config/question/model/backend.
It does not store raw prompts or turn cached advice into PASS, approval, or new test evidence.
Concurrent cold misses may duplicate API requests. Clearing cache preserves evidence/history.

A hard-killed parent can leave a RUNNING job or orphan process. Automatic crash recovery is not
implemented. Preserve state, stop remaining processes, and use a separate workspace for experiments;
do not edit the DB to manufacture DONE. Interrupted Skill updates may require manual inspection.

## Reporting a vulnerability

Do not put exploit details or secrets in a public issue. Use GitHub's private vulnerability reporting
interface **if the repository has it enabled**. Its availability has not been verified here.
Otherwise ask the maintainer for a private contact route with only a non-sensitive description.
No dedicated security inbox or response-time commitment is currently published.

If a real credential was exposed, revoke/rotate it; deleting a file does not remove prior copies
or Git history. This guidance is not a claim that a credential leak has been found.
