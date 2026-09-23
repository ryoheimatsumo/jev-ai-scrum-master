#!/usr/bin/env python3
"""Publish the reviewed alpha snapshot as a NEW public repository.

Python 3.9+ standard library only. Default is an offline preview. No credential
is read or printed by this script; authenticated GitHub CLI owns authentication.
Existing repositories are never updated, made public, overwritten, or deleted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "PUBLICATION_MANIFEST.json"
EXPECTED_REPOSITORY = "ryoheimatsumo/jev-ai-scrum-master"
REQUIRED = {
    "README.md", "LICENSE", "pyproject.toml", "skills/jev-scrum-master/SKILL.md",
    "skills/jev-scrum-master/runtime/manifest.json", ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json", ".agents/plugins/marketplace.json", "plugin.json",
}
DENIED_PARTS = {".git", ".ssh", ".aws", ".gcloud", ".venv", "venv", "__pycache__", ".pytest_cache"}


class PublishError(RuntimeError):
    pass


def load_snapshot(root: Path):
    raw = (root / MANIFEST_NAME).read_bytes()
    doc = json.loads(raw)
    if doc.get("schema_version") != 1 or doc.get("repository") != EXPECTED_REPOSITORY:
        raise PublishError("Unexpected publication manifest or destination.")
    if doc.get("visibility") != "public" or doc.get("branch") != "main":
        raise PublishError("Only the declared new public main snapshot is supported.")
    files = doc.get("files")
    if not isinstance(files, list) or not files:
        raise PublishError("Publication manifest is empty.")
    seen, captured = set(), []
    for entry in files:
        name = entry["path"]
        if not isinstance(name, str) or "\\" in name or any(ord(c) < 32 for c in name):
            raise PublishError("Invalid publication path.")
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != name or name in seen:
            raise PublishError("Unsafe or duplicate publication path: " + name)
        if DENIED_PARTS.intersection(rel.parts) or rel.name in {MANIFEST_NAME, "history.bundle", ".DS_Store"}:
            raise PublishError("Local/private artifact in publication manifest: " + name)
        if (rel.name.startswith(".env") and rel.name != ".env.example") or re.search(r"\.(?:pem|key|sqlite3?|db)(?:-.*)?$", rel.name):
            raise PublishError("Potential secret/runtime file in publication manifest: " + name)
        if entry.get("mode") not in ("0644", "0755"):
            raise PublishError("Unsupported file mode: " + name)
        cursor = root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise PublishError("Symlinks are not published: " + name)
        content = cursor.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise PublishError("File changed since preparation: " + name)
        seen.add(name)
        captured.append((name, content, int(entry["mode"], 8)))
    if not REQUIRED.issubset(seen):
        raise PublishError("Missing required source, skill or marketplace files.")
    runtime = json.loads(next(content for name, content, _ in captured if name.endswith("skills/jev-scrum-master/runtime/manifest.json")))
    wheel_name = "skills/jev-scrum-master/runtime/" + runtime["wheel"]
    wheels = [content for name, content, _ in captured if name == wheel_name]
    if len(wheels) != 1 or hashlib.sha256(wheels[0]).hexdigest() != runtime["sha256"]:
        raise PublishError("Bundled runtime wheel is missing or inconsistent.")
    # Capture bytes before any network writes; added files are never staged implicitly.
    return doc, captured, raw


def call(argv, *, env=None, cwd=None, capture=False):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if result.returncode:
        # Avoid dumping credentials or Git configuration. gh/git owns normal interactive errors.
        raise PublishError("Command failed: " + " ".join(argv[:3]))
    return result.stdout.strip() if capture else ""


def gh_json(gh, endpoint, env):
    return json.loads(call([gh, "api", "--hostname", "github.com", endpoint], env=env, capture=True))


def publish(root: Path):
    doc, captured, raw = load_snapshot(root)
    git, gh = shutil.which("git"), shutil.which("gh")
    if not git:
        raise PublishError("Git is required. On macOS install the command line tools first.")
    if not gh:
        raise PublishError("GitHub CLI is required. With Homebrew: brew install gh")
    env = dict(os.environ, GH_HOST="github.com", GH_PROMPT_DISABLED="1")
    env.pop("GH_REPO", None)
    auth = subprocess.run([gh, "auth", "status", "--hostname", "github.com"],
                          env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if auth.returncode:
        raise PublishError("Authenticate first: gh auth login --hostname github.com --git-protocol https --web --scopes workflow")
    user = gh_json(gh, "user", env)
    owner = EXPECTED_REPOSITORY.split("/", 1)[0]
    if user.get("login") != owner or not isinstance(user.get("id"), int):
        raise PublishError("Wrong GitHub account. Required: " + owner + ". No repository was created.")
    existence = subprocess.run([gh, "api", "--hostname", "github.com", "repos/" + EXPECTED_REPOSITORY],
                               env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if existence.returncode == 0:
        raise PublishError("Repository already exists. Refusing to change its content or visibility.")
    if "HTTP 404" not in existence.stderr:
        raise PublishError("Could not verify repository availability (network/authentication error). No creation attempted.")

    parent = Path(tempfile.mkdtemp(prefix="jev-publication-"))
    staging = parent / "jev-ai-scrum-master"
    staging.mkdir()
    print("Reviewed snapshot staging: " + str(staging), flush=True)
    print("Publishing NEW PUBLIC repository: " + EXPECTED_REPOSITORY, flush=True)
    try:
        for name, content, mode in captured:
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(mode)
        (staging / MANIFEST_NAME).write_bytes(raw)
        call([git, "init", "--initial-branch=main", str(staging)], env=env)
        def local_git(*args, capture=False):
            return call([git, "-C", str(staging), *args], env=env, capture=capture)
        local_git("config", "--local", "user.name", owner)
        local_git("config", "--local", "user.email", str(user["id"]) + "+" + owner + "@users.noreply.github.com")
        # Local credential helper only: do not edit the person's global Git configuration.
        import shlex
        local_git("config", "--local", "credential.https://github.com.helper", "")
        local_git("config", "--local", "--add", "credential.https://github.com.helper", "!" + shlex.quote(gh) + " auth git-credential")
        local_git("add", "--all")
        local_git("-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-m",
                  "Publish experimental 0.1.0a3: Skill-first CLI and marketplace distribution")
        commit = local_git("rev-parse", "HEAD", capture=True)
        # A race to create this name fails safely. Never retry as an update to an existing repo.
        call([gh, "repo", "create", EXPECTED_REPOSITORY, "--public", "--source", str(staging),
              "--remote", "origin", "--disable-wiki", "--description",
              "Experimental Skill-first AI Scrum Master: evidence-based CLI/Core, optional Jev, npx skills installation"], env=env)
        local_git("push", "--set-upstream", "origin", "main")
        call([gh, "repo", "edit", EXPECTED_REPOSITORY, "--default-branch", "main"], env=env)
        remote = gh_json(gh, "repos/" + EXPECTED_REPOSITORY, env)
        ref = gh_json(gh, "repos/" + EXPECTED_REPOSITORY + "/git/ref/heads/main", env)
        if remote.get("private") is not False or remote.get("default_branch") != "main" or ref.get("object", {}).get("sha") != commit:
            raise PublishError("Remote verification was incomplete. Inspect the repository before sharing install commands.")
        print("\nPublished and verified: https://github.com/" + EXPECTED_REPOSITORY)
        print("Main commit: " + commit)
        print("Local checkout retained at: " + str(staging))
        print("\nInstall after reviewing the public repository:")
        print("npx skills add " + EXPECTED_REPOSITORY + " --skill jev-scrum-master")
        print("\nClaude Code:")
        print("/plugin marketplace add " + EXPECTED_REPOSITORY)
        print("/plugin install jev-ai-scrum-master@jev-dev-tools")
        print("\nPublication is NOT proof of passing CI, live-host compatibility, or official marketplace listing.")
    except Exception:
        print("\nPublication stopped. Staging was preserved at: " + str(staging), file=sys.stderr)
        print("An empty/partial remote may exist. Do not delete or force-push it. Inspect gh repo view " + EXPECTED_REPOSITORY, file=sys.stderr)
        print("If workflow scope is missing: gh auth refresh --hostname github.com --scopes workflow", file=sys.stderr)
        print("After inspection, a failed initial push can be resumed with: git -C " + repr(str(staging)) + " push --set-upstream origin main", file=sys.stderr)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--public", action="store_true", help="Create the declared NEW public repository and push its main branch")
    group.add_argument("--preview", action="store_true", help="Validate and list the reviewed files offline (default)")
    args = parser.parse_args(argv)
    try:
        if args.public:
            publish(ROOT)
        else:
            doc, captured, _ = load_snapshot(ROOT)
            print("OFFLINE PREVIEW ONLY — nothing uploaded")
            print("Repository: " + doc["repository"] + " (PUBLIC, main)")
            print("Snapshot version: " + doc["version"])
            print("Files: " + str(len(captured)) + " + publication manifest")
            for name, _, _ in captured:
                print("  " + name)
            print("\nOnly these exact files are published. Original Git history, .env files, local databases and added files are not included.")
            print("Run: bash scripts/publish-github.sh --public")
    except (PublishError, OSError, ValueError, KeyError, TypeError) as exc:
        print("Publication error: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
