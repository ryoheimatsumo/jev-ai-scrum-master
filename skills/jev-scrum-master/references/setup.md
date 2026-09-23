# Marketplace first-run setup

The Skill includes its own versioned CLI wheel. Do not ask the user to clone the repo,
activate a virtualenv, run pip manually, or add MCP. This is still experimental local software,
not a zero-dependency cloud service. Git is required. The launcher works on Python 3.9+;
the CLI needs Python 3.12+. If a suitable Python is missing, an already installed uv can
prepare Python after explicit download consent. Never silently install uv, Homebrew, or Node.
Native Windows/Core execution is unsupported. Linux is tested; macOS and all actual host applications still need smoke tests.

## Locate and inspect

Resolve `<SKILL_ROOT>` to the directory of this loaded SKILL.md, not the target project's
root. Use an absolute path; marketplace caches, symlinks, and spaces in paths are normal.
If this is a skills-only copy, the launcher and wheel are still inside it.

```sh
python3 "<SKILL_ROOT>/scripts/runtime.py" status --with-jev
python3 "<SKILL_ROOT>/scripts/runtime.py" setup --with-jev
```

These are read-only previews and do not call Jev. If Python is missing completely, explain
that Python or a user-approved Python installation is needed. Do not pretend setup succeeded.

## One setup confirmation

Explain what is being installed: this bundled CLI, its Python dependencies from PyPI, and
(optional) the TypeSafe SDK. Installation uses a dedicated user-data environment outside
the project; it does not alter global Python, shell configuration, host permissions or MCP.
A sufficiently old Python may require uv to download a newer interpreter. Offer base mode
without the Jev SDK when the user does not intend to use Jev. Do not request an API key in chat.
After the person consents to the setup action, run:

```sh
python3 "<SKILL_ROOT>/scripts/runtime.py" setup --with-jev --write --allow-downloads
```

For base mode omit `--with-jev` on all launcher commands. For offline installation use
`setup --write --wheelhouse /absolute/prepared/wheels` instead of `--allow-downloads`.
The wheelhouse must contain all dependency wheels for the active Python/platform.
An installation failure or hash mismatch is not permission to bypass validation or install
another package named similarly. Stop and report the structured error.

## Use the selected launcher, not PATH

Replace every `jev-sm ...` in this Skill's other references with:

```sh
python3 "<SKILL_ROOT>/scripts/runtime.py" exec --with-jev -- ...
```

For example:

```sh
python3 "<SKILL_ROOT>/scripts/runtime.py" exec --with-jev -- --repo /absolute/project doctor
```

`exec` never installs, upgrades or downloads. It runs the exact runtime matched to this
Skill's wheel. Reusing it works across sessions and cache relocations. A Skill update with
a changed bundle requires a new setup confirmation, while old environments remain intact.
For approval commands shown by Core, show the person the same launcher prefix followed by
the unchanged approval arguments. The person runs those commands themselves. Setup consent
is NOT task-plan approval and is NOT authorization to auto-enter TTY approvals.

## Configure the project once

Run `init` as a preview. Explain the change before `init --write`. Inspect the project's
existing manifests/docs to propose real check commands and report formats; never label the
placeholder check as a validated project test. Do not install project dependencies or run
unreviewed scripts during detection. Review commands with the person before task approval.
This setup code does not automatically register test commands.

The Jev SDK alone does not enable network requests. The person sets `TYPESAFE_API_KEY` in
the host environment or an approved secret store, never in this Skill/config/repository.
Never print it. Explain what code/log excerpts leave the machine and the API cost; change
`jev_enabled` only after the person opts in. Existing task plans may need reapproval when
project config changes. Base mode is usable without any API key.

## Updates and removal

Use the same installer/channel that installed this Skill; do not run the legacy `skill
install` updater against a marketplace/skills.sh-managed copy. Do not overwrite local edits.
A launcher hash mismatch means the bundle is damaged or altered; reinstall from a trusted
source. Hashes detect mismatches, not publisher authenticity. Package dependencies currently
use the Core's declared constraints, not a cross-platform locked and signed supply chain.
Uninstalling the Skill does not delete task state, evidence, credentials or runtime data.
Use status to show the exact runtime path before a person removes unused environments.

## npx distribution is separate from runtime activation

`npx skills add` installs this entire directory, including runtime/ and scripts/. It does
not run setup or grant permission to download Python packages. After install/reload the
user asks this host to set up `jev-scrum-master`; then follow this document. The installer
requires Node/npm. A Python 3.12+ runtime and project dependencies remain necessary to run
Core. Never claim Node alone is enough to run the Python verification engine.

Do not install both a marketplace plugin and a skills.sh copy for the same host. To
update/remove a skills.sh installation, use the `skills` CLI rather than this project's
legacy `skill install`. Installer updates may overwrite Skill files: keep custom changes
in a separate fork, and back them up before updating. Removing a Skill does not erase
project task history, runtime environments, or credentials.
