"""Session Agent Stream — SSE streaming, user input processing, and document download.

Invariants:
    - Every SSE stream instantiates AgentRunner with fresh DB session and shared Anthropic client
    - User input triggers phase-appropriate processing based on UserInput.type
    - Phase review events (review_decompose, review_explore, etc.) emitted by route, not agent
    - ForgeState synced to DB after every phase transition (observability + crash recovery)
    - Message history reset on phase transition (token explosion prevention)

Design Decisions:
    - Imports _forge_states and get_session_or_404 from session_lifecycle (shared state, DRY)
    - StreamingResponse for SSE: event_generator yields formatted SSE lines
    - Phase review logic in route: agent does the work, route emits the review event
    - History reset: ForgeState already has structured data, conversational history is redundant
    - User input processing + review event builders extracted to session_stream_helpers.py (ExMA)
"""

import asyncio
import json
import os
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.schemas.session import UserInput
from app.services.agent_runner import AgentRunner
from app.core.forge_state import ForgeState
from app.core.domain_types import Locale, Phase
from app.config import get_settings
from app.api.routes.session_lifecycle import (
    _forge_states, get_session_or_404,
)
from app.models.session import Session as SessionModel
from app.core.language_strings import get_phase_prefix
from app.core.format_messages import (
    format_user_input as _format_user_input_pure,
    build_initial_stream_message,
    build_resume_message,
)
from app.api.routes.session_stream_helpers import (
    apply_user_input,
    build_review_event,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# ADR: SSE headers prevent proxy/browser buffering of streamed events.
# Without these, nginx (X-Accel-Buffering) and browsers (Cache-Control)
# may batch small chunks before delivering them to the client.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _get_or_restore_forge_state(
    session_id: UUID, session: SessionModel,
) -> ForgeState:
    """Return in-memory ForgeState or restore from DB snapshot.

    Lookup order: _forge_states dict → session.forge_state_snapshot → new default.
    Always syncs locale from Session (DB is source of truth for locale).
    """
    if session_id in _forge_states:
        state = _forge_states[session_id]
    elif session.forge_state_snapshot:
        state = ForgeState.from_snapshot(session.forge_state_snapshot)
        _forge_states[session_id] = state
        logger.info("Restored ForgeState from DB snapshot (session=%s)", session_id)
    else:
        state = ForgeState()
        _forge_states[session_id] = state

    # ADR: Session.locale (DB) is source of truth — ForgeState snapshot may
    # have stale/default locale if saved before locale propagation was fixed.
    if session.locale:
        db_locale = Locale(session.locale)
        if state.locale != db_locale:
            logger.info(
                "Synced ForgeState locale from DB: %s → %s (session=%s)",
                state.locale.value, db_locale.value, session_id,
            )
            state.locale = db_locale
            state.locale_confidence = session.locale_confidence or 1.0
    return state


def _done_event(error: bool = False, awaiting_input: bool = False) -> dict:
    """SSE done event — mirrors agent_runner._done_event for route-level use."""
    return {"type": "done", "data": {"error": error, "awaiting_input": awaiting_input}}


def _build_resume_review_event(state: ForgeState) -> dict | None:
    """Build review event covering ALL phases (including DECOMPOSE).

    Extends build_review_event (which skips DECOMPOSE) so reconnect
    can re-emit the correct review for any phase.
    """
    if state.current_phase == Phase.DECOMPOSE:
        event = {
            "type": "review_decompose",
            "data": {
                "fundamentals": state.fundamentals,
                "assumptions": state.assumptions,
                "reframings": state.reframings,
            },
        }
        return event
    return build_review_event(state)


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
    forge_state = _get_or_restore_forge_state(session_id, session)

    async def event_generator():
        try:
            # === RECONNECT: session paused for user review ===
            # Re-emit the review event so frontend renders the correct UI
            # without re-running the agent. ADR: zero-cost reconnect.
            if forge_state.awaiting_user_input:
                review = _build_resume_review_event(forge_state)
                if review:
                    yield _sse_line(review)
                yield _sse_line(_done_event(awaiting_input=True))
                return

            # === NEW or RESUMED session: run agent ===
            prefix = get_phase_prefix(forge_state.locale, session.problem)
            if (session.message_history
                    and forge_state.current_phase != Phase.DECOMPOSE):
                message = build_resume_message(
                    prefix, forge_state.current_phase,
                    session.problem, forge_state.locale,
                )
            else:
                message = build_initial_stream_message(
                    prefix, session.problem, locale=forge_state.locale,
                )

            runner = _create_runner(db)
            async for event in runner.run(session, message, forge_state):
                yield _sse_line(event)

            # After agent finishes, emit review + set awaiting flag
            review = _build_resume_review_event(forge_state)
            if review:
                forge_state.awaiting_user_input = True
                _patch_snapshot_awaiting(session)
                try:
                    await db.commit()
                except Exception as exc:
                    logger.error("Failed to save awaiting state: %s", exc)
                yield _sse_line(review)
        except asyncio.CancelledError:
            logger.info("Client disconnected from stream (session=%s)", session_id)
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
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
    forge_state = _get_or_restore_forge_state(session_id, session)
    runner = _create_runner(db)

    message = _format_user_input(body, forge_state, session.problem)
    await apply_user_input(body, forge_state, session, db)

    async def event_generator():
        try:
            async for event in runner.run(session, message, forge_state):
                yield _sse_line(event)

            # Emit review + set awaiting flag for session resume
            review = build_review_event(forge_state)
            if review:
                forge_state.awaiting_user_input = True
                _patch_snapshot_awaiting(session)
                try:
                    await db.commit()
                except Exception as exc:
                    logger.error("Failed to save awaiting state: %s", exc)
                yield _sse_line(review)
        except asyncio.CancelledError:
            logger.info("Client disconnected from user-input stream (session=%s)", session_id)
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
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


# -- Helpers -------------------------------------------------------------------

_anthropic_client: ResilientAnthropicClient | None = None


def _get_anthropic_client() -> ResilientAnthropicClient:
    """Singleton Anthropic client — reused across all SSE streams.

    ADR: AsyncAnthropic is stateless and connection-pool-safe. Creating a new
    client per request wasted connection pool setup + TLS handshake. Singleton
    amortizes this cost across the process lifetime.
    """
    global _anthropic_client
    if _anthropic_client is None:
        settings = get_settings()
        _anthropic_client = ResilientAnthropicClient(
            api_key=settings.anthropic_api_key,
            max_retries=settings.anthropic_max_retries,
            timeout_seconds=settings.anthropic_timeout_seconds,
            enable_1m_context=settings.anthropic_context_1m,
        )
    return _anthropic_client


def _create_runner(db: AsyncSession) -> AgentRunner:
    """Create AgentRunner with shared Anthropic client."""
    return AgentRunner(db, _get_anthropic_client())


def _sse_line(event: dict) -> str:
    """Format event as SSE data line."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _patch_snapshot_awaiting(session) -> None:
    """Patch awaiting_user_input in existing snapshot — avoids full rebuild.

    ADR: agent_runner already committed the full snapshot via _save_state.
    Re-serializing 30+ ForgeState fields (including set→sorted-list conversions)
    just to flip one boolean is wasteful. Dict spread copies only top-level keys.
    """
    if session.forge_state_snapshot:
        session.forge_state_snapshot = {
            **session.forge_state_snapshot,
            "awaiting_user_input": True,
        }


def _format_user_input(
    body: UserInput, state: ForgeState, problem: str,
) -> str:
    """Delegate to pure core function with locale prefix.

    Thin shell wrapper — builds locale prefix, then delegates to
    format_user_input in core/format_messages.py (pure, no IO).
    """
    prefix = get_phase_prefix(state.locale, problem)
    return _format_user_input_pure(
        input_type=body.type,
        locale_prefix=prefix,
        locale=state.locale,
        forge_state=state,
        confirmed_assumptions=body.confirmed_assumptions,
        rejected_assumptions=body.rejected_assumptions,
        added_assumptions=body.added_assumptions,
        selected_reframings=body.selected_reframings,
        added_reframings=body.added_reframings,
        starred_analogies=body.starred_analogies,
        suggested_domains=body.suggested_domains,
        added_contradictions=body.added_contradictions,
        claim_feedback=body.claim_feedback,
        verdicts=body.verdicts,
        decision=body.decision,
        deep_dive_claim_id=body.deep_dive_claim_id,
        user_insight=body.user_insight,
        user_evidence_urls=body.user_evidence_urls,
    )
