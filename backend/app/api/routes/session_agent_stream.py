"""Session Agent Stream — SSE streaming routes for the TRIZ pipeline.

Invariants:
    - Every SSE stream instantiates AgentRunner with fresh DB session
    - Phase review events emitted by route, not agent
    - ForgeState synced to DB after every phase transition

Design Decisions:
    - All helpers moved to session_stream_helpers.py (ADR: ExMA import fan-out < 10)
    - Routes are thin: validate, delegate to helpers, yield SSE events
    - Document download in separate route to keep this module focused on streaming
"""

import asyncio
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.session import UserInput
from app.api.routes.session_lifecycle import _forge_states, get_session_or_404
from app.api.routes.session_stream_helpers import (
    get_or_restore_forge_state, build_stream_message,
    format_user_input, apply_user_input,
    build_resume_review_event, build_review_event,
    create_runner, sse_line, done_event, patch_snapshot_awaiting,
    SSE_HEADERS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: UUID, db: AsyncSession = Depends(get_db),
):
    """SSE stream — reconnects paused sessions or starts agent work."""
    session = await get_session_or_404(session_id, db)
    if session.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Session is cancelled",
        )
    forge_state = get_or_restore_forge_state(
        session_id, session, _forge_states,
    )

    async def event_generator():
        try:
            # Reconnect: re-emit review event without re-running agent
            if forge_state.awaiting_user_input:
                review = build_resume_review_event(forge_state, session)
                if review:
                    yield sse_line(review)
                yield sse_line(done_event(awaiting_input=True))
                return

            message = build_stream_message(session, forge_state)
            runner = create_runner(db)
            async for event in runner.run(session, message, forge_state):
                yield sse_line(event)

            review = build_resume_review_event(forge_state, session)
            if review:
                forge_state.awaiting_user_input = True
                patch_snapshot_awaiting(session)
                try:
                    await db.commit()
                except Exception as exc:
                    logger.error("Failed to save awaiting state: %s", exc)
                yield sse_line(review)
        except asyncio.CancelledError:
            logger.info("Client disconnected (session=%s)", session_id)
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/{session_id}/user-input")
async def send_user_input(
    session_id: UUID,
    body: UserInput,
    db: AsyncSession = Depends(get_db),
):
    """Send user input — dispatches to phase-appropriate processing."""
    session = await get_session_or_404(session_id, db)
    if session.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Session is cancelled",
        )
    forge_state = get_or_restore_forge_state(
        session_id, session, _forge_states,
    )
    runner = create_runner(db)
    message = format_user_input(body, forge_state, session.problem)
    await apply_user_input(body, forge_state, session, db)

    async def event_generator():
        try:
            async for event in runner.run(session, message, forge_state):
                yield sse_line(event)

            review = build_review_event(forge_state, session)
            if review:
                forge_state.awaiting_user_input = True
                patch_snapshot_awaiting(session)
                try:
                    await db.commit()
                except Exception as exc:
                    logger.error("Failed to save awaiting state: %s", exc)
                yield sse_line(review)
        except asyncio.CancelledError:
            logger.info(
                "Client disconnected from user-input (session=%s)",
                session_id,
            )
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/{session_id}/document")
async def download_document(session_id: UUID):
    """Download the Knowledge Document as a .md file."""
    import tempfile
    specs_dir = os.path.join(tempfile.gettempdir(), "triz", "specs")
    file_path = os.path.join(specs_dir, f"{session_id}.md")
    if not os.path.exists(file_path):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Document not found",
        )
    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=f"triz-knowledge-{session_id}.md",
    )
