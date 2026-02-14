"""Analyze git changes and produce structured JSON for the ship skill.

Read-only — runs git status/diff and categorizes changes.
Outputs JSON with: commit type suggestion, secret warnings, file categories.

Invariants:
    - Never modifies the working tree or index
    - All subprocess calls are read-only git commands
"""

import json
import subprocess
from pathlib import PurePosixPath


SECRET_EXACT_NAMES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.development",
    "credentials.json", "service-account.json", "secrets.yaml",
    "secrets.yml", "token.json", "auth.json",
    "id_rsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc",
})

SECRET_EXTENSIONS = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore",
})

SECRET_NAME_KEYWORDS = frozenset({
    "secret", "credential", "apikey", "api_key", "private_key", "privatekey",
})

# Ordered by priority — first match wins.
# More specific patterns come first to avoid misclassification.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("test", (
        "test_", "_test.py", ".test.ts", ".test.tsx", ".spec.ts",
        ".spec.tsx", "/tests/", "/__tests__/", "conftest.py",
    )),
    ("migration", ("alembic/versions/", "/migrations/",)),
    ("docs", (
        "README", "CHANGELOG", "LICENSE",
        "/docs/",
    )),
    ("config", (
        "Dockerfile", "docker-compose", ".dockerignore",
        ".gitignore", ".eslintrc", ".prettierrc",
        "tsconfig.json", "vite.config", "tailwind.config", "postcss.config",
        "pyproject.toml", "setup.cfg", "alembic.ini",
    )),
    ("frontend", (".tsx", ".ts", ".jsx", ".js", ".css", ".html")),
    ("backend", (".py",)),
]

# File extensions that are docs, not source (avoids .md → frontend false negative)
DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt"})


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def classify_file(path: str) -> str:
    p = path.lower()
    ext = PurePosixPath(p).suffix

    # Doc extensions checked first — avoids .md being "other"
    if ext in DOC_EXTENSIONS:
        return "docs"

    for category, patterns in CATEGORY_RULES:
        if any(pat in p for pat in patterns):
            return category

    # Config files by extension (only if not caught above)
    if ext in {".toml", ".cfg", ".ini", ".yaml", ".yml", ".json"}:
        return "config"

    return "other"


def detect_secrets(files: list[str]) -> list[str]:
    warnings = []
    for f in files:
        name = PurePosixPath(f).name.lower()
        ext = PurePosixPath(f).suffix.lower()

        # Exact filename match (handles .env, credentials.json, etc.)
        if name in SECRET_EXACT_NAMES:
            warnings.append(f)
            continue

        # Extension match (handles .pem, .key, .p12, etc.)
        if ext in SECRET_EXTENSIONS:
            warnings.append(f)
            continue

        # Keyword match in filename
        if any(kw in name for kw in SECRET_NAME_KEYWORDS):
            warnings.append(f)
            continue

    return warnings


def suggest_commit_type(categories: dict[str, list[str]], status_lines: list[str]) -> str:
    has_new = any(line.startswith("?") or line.startswith("A") for line in status_lines)
    has_deleted = any(line.startswith("D") for line in status_lines)
    has_renamed = any(line.startswith("R") for line in status_lines)

    present = {k for k, v in categories.items() if v}

    # Single-category changes have obvious types
    if present == {"test"}:
        return "test"
    if present == {"docs"}:
        return "docs"
    if present == {"config"}:
        return "chore"
    if "migration" in present:
        return "feat"

    # Structural changes without new code
    if has_renamed and len(status_lines) <= 3:
        return "refactor"
    if has_deleted and not has_new and sum(len(v) for v in categories.values()) <= 3:
        return "refactor"

    # New source files → likely a feature
    if has_new and present & {"backend", "frontend"}:
        return "feat"

    return "fix"


def main() -> None:
    status_short = run_git("status", "--porcelain")
    diff_staged_summary = run_git("diff", "--staged", "--shortstat")
    diff_unstaged_summary = run_git("diff", "--shortstat")

    if not status_short and not diff_staged_summary:
        print(json.dumps({"clean": True, "message": "Working tree is clean. Nothing to commit."}))
        return

    # Parse files from porcelain v1 output (XY filename / XY old -> new)
    status_lines = [line for line in status_short.splitlines() if line.strip()]
    all_files = []
    for line in status_lines:
        raw = line[3:]
        # Unquote if git quoted the filename (spaces, unicode)
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1].encode().decode("unicode_escape")
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        all_files.append(raw)

    # Categorize
    categories: dict[str, list[str]] = {}
    for f in all_files:
        cat = classify_file(f)
        categories.setdefault(cat, []).append(f)

    output = {
        "clean": False,
        "total_files": len(all_files),
        "commit_type_suggestion": suggest_commit_type(categories, status_lines),
        "categories": {k: sorted(v) for k, v in categories.items()},
        "secret_warnings": detect_secrets(all_files),
        "stats": {
            "staged": diff_staged_summary or "nothing staged",
            "unstaged": diff_unstaged_summary or "nothing unstaged",
        },
        "files": all_files,
        "status_raw": status_short,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
