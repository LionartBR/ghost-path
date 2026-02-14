---
name: ship
description: Commit all changes, push to remote, and create a PR using gh CLI. Use when the user wants to ship their work.
argument-hint: [optional PR title]
disable-model-invocation: true
allowed-tools: Bash, Read, Glob, Grep
---

# Ship — Commit, Push & Create PR

Automate the full shipping workflow: commit staged/unstaged changes, push the branch, and open a pull request.

## Pre-computed Context (read-only scripts — no side effects)

### Change Analysis
!`python .claude/skills/ship/scripts/analyze_changes.py 2>&1`

### PR Body Draft
!`python .claude/skills/ship/scripts/generate_pr_body.py 2>&1`

### Branch Info
- Current branch: !`git branch --show-current`
- Default branch: !`git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}' || echo "master"`
- Upstream: !`git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "none"`
- Existing PR: !`gh pr view --json number,url,title 2>/dev/null || echo "no PR"`

## Pre-flight Checks

Before starting, verify these conditions. If any fails, **inform the user and stop**:

1. **Current branch** must not be empty (detached HEAD → tell user to create a branch first).
2. **Current branch** must not be the default branch (main/master → tell user to create a feature branch first).
3. **Change Analysis** `"clean": true` → nothing to commit, stop.
4. **PR Body Draft** `"error"` contains `"base branch"` or `"cannot create PR to self"` → report and stop.

## Workflow

The scripts above already analyzed everything. Now follow these steps **sequentially**:

### Step 1: Review the Analysis

1. Parse the **Change Analysis** JSON above.
2. If `"secret_warnings"` is non-empty — **warn the user** about those files and exclude them from staging. Do NOT proceed until the user confirms.
3. Use `"commit_type_suggestion"` as the commit type (feat/fix/refactor/etc). Override only if the suggestion is clearly wrong after reading the diff.
4. Use `"categories"` to understand what changed at a glance.

### Step 2: Commit

1. Run `git diff` and `git diff --staged` to understand the actual content of changes (the analysis only has file names).
2. Stage relevant files with `git add <file1> <file2> ...` — use the `"files"` list from the analysis, excluding any secret warnings.
3. Write a concise commit message using conventional commit format and the suggested type:

```bash
git commit -m "$(cat <<'EOF'
type: short description focusing on WHY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

4. If the commit fails due to a pre-commit hook, fix the issue and create a **NEW** commit (never `--amend`).

### Step 3: Push

1. Check the **Upstream** value from Branch Info above.
2. If `"none"` — push with: `git push -u origin <current-branch>`
3. Otherwise — push with: `git push`
4. Never force push unless the user explicitly asks.

### Step 4: Create PR

1. Check the **Existing PR** value from Branch Info above.
2. If a PR already exists, show the URL and stop — the push already updated it.
3. If no PR exists, parse the **PR Body Draft** JSON above:
   - Use `"pr_body"` directly as the `--body` argument.
   - Use `$ARGUMENTS` as title if provided. Otherwise use `"suggested_title"` from the JSON (if single commit), or draft one yourself (under 70 chars).
4. Use the **Default branch** from Branch Info as `--base`:

```bash
gh pr create --base <default-branch> --title "the pr title" --body "$(cat <<'EOF'
<pr_body from the JSON>
EOF
)"
```

5. Return the PR URL to the user.

## Rules

- NEVER use `--no-verify` or skip hooks unless the user explicitly asks.
- NEVER use `--force` push unless the user explicitly asks.
- NEVER amend commits — always create new ones.
- NEVER use interactive flags (`-i`).
- If any step fails, report the error clearly and stop — don't proceed to subsequent steps.
- Always show the PR URL at the end.
