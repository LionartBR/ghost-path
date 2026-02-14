"""Service test fixtures — async DB + FastAPI test client.

Invariants:
    - Every test gets a fresh in-memory SQLite database
    - get_db dependency overridden to use test DB session
    - db_manager initialized for background tasks that bypass get_db

Design Decisions:
    - SQLite in-memory: fast, no external dependency, sufficient for route tests
      (ADR: hackathon — PostgreSQL-specific features not exercised here)
    - db_manager patched: background tasks use db_manager.session() directly
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.infrastructure.database import get_db, DatabaseSessionManager
import app.infrastructure.database as db_module
from app.main import app


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )


@pytest.fixture
async def test_db(test_session_factory):
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client(test_engine, test_session_factory):
    """FastAPI test client with DB dependency overridden."""
    # Override get_db for route-level dependency injection
    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Patch db_manager for background tasks that use it directly
    original_manager = db_module.db_manager
    fake_manager = DatabaseSessionManager.__new__(DatabaseSessionManager)
    fake_manager.engine = test_engine
    fake_manager._session_factory = test_session_factory
    db_module.db_manager = fake_manager

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()
    db_module.db_manager = original_manager
