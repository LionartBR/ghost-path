"""Delete Session — verifies background deletion with instant ForgeState cleanup.

Invariants:
    - DELETE returns 202 Accepted (not 204 — work is deferred)
    - ForgeState removed from memory before response returns
    - Session and cascade data deleted from DB in background
    - Deleting non-existent session returns 404

Design Decisions:
    - Background tasks run synchronously in httpx test client (FastAPI behavior)
      so we can assert DB state after the response
"""

import pytest
from uuid import uuid4

from app.api.routes.session_lifecycle import _forge_states
from app.core.forge_state import ForgeState
from app.models.session import Session as SessionModel


@pytest.fixture
async def seed_session(test_db):
    """Insert a session directly into the test DB."""
    session = SessionModel(problem="Test problem for deletion", status="decomposing")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)
    return session


async def test_delete_returns_202_accepted(client, seed_session):
    """DELETE /sessions/{id} returns 202 Accepted (background deletion)."""
    res = await client.delete(f"/api/v1/sessions/{seed_session.id}")
    assert res.status_code == 202


async def test_delete_cleans_forge_state_immediately(client, seed_session):
    """ForgeState is removed from memory in the request handler, not the background task."""
    _forge_states[seed_session.id] = ForgeState()

    await client.delete(f"/api/v1/sessions/{seed_session.id}")

    assert seed_session.id not in _forge_states


async def test_delete_removes_session_from_db(client, seed_session, test_db):
    """Background task deletes session and cascade data from DB."""
    await client.delete(f"/api/v1/sessions/{seed_session.id}")

    # Background tasks run synchronously in test client
    from sqlalchemy import select
    result = await test_db.execute(
        select(SessionModel).where(SessionModel.id == seed_session.id),
    )
    assert result.scalar_one_or_none() is None


async def test_delete_nonexistent_session_returns_404(client):
    """Deleting a session that doesn't exist returns 404."""
    fake_id = uuid4()
    res = await client.delete(f"/api/v1/sessions/{fake_id}")
    assert res.status_code == 404


async def test_delete_is_idempotent_for_forge_state(client, seed_session):
    """Deleting a session without ForgeState in memory doesn't raise."""
    _forge_states.pop(seed_session.id, None)

    res = await client.delete(f"/api/v1/sessions/{seed_session.id}")
    assert res.status_code == 202
