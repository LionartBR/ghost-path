"""Service test fixtures — async DB + FastAPI test client.

Invariants:
    - Every test gets a fresh in-memory SQLite database
    - get_db dependency overridden to use test DB session
    - db_manager initialized for background tasks that bypass get_db
    - mock_dispatch patches ToolDispatch at the agent_runner boundary

Design Decisions:
    - SQLite in-memory: fast, no external dependency, sufficient for route tests
      (ADR: hackathon — PostgreSQL-specific features not exercised here)
    - db_manager patched: background tasks use db_manager.session() directly
    - mock_dispatch patches class, not methods: avoids instantiating 7 handler classes
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.infrastructure.database import get_db, DatabaseSessionManager
from app.models.session import Session as SessionModel
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


@pytest.fixture
async def seed_session(test_db):
    """Insert a minimal session into the test DB for agent_runner tests."""
    session = SessionModel(problem="Test problem", status="decomposing")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)
    return session


@pytest.fixture
def mock_dispatch(monkeypatch):
    """Replace ToolDispatch in agent_runner with a controllable fake.

    Returns dict with:
      - log: list of {"tool": str, "input": dict} for each execute() call
      - results: dict[tool_name, result_dict | callable] to configure responses
    """
    log = []
    results = {}

    class _FakeDispatch:
        def __init__(self, db, state, session_id=None, anthropic_client=None):
            self._state = state

        async def execute(self, tool_name, session, input_data):
            log.append({"tool": tool_name, "input": input_data})
            r = results.get(tool_name, {"status": "ok"})
            return r() if callable(r) else r

        def record_web_search(self, query, summary):
            self._state.record_web_search(query, summary)

    monkeypatch.setattr(
        "app.services.agent_runner.ToolDispatch", _FakeDispatch,
    )
    return {"log": log, "results": results}
