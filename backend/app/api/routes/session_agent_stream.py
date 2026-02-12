"""Session Agent Stream — SSE streaming, user input processing, and spec download.

Invariants:
    - Every SSE stream instantiates AgentRunner with fresh DB session and Anthropic client
    - Spec files saved to /tmp/ghostpath/specs/{session_id}.md
    - User input types: "scores" | "ask_user_response" | "resolved"

Design Decisions:
    - Imports _session_states and get_session_or_404 from session_lifecycle (shared state, DRY)
    - StreamingResponse for SSE: event_generator yields formatted SSE lines
    - ResilientAnthropicClient instantiated per-request: settings may change between requests
"""

import json
import os
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.models.premise import Premise
from app.schemas.session import UserInput
from app.services.agent_runner import AgentRunner
from app.core.session_state import SessionState
from app.config import get_settings
from app.api.routes.session_lifecycle import (
    _session_states, get_session_or_404,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: UUID, db: AsyncSession = Depends(get_db),
):
    """Initial SSE stream: triggers agent to analyze and generate round 1."""
    session = await get_session_or_404(session_id, db)
    session_state = _session_states.setdefault(session_id, SessionState())
    settings = get_settings()
    client = ResilientAnthropicClient(
        api_key=settings.anthropic_api_key,
        max_retries=settings.anthropic_max_retries,
        timeout_seconds=settings.anthropic_timeout_seconds,
        enable_1m_context=settings.anthropic_context_1m,
    )
    runner = AgentRunner(db, client)

    async def event_generator():
        message = (
            f"The user has submitted the following problem:\n\n"
            f"\"{session.problem}\"\n\n"
            f"Begin by calling decompose_problem, "
            f"map_conventional_approaches, "
            f"and extract_hidden_axioms. "
            f"Then generate 3 premises for the first round."
        )
        async for event in runner.run(session, message, session_state):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
    )


@router.post("/{session_id}/user-input")
async def send_user_input(
    session_id: UUID,
    body: UserInput,
    db: AsyncSession = Depends(get_db),
):
    """Send user input (scores, ask_user response, or resolved)."""
    session = await get_session_or_404(session_id, db)
    session_state = _session_states.setdefault(session_id, SessionState())
    settings = get_settings()
    client = ResilientAnthropicClient(
        api_key=settings.anthropic_api_key,
        max_retries=settings.anthropic_max_retries,
        timeout_seconds=settings.anthropic_timeout_seconds,
        enable_1m_context=settings.anthropic_context_1m,
    )
    runner = AgentRunner(db, client)

    match body.type:
        case "scores":
            message = _format_scores_message(body.scores)
            for s in body.scores:
                await _update_premise_score(db, session_id, s)
        case "ask_user_response":
            message = f'The user responded: "{body.response}"'
        case "resolved":
            winner = body.winner
            message = (
                f"The user triggered 'Problem Resolved'. "
                f'The winning premise is: "{winner.title}" '
                f"(score: {winner.score}). "
                f"Respond with a positive and enthusiastic message, "
                f"then call generate_final_spec with the complete "
                f"content in Markdown."
            )

    async def event_generator():
        spec_content = None
        async for event in runner.run(session, message, session_state):
            if event["type"] == "final_spec":
                spec_content = event["data"]
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        if spec_content:
            file_path = f"/tmp/ghostpath/specs/{session_id}.md"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(spec_content)
            yield (
                f"data: {json.dumps({'type': 'spec_file_ready', 'data': {'download_url': f'/api/v1/sessions/{session_id}/spec'}}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
    )


@router.get("/{session_id}/spec")
async def download_spec(session_id: UUID):
    """Download the final spec as a .md file."""
    file_path = f"/tmp/ghostpath/specs/{session_id}.md"
    if not os.path.exists(file_path):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Spec not found",
        )
    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=f"ghostpath-spec-{session_id}.md",
    )


def _format_scores_message(scores: list) -> str:
    """Format user scores as a message for the agent."""
    lines = []
    for s in scores:
        line = f'- "{s.premise_title}": {s.score}/10'
        if s.comment:
            line += f' — "{s.comment}"'
        lines.append(line)
    best = max(scores, key=lambda s: s.score)
    return (
        "The user scored the premises:\n"
        + "\n".join(lines)
        + f'\n\nHighest scored: "{best.premise_title}" '
        f"({best.score}/10).\n"
        "Use this feedback to evolve the next round. "
        "Call get_negative_context first, then generate 3 new premises."
    )


async def _update_premise_score(
    db: AsyncSession, session_id: UUID, score_data,
) -> None:
    """Update premise score in DB."""
    try:
        result = await db.execute(
            select(Premise)
            .where(Premise.session_id == session_id)
            .where(Premise.title == score_data.premise_title)
            .order_by(Premise.created_at.desc())
            .limit(1),
        )
        premise = result.scalar_one_or_none()
        if premise:
            premise.score = score_data.score
            premise.user_comment = score_data.comment
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to update premise score: {e}")
        await db.rollback()
