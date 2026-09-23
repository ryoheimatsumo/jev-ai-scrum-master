## Summary

Self-contained Skill distribution through Claude/Codex marketplaces and Vercel's standard
`npx skills add` for other local coding agents. Bundled wheel, integrity manifest and
stdlib launcher remove manual clone/venv setup on suitable machines. Runtime downloads
require consent; Jev API/data egress, project checks and task approval remain separate.
No automatic hooks, MCP, permissions or shell-profile changes.

## Verification

See docs/validation/marketplace/ for actual results. Copy/symlink package tests and offline
Python setup are separate from actual npx/agent testing. Fixture dependency wheelhouse is
not an official download. npx fetch is blocked here; manual CI has not run on GitHub.

## Release warning

This PR does not publish npm/PyPI or submit an official marketplace listing. Repo shorthand
install commands require these files on the default branch. No live-agent, Jev API,
quality, speedup or token-savings claims.
