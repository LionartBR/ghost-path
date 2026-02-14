"""Generate a structured PR body from commit history.

Read-only — inspects git log and diff between current branch and base branch.
Outputs JSON with: pr_body markdown, suggested_title, commit breakdown.

Usage: python generate_pr_body.py [base_branch]
       base_branch defaults to auto-detected default branch, then 'master'

Invariants:
    - Never modifies the working tree or index
    - All subprocess calls are read-only git commands
"""

import json
import re
import subprocess
import sys


CONVENTIONAL_TYPES = {
    "feat": "New Features",
    "fix": "Bug Fixes",
    "refactor": "Refactoring",
    "test": "Tests",
    "docs": "Documentation",
    "chore": "Chores",
    "perf": "Performance",
    "style": "Style",
    "ci": "CI/CD",
    "build": "Build",
}

CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|refactor|test|docs|chore|perf|style|ci|build)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r":\s*(?P<desc>.+)$"
)

# Null byte delimiter — cannot appear in commit messages
NUL = "%x00"


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def detect_default_branch() -> str:
    """Auto-detect the repo's default branch from origin HEAD."""
    ref = run_git("symbolic-ref", "refs/remotes/origin/HEAD", "--short")
    if ref:
        # Returns "origin/main" or "origin/master" — strip prefix
        return ref.removeprefix("origin/")
    # Fallback: check if 'main' exists
    if run_git("rev-parse", "--verify", "main"):
        return "main"
    return "master"


def branch_exists(name: str) -> bool:
    return bool(run_git("rev-parse", "--verify", name))


def parse_commits(base: str) -> list[dict]:
    """Parse commits between base..HEAD using null-byte delimiters."""
    raw = run_git(
        "log", f"{base}..HEAD",
        f"--pretty=format:%x00%h%x00%s%x00%b%x00",
        "--reverse",
    )
    if not raw:
        return []

    commits = []
    # Split on null bytes: sequence is \0hash\0subject\0body\0
    parts = raw.split("\x00")

    # Skip empty leading element, then consume groups of 3
    # Filter out empty strings from split
    tokens = [p for p in parts if p or p == ""]
    # The format produces: ['', hash, subject, body, '', hash, subject, body, '', ...]
    # Remove empties and group
    clean = [p.strip() for p in parts if p.strip()]

    # Rebuild by grouping: each commit has (hash, subject, body)
    # But body can be empty, so let's use a different approach
    # Re-parse with a unique record separator
    raw2 = run_git(
        "log", f"{base}..HEAD",
        "--pretty=format:---RECORD---%n%h%n%s%n%B---END---",
        "--reverse",
    )
    if not raw2:
        return []

    for block in raw2.split("---RECORD---"):
        block = block.strip()
        if not block:
            continue

        # Remove trailing ---END--- marker
        block = block.replace("---END---", "").strip()
        lines = block.split("\n", 2)
        if len(lines) < 2:
            continue

        hash_str = lines[0].strip()
        subject = lines[1].strip()
        body = lines[2].strip() if len(lines) > 2 else ""

        match = CONVENTIONAL_RE.match(subject)
        if match:
            commit_type = match.group("type")
            scope = match.group("scope") or ""
            desc = match.group("desc")
        else:
            commit_type = "other"
            scope = ""
            desc = subject

        commits.append({
            "hash": hash_str,
            "subject": subject,
            "body": body,
            "type": commit_type,
            "scope": scope,
            "description": desc,
        })

    return commits


def generate_summary(commits: list[dict]) -> list[str]:
    """Group commits by type and produce bullet-point summary."""
    grouped: dict[str, list[dict]] = {}
    for c in commits:
        grouped.setdefault(c["type"], []).append(c)

    bullets = []
    for ctype in CONVENTIONAL_TYPES:
        if ctype not in grouped:
            continue
        items = grouped[ctype]
        section_name = CONVENTIONAL_TYPES[ctype]
        if len(items) == 1:
            bullets.append(f"**{section_name}**: {items[0]['description']}")
        else:
            descriptions = ", ".join(c["description"] for c in items)
            bullets.append(f"**{section_name}**: {descriptions}")

    # Non-conventional commits
    if "other" in grouped:
        for c in grouped["other"]:
            bullets.append(c["description"])

    return bullets


def generate_test_plan(commits: list[dict], diff_stat: str) -> list[str]:
    """Suggest test plan items based on what changed."""
    items = []
    types_present = {c["type"] for c in commits}

    if "feat" in types_present:
        items.append("Verify new feature works as expected")
    if "fix" in types_present:
        items.append("Confirm bug is fixed and regression tests pass")
    if "refactor" in types_present:
        items.append("Verify existing behavior is unchanged after refactor")

    if "test" in diff_stat.lower() or "spec" in diff_stat.lower():
        items.append("Run test suite and verify all tests pass")
    else:
        items.append("Run existing tests to check for regressions")

    if "migration" in diff_stat.lower() or "alembic" in diff_stat.lower():
        items.append("Test database migration (up and down)")

    return items


def main() -> None:
    if len(sys.argv) > 1:
        base = sys.argv[1]
    else:
        base = detect_default_branch()

    # Verify base branch exists (local or remote)
    if not branch_exists(base):
        remote = f"origin/{base}"
        if branch_exists(remote):
            base = remote
        else:
            print(json.dumps({
                "error": f"Base branch '{base}' not found (tried local and origin/)",
                "pr_body": None,
            }))
            return

    # Guard: current branch IS the base branch → no PR makes sense
    current = run_git("branch", "--show-current")
    if current == base or current == base.removeprefix("origin/"):
        print(json.dumps({
            "error": f"Current branch '{current}' is the base branch — cannot create PR to self",
            "pr_body": None,
        }))
        return

    commits = parse_commits(base)
    if not commits:
        print(json.dumps({
            "error": "No commits found between base and HEAD",
            "pr_body": None,
        }))
        return

    diff_stat = run_git("diff", "--stat", f"{base}...HEAD")
    diff_shortstat = run_git("diff", "--shortstat", f"{base}...HEAD")

    summary_bullets = generate_summary(commits)
    test_plan = generate_test_plan(commits, diff_stat)

    body_lines = ["## Summary"]
    for bullet in summary_bullets:
        body_lines.append(f"- {bullet}")

    body_lines.append("")
    body_lines.append(f"**Scope**: {diff_shortstat}")
    body_lines.append("")
    body_lines.append("## Test plan")
    for item in test_plan:
        body_lines.append(f"- [ ] {item}")
    body_lines.append("")
    body_lines.append("\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)")

    pr_body = "\n".join(body_lines)

    output = {
        "error": None,
        "base_branch": base,
        "total_commits": len(commits),
        "commits": commits,
        "pr_body": pr_body,
        "suggested_title": commits[-1]["subject"] if len(commits) == 1 else None,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
