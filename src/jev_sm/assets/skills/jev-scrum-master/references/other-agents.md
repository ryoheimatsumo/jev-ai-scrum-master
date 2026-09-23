# Other coding agents: the same Skill + CLI

The distribution route is the official Vercel `skills` CLI: `npx skills add SOURCE
--skill jev-scrum-master --agent AGENT`. The installer owns host detection, placement,
copy/symlink behavior, updates and removal. No separate npm package for this project is
required. Do not invent host paths or replace a host's settings. The upstream list of
agent identifiers is https://github.com/vercel-labs/skills#supported-agents.

This Skill has no dependency on Claude-specific tool names, Codex-specific task APIs,
hooks, or MCP. Read local files with the host's read tool and run the bundled runtime
launcher with its shell tool, subject to host permissions. Resolve the actual installed
Skill path from the loaded SKILL.md. Never assume the repository root or a fixed hidden
folder is the Skill's location. Copy installations and symbolic links are supported
by the launcher. Follow references/setup.md for first-run setup.

A host without local shell execution, Git, or a supported Python runtime can read this
Skill but cannot run its Core. Explain the missing capability; never pretend the task
has been verified, and do not install an unrelated MCP or enable broad permissions.
The supported execution target is trusted local POSIX code (Linux tested; macOS needs
a smoke test). Native Windows/Core execution is not supported in this alpha.

An installer accepting an agent ID does not prove the host invoked this Skill, preserved
its instructions, or allowed subprocess execution. Actual agent end-to-end tests remain
separate. Continue preserving human plan approvals and independent review requirements.
Do not start another copy of the task because another host can see the same Skill.
