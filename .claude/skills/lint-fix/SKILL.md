---
name: lint-fix
description: This skill should be used when the user asks to "run linters", "fix lint errors", "check code quality", "run ruff", "run mypy", "run bandit", "typescript check", "lint and fix", or mentions code analysis tools. Runs all configured linters/checkers sequentially and fixes every issue found before moving to the next tool.
argument-hint: [backend|frontend|all]
allowed-tools: Bash, Read, Glob, Grep, Edit, Write
---

# Lint-Fix — Sequential Code Analysis & Auto-Fix

Run every configured code analysis tool **one at a time**, fixing all reported issues before moving to the next tool. Never skip a tool. Never move on with unfixed errors.

## Scope

Determine scope from `$ARGUMENTS`:
- `backend` — Python tools only (ruff, mypy, bandit)
- `frontend` — TypeScript/JS tools only (tsc, eslint)
- `all` or empty — both backend and frontend

## Tool Execution Order

Run tools in this exact order. For each tool: run → read output → fix every issue → re-run to confirm clean → move to next tool.

### Tool 1: Ruff (Python linter + formatter)

```bash
cd backend && python -m ruff check app/ 2>&1
```

**Fix strategy (in order of preference):**
1. Auto-fixable errors → run `python -m ruff check app/ --fix`
2. Remaining errors → fix manually by reading and editing the affected files
3. **F821 (undefined name)**: In SQLAlchemy models, forward-reference strings like `"Session"` are valid — add `# noqa: F821` only if the string is a legitimate ORM forward reference
4. **F401 (unused import)**: Remove the import. If it's re-exported intentionally, add `# noqa: F401`
5. **E501 (line too long)**: Break the line. Follow project convention (max 120 chars)

After fixing, re-run to confirm 0 errors:
```bash
cd backend && python -m ruff check app/ 2>&1
```

### Tool 2: Mypy (Python type checker)

```bash
cd backend && python -m mypy app/ --ignore-missing-imports 2>&1
```

**Fix strategy:**
1. **name-defined errors in ORM models**: SQLAlchemy forward references (`Mapped[list["ModelName"]]`) are valid — these are false positives. Add `# type: ignore[name-defined]` with a comment explaining it's an ORM forward ref
2. **attr-defined on Protocol-typed params**: The handler/service receives a Protocol or `object` type but accesses concrete attributes. Fix by adding proper type annotations (import the concrete type or use `cast`)
3. **arg-type mismatches**: Fix the type annotation or add a `cast()` where the types are structurally compatible but nominally different
4. **assignment type errors**: Fix with proper typing or `cast()` where the assignment is intentionally polymorphic
5. **General rule**: Prefer fixing the actual type over adding `# type: ignore`. Only use `# type: ignore` for genuine false positives (like SQLAlchemy forward refs)

After fixing, re-run to confirm 0 errors:
```bash
cd backend && python -m mypy app/ --ignore-missing-imports 2>&1
```

### Tool 3: Bandit (Python security scanner)

```bash
cd backend && python -m bandit -r app/ -q 2>&1
```

**Fix strategy:**
1. **B110 (try-except-pass)**: If the `pass` is intentional and documented with a comment explaining why, add `# nosec B110`. If it's lazy error handling, add proper logging or re-raise
2. **B105/B106 (hardcoded passwords)**: Move to environment variables or config
3. **B101 (assert)**: If in production code, replace with proper validation. If in test-only code, ignore
4. **B608 (SQL injection)**: Use parameterized queries
5. **Low severity + intentional**: Add `# nosec BXXX` with a comment justifying why it's safe

After fixing, re-run to confirm 0 issues (or only `# nosec`-suppressed ones):
```bash
cd backend && python -m bandit -r app/ -q 2>&1
```

### Tool 4: TypeScript Compiler (type checking)

```bash
cd frontend && npx tsc --noEmit 2>&1
```

**Fix strategy:**
1. **Type errors**: Fix the actual types — add proper annotations, fix interfaces, update generics
2. **Missing properties**: Add the missing property to the interface or component props
3. **Implicit any**: Add explicit type annotations
4. **Module not found**: Check import paths, install missing `@types/` packages if needed

After fixing, re-run to confirm 0 errors:
```bash
cd frontend && npx tsc --noEmit 2>&1
```

### Tool 5: ESLint (JS/TS linter)

Only run if an `eslint.config.js`, `eslint.config.mjs`, or `.eslintrc.*` file exists:

```bash
cd frontend && npx eslint src/ 2>&1
```

If no ESLint config exists, **skip this tool** and report: "ESLint: skipped (no config found)".

**Fix strategy:**
1. Auto-fixable → run `npx eslint src/ --fix`
2. Remaining → fix manually by reading and editing the affected files

After fixing, re-run to confirm 0 errors.

## Output Format

After all tools complete, print a summary table:

```
## Lint-Fix Summary

| Tool       | Initial Errors | Fixed | Remaining | Status |
|------------|---------------|-------|-----------|--------|
| ruff       | N             | N     | 0         | PASS   |
| mypy       | N             | N     | 0         | PASS   |
| bandit     | N             | N     | 0         | PASS   |
| tsc        | N             | N     | 0         | PASS   |
| eslint     | -             | -     | -         | SKIP   |
```

## Rules

- **Sequential execution**: finish one tool completely before starting the next
- **Fix before moving on**: every issue must be resolved (fixed or explicitly suppressed with justification) before re-running the tool and moving to the next
- **Re-run after fixes**: always re-run the tool after fixing to confirm 0 errors
- **No regressions**: if fixing one tool's issues breaks another, note it and fix in that tool's pass
- **Read before edit**: always read the file before editing it
- **Minimal changes**: only change what's needed to fix the reported issue — do not refactor surrounding code
- **Preserve behavior**: fixes must not change runtime behavior. Type annotations, import cleanup, and lint suppressions are safe. Logic changes are not
- **Document suppressions**: every `# noqa`, `# type: ignore`, or `# nosec` must have a brief comment explaining why
