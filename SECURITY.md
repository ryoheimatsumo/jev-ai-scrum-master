# Security model and alpha limitations

This software is designed to reduce accidental stale approvals, unsupported completion claims,
and common workflow mistakes; it does not guarantee their absence. It is **not a hostile-code execution sandbox or tamper-proof audit system**.

- Use only trusted repositories. Commands run in disposable copies with minimized environment,
  isolated HOME, no inherited model/cloud keys, output/time limits, and process-group cleanup.
  Copied source can still open network connections and access files available to the same OS user.
- CLI confirmations are interactive and unavailable over MCP. A same-UID process can emulate a
  terminal, alter Python/SQLite, or read state. High-assurance deployment needs distinct users,
  filesystem access controls, containers/VMs and network policy not implemented here.
- Test reports are Runner-collected, not cryptographic attestations of test honesty. The human
  substitute reviewer must inspect assertions and tests. A malicious test can forge its output.
- Paths are confined, symlinks rejected, XML parsed with defusedxml, pre-existing reports removed.
  File hashes bind source/test/config bytes and artifacts, including dirty/untracked source.
  The manifest and SQLite transaction are not a filesystem lock against concurrent edits; gate
  checks current content before/after evaluation, and should be rerun at any downstream boundary.
- Source references are hashed into a contract and require new approval when changed. All source
  content changes conservatively invalidate final evidence. Required test edits trigger protection.
- The environment fingerprint covers OS/runtime and executable content, not every installed
  dependency, dynamic library, environment variable or external service. Reverify after any such
  change; reproducible dependency/container fingerprints remain release-blocking follow-up work.
- `.env*` (except `.env.example`), private-key extensions and explicit cache/dependency directories
  are not copied. If a check depends on excluded secrets, local editable installs, external files,
  or production credentials, this alpha cannot claim a complete reproducible verification.
- Jev calls are opt-in; no secret .env loading or automatic external telemetry. API responses,
  requested/resolved model IDs, observed usage and hashes are recorded. Free text exceptions from
  providers are not logged. Redaction is heuristic; review permissible input before enabling.
- Context filtering is advisory. Mandatory input must be declared by the caller; no summary is
  allowed to replace the contract, an actual log, the full test result or a required review.
- A hard-killed parent may leave a RUNNING job or orphan process. Automatic stale-job recovery is
  not implemented. Stop remaining processes, preserve state, and use an isolated new workspace
  for experiments. Do not edit the DB to manufacture DONE. This limitation blocks production beta.
- No automatic mutation execution, code deployment, permission escalation, forced merges,
  approval override or autonomous executable learning rules are included.

Do not upload secrets in public bug reports. Share only a minimal redacted reproducer with the
repository owner through an agreed private channel; no security inbox is provisioned by this code.

## Installer boundaries

The first-party `jev-sm skill install` installer writes only the selected Skill directory; it does not modify host configuration,
MCP registration, user instruction files or permissions. Updates require unchanged installer-owned
files, an explicit update flag and explicit write. A cooperative lock prevents overlapping installers;
hard power loss during the replacement can leave a hidden backup/lock for manual inspection.
It rejects symlink paths and refuses custom files. Same-user hostile filesystem races are not isolated.
These first-party overwrite protections do not describe Vercel `skills` or host marketplace updaters.
Those third-party installers have their own permissions, update behavior, and telemetry settings.

Persistent Jev cache entries are advisory only, keyed by original-input hash and redacted state,
contract/config/question/model/backend/task, with TTL and bounded entries. No raw prompt is stored.
Clearing cache preserves evidence and audit. Concurrent cold misses can still produce duplicate
provider calls. Never interpret cached advice or confidence as a fresh PASS/approval.

## External services and local storage

“Local” describes task storage and command execution, not a promise of offline inference.

| Component | Possible data movement |
| --- | --- |
| Host coding agent | May send repository context, tool output, and conversations to its provider under host settings |
| Jev (opt-in) | Sends selected plan/code/log inputs to TypeSafe; heuristic masking is not guaranteed secret removal |
| Skill/runtime installation | Contacts GitHub/npm/PyPI and possibly interpreter-download services after the relevant setup consent |
| Local state/artifacts | Stores task text, evidence, decisions, and approvals, which may contain confidential project information |

The project does not intentionally send analytics by default. This does not control telemetry
from installers, SDKs, or coding hosts. Their terms, retention, and training policies are separate.
Do not assume disabling Jev disables the host's network access or data sharing.

## Reporting a vulnerability

Do not post secrets, customer data, or exploit details in a public issue. If GitHub shows
**Security → Report a vulnerability**, use that private reporting channel. If it is not
available, ask the maintainer to establish a private channel without including sensitive details.
This repository does not currently promise a staffed security inbox or response SLA.
A leaked credential needs revocation/rotation; removing it from a current file is insufficient.

## What the public-content check does not prove

The offline checker flags selected credential formats, tracked secret-like filenames, and
machine-specific metadata in committed validation records. It also inspects wheel/ZIP text.
It is a hygiene regression check, not a full secret scanner, dependency advisory scanner,
penetration test, license clearance, or complete review of Git history and external artifacts.
