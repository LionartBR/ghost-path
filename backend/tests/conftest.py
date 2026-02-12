"""Root conftest — shared test configuration."""

import os

# Ensure tests don't accidentally use real API keys
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-fake-key")
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///test.db",
)
