"""Async Session Factory — provides async DB sessions for direct usage outside FastAPI.

Invariants:
    - Uses the same engine as DatabaseSessionManager
    - Meant for scripts, migrations, and test fixtures

Design Decisions:
    - Separate from infrastructure/database.py: this is a convenience for non-FastAPI contexts
      (ADR: alembic and test fixtures need raw session factory)
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def create_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for the given database URL."""
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
