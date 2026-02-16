"""Session Lifecycle — CRUD operations and in-memory ForgeState management.

Invariants:
    - ForgeState is per-session, in-memory (module-level dict)
    - User input is validated by Pydantic before reaching the route handler
    - _forge_states dict is the single source for in-memory state

Design Decisions:
    - _forge_states as module-level dict: deliberate exception to no-global-state rule
      (ADR: hackathon — single-process uvicorn, no multi-worker, state lost on restart)
    - get_session_or_404 exported for reuse by session_agent_stream (DRY over duplication)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.models.session import Session as SessionModel
from app.schemas.session import SessionCreate, SessionResponse
from app.core.forge_state import ForgeState
from app.core.detect_language import detect_locale
from app.core.domain_types import Locale, SessionId
from app.core.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# ADR: ForgeState is in-memory (not DB/Redis)
# Context: hackathon — single-process uvicorn, no multi-worker
# Trade-off: state lost on restart, acceptable for demo
_forge_states: dict[UUID, ForgeState] = {}


async def get_session_or_404(
    session_id: SessionId, db: AsyncSession,
) -> SessionModel:
    """Get session or raise 404. Exported for agent_stream."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id),
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=ResourceNotFoundError(
                "Session", str(session_id),
            ).to_response(),
        )
    return session


@router.post(
    "", response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    body: SessionCreate, db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new TRIZ session."""
    try:
        if body.locale:
            locale = Locale(body.locale)
            confidence = 1.0  # user-selected = maximum confidence
        else:
            locale, confidence = detect_locale(body.problem)
        session = SessionModel(
            problem=body.problem, status="decomposing",
            locale=locale.value, locale_confidence=confidence,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        _forge_states[session.id] = ForgeState(
            locale=locale, locale_confidence=confidence,
        )
        return SessionResponse(
            id=session.id,
            problem=session.problem,
            status=session.status,
            current_phase=session.current_phase,
            current_round=session.current_round,
            locale=session.locale,
        )
    except Exception as e:
        _forge_states.pop(session.id, None)
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )


@router.get("")
async def list_sessions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List sessions with pagination."""
    query = select(SessionModel).order_by(
        SessionModel.created_at.desc(),
    )
    if status_filter:
        query = query.where(SessionModel.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": str(s.id),
                "problem": (
                    s.problem[:200] + ("..." if len(s.problem) > 200 else "")
                ),
                "status": s.status,
                "current_phase": s.current_phase,
                "current_round": s.current_round,
                "locale": s.locale,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
        "pagination": {"limit": limit, "offset": offset},
    }


@router.get("/{session_id}")
async def get_session(
    session_id: SessionId, db: AsyncSession = Depends(get_db),
) -> dict:
    """Get session details."""
    session = await get_session_or_404(session_id, db)
    return {
        "id": str(session.id),
        "problem": session.problem,
        "status": session.status,
        "current_phase": session.current_phase,
        "current_round": session.current_round,
        "locale": session.locale,
        "created_at": session.created_at.isoformat(),
        "resolved_at": (
            session.resolved_at.isoformat() if session.resolved_at else None
        ),
        "total_tokens_used": session.total_tokens_used,
    }


async def _delete_session_in_background(session_id: SessionId) -> None:
    """Background task: delete session and cascade all data.

    Uses its own DB session — request session is closed when this runs.
    ADR: fire-and-forget acceptable for hackathon.
    """
    from app.infrastructure.database import db_manager

    if not db_manager:
        logger.error("Cannot delete session %s: DB not init", session_id)
        return

    try:
        async with db_manager.session() as db:
            result = await db.execute(
                select(SessionModel).where(
                    SessionModel.id == session_id,
                ),
            )
            session = result.scalar_one_or_none()
            if not session:
                logger.warning("Session %s already deleted", session_id)
                return
            await db.delete(session)
            await db.commit()
            logger.info("Session %s deleted in background", session_id)
    except Exception as e:
        logger.error("Failed to delete session %s: %s", session_id, e,
            exc_info=True)


@router.delete(
    "/{session_id}", status_code=status.HTTP_202_ACCEPTED,
)
async def delete_session(
    session_id: SessionId,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Accept deletion. ForgeState cleaned now, DB cascade in background."""
    await get_session_or_404(session_id, db)
    _forge_states.pop(session_id, None)
    background_tasks.add_task(_delete_session_in_background, session_id)


@router.post("/{session_id}/cancel")
async def cancel_session(
    session_id: SessionId, db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel active session. Sets ForgeState flag for loop termination."""
    session = await get_session_or_404(session_id, db)
    if session.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Session is already cancelled",
        )
    if session.status == "crystallized":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed session",
        )

    if session_id in _forge_states:
        _forge_states[session_id].cancelled = True

    session.status = "cancelled"
    await db.commit()
    return {"message": "Session cancelled"}
