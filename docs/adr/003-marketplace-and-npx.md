# ADR-003: Marketplace and standard npx distribution

Date: 2026-09-23. Accepted distribution design, not an official store listing.

Use native plugin manifests for Claude Code and Codex. For other local coding agents,
use Vercel's existing `npx skills add` rather than a second custom Node installer or
project-specific npm publication. Let that installer own agent discovery and paths.

The repository's skills/jev-scrum-master must be self-contained: it includes instructions,
references, a Python 3.9+ stdlib launcher and the exact built Python wheel with a digest.
A plugin cache or skills.sh may copy only this folder, so no ../src or repository-root
assumptions are allowed. The Python wheel contains the Skill but not the bundled wheel,
preventing recursive packaging. `build_marketplace.py` and `validate_distribution.py`
ensure source/package parity.

The host asks for first-run setup consent, then executes the launcher. Runtime and optional
Jev SDK installation are separate from project setup, task-plan approval and permission to
call Jev. Nothing installs on plugin load; exec/status never install or update anything.
Runtimes live outside worktrees, keyed by version/content/profile. Host permissions, hooks,
MCP settings and shell profiles are not changed. Runtime metadata is not cryptographic
attestation; same-user adversarial processes are not isolated.

Local code requires POSIX and Python 3.12+. A read-only client without a shell cannot run
Core, even if it can install Skill Markdown. Downloading a Skill is not certification of
agent behavior. All actual host smoke tests remain separately reportable. No benchmark
claims are implied. First-run dependency versions are constrained, not fully locked.

Distribution can be tested locally before GitHub publication. Repository shorthand
commands are not usable until the requested source exists with the bundle on its default
branch; an unmerged implementation PR does not satisfy that requirement. Official public
marketplace acceptance is separate from owning a repo marketplace.
