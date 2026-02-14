"""Session Agent Stream — SSE streaming, user input processing, and document download.

Invariants:
    - Every SSE stream instantiates AgentRunner with fresh DB session and Anthropic client
    - User input triggers phase-appropriate processing based on UserInput.type
    - Phase review events (review_decompose, review_explore, etc.) emitted by route, not agent
    - ForgeState synced to DB after every phase transition (observability + crash recovery)
    - Message history reset on phase transition (token explosion prevention)

Design Decisions:
    - Imports _forge_states and get_session_or_404 from session_lifecycle (shared state, DRY)
    - StreamingResponse for SSE: event_generator yields formatted SSE lines
    - Phase review logic in route: agent does the work, route emits the review event
    - History reset: ForgeState already has structured data, conversational history is redundant
"""

import asyncio
import json
import os
import logging
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.schemas.session import UserInput
from app.services.agent_runner import AgentRunner
from app.core.forge_state import ForgeState
from app.core.domain_types import Phase, SessionStatus
from app.models.knowledge_claim import KnowledgeClaim
from app.config import get_settings
from app.api.routes.session_lifecycle import (
    _forge_states, get_session_or_404,
)
from app.models.session import Session as SessionModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _get_or_restore_forge_state(
    session_id: UUID, session: SessionModel,
) -> ForgeState:
    """Return in-memory ForgeState or restore from DB snapshot.

    Lookup order: _forge_states dict → session.forge_state_snapshot → new default.
    """
    if session_id in _forge_states:
        return _forge_states[session_id]
    if session.forge_state_snapshot:
        state = ForgeState.from_snapshot(session.forge_state_snapshot)
        _forge_states[session_id] = state
        logger.info("Restored ForgeState from DB snapshot (session=%s)", session_id)
        return state
    state = ForgeState()
    _forge_states[session_id] = state
    return state


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: UUID, db: AsyncSession = Depends(get_db),
):
    """Initial SSE stream: triggers Phase 1 (DECOMPOSE)."""
    session = await get_session_or_404(session_id, db)
    forge_state = _get_or_restore_forge_state(session_id, session)
    runner = _create_runner(db)

    async def event_generator():
        try:
            message = (
                f'The user has submitted the following problem:\n\n'
                f'"{session.problem}"\n\n'
                f'Begin Phase 1 (DECOMPOSE). Use web_search to research the domain, '
                f'then call decompose_to_fundamentals, map_state_of_art, '
                f'extract_assumptions, and reframe_problem (>= 3 reframings). '
                f'When you are done with all decompose tools, output a summary '
                f'of your findings for the user to review.'
            )
            async for event in runner.run(session, message, forge_state):
                yield _sse_line(event)

            # After agent finishes Phase 1, emit review event
            if forge_state.current_phase == Phase.DECOMPOSE:
                review_event = {
                    "type": "review_decompose",
                    "data": {
                        "fundamentals": forge_state.fundamentals,
                        "assumptions": forge_state.assumptions,
                        "reframings": forge_state.reframings,
                    },
                }
                yield _sse_line(review_event)
        except asyncio.CancelledError:
            logger.info("Client disconnected from stream (session=%s)", session_id)
            return

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
    )


@router.post("/{session_id}/user-input")
async def send_user_input(
    session_id: UUID,
    body: UserInput,
    db: AsyncSession = Depends(get_db),
):
    """Send user input — dispatches to phase-appropriate processing."""
    session = await get_session_or_404(session_id, db)
    forge_state = _get_or_restore_forge_state(session_id, session)
    runner = _create_runner(db)

    message = _format_user_input(body, forge_state)
    await _apply_user_input(body, forge_state, session, db)

    async def event_generator():
        try:
            async for event in runner.run(session, message, forge_state):
                yield _sse_line(event)

            # Emit phase-appropriate review event
            review = _build_review_event(forge_state)
            if review:
                yield _sse_line(review)
        except asyncio.CancelledError:
            logger.info("Client disconnected from user-input stream (session=%s)", session_id)
            return

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
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

def _create_runner(db: AsyncSession) -> AgentRunner:
    """Create AgentRunner with fresh Anthropic client."""
    settings = get_settings()
    client = ResilientAnthropicClient(
        api_key=settings.anthropic_api_key,
        max_retries=settings.anthropic_max_retries,
        timeout_seconds=settings.anthropic_timeout_seconds,
        enable_1m_context=settings.anthropic_context_1m,
    )
    return AgentRunner(db, client)


def _sse_line(event: dict) -> str:
    """Format event as SSE data line."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _format_user_input(body: UserInput, state: ForgeState) -> str:
    """Convert UserInput to a message string for the agent."""
    match body.type:
        case "decompose_review":
            parts = ["The user reviewed the decomposition:"]
            if body.confirmed_assumptions:
                parts.append(f"Confirmed assumptions: indices {body.confirmed_assumptions}")
            if body.rejected_assumptions:
                parts.append(f"Rejected assumptions: indices {body.rejected_assumptions}")
            if body.added_assumptions:
                parts.append(f"Added assumptions: {body.added_assumptions}")
            if body.selected_reframings:
                parts.append(f"Selected reframings: indices {body.selected_reframings}")
            if body.added_reframings:
                parts.append(f"Added reframings: {body.added_reframings}")
            parts.append(
                "Proceed to Phase 2 (EXPLORE). Build a morphological box, "
                "search >= 2 distant domains for analogies (use web_search first), "
                "identify contradictions, and map the adjacent possible."
            )
            return "\n".join(parts)

        case "explore_review":
            parts = ["The user reviewed the exploration:"]
            if body.starred_analogies:
                parts.append(f"Starred analogies: indices {body.starred_analogies}")
            if body.suggested_domains:
                parts.append(f"Suggested domains to search: {body.suggested_domains}")
            if body.added_contradictions:
                parts.append(f"Added contradictions: {body.added_contradictions}")
            parts.append(
                "Proceed to Phase 3 (SYNTHESIZE). For each promising direction, "
                "state a thesis (with evidence), find antithesis (use web_search), "
                "then create a synthesis claim. Generate up to 3 claims this round."
            )
            return "\n".join(parts)

        case "claims_review":
            parts = ["The user reviewed the claims:"]
            if body.claim_feedback:
                for fb in body.claim_feedback:
                    parts.append(f"Claim #{fb.claim_index}:")
                    parts.append(f"  Evidence valid: {fb.evidence_valid}")
                    if fb.counter_example:
                        parts.append(f"  Counter-example: {fb.counter_example}")
                    if fb.synthesis_ignores:
                        parts.append(f"  Missing factor: {fb.synthesis_ignores}")
                    if fb.additional_evidence:
                        parts.append(f"  Additional evidence: {fb.additional_evidence}")
            parts.append(
                "Proceed to Phase 4 (VALIDATE). For each claim, attempt falsification "
                "(use web_search to disprove), check novelty (use web_search), "
                "then score each claim."
            )
            return "\n".join(parts)

        case "verdicts":
            parts = ["The user rendered verdicts on the claims:"]
            if body.verdicts:
                for v in body.verdicts:
                    parts.append(f"Claim #{v.claim_index}: {v.verdict}")
                    if v.rejection_reason:
                        parts.append(f"  Reason: {v.rejection_reason}")
                    if v.qualification:
                        parts.append(f"  Qualification: {v.qualification}")
                    if v.merge_with_claim_id:
                        parts.append(f"  Merge with: {v.merge_with_claim_id}")
            parts.append(
                "Proceed to Phase 5 (BUILD). Add accepted/qualified claims to "
                "the knowledge graph, analyze gaps, and present the build review."
            )
            return "\n".join(parts)

        case "build_decision":
            if body.decision == "continue":
                return (
                    "The user wants to continue with another round. "
                    "Go back to Phase 3 (SYNTHESIZE). Remember: call "
                    "get_negative_knowledge first (Rule #10), and reference "
                    "at least one previous claim (Rule #9)."
                )
            elif body.decision == "deep_dive":
                return (
                    f"The user wants to deep-dive into claim {body.deep_dive_claim_id}. "
                    f"Do a focused EXPLORE -> SYNTHESIZE -> VALIDATE cycle "
                    f"scoped to this claim only."
                )
            elif body.decision == "resolve":
                return (
                    "The user is satisfied with the knowledge graph. "
                    "Proceed to Phase 6 (CRYSTALLIZE). Generate the final "
                    "Knowledge Document with all 10 sections using "
                    "generate_knowledge_document."
                )
            elif body.decision == "add_insight":
                return (
                    f'The user wants to add their own insight:\n'
                    f'"{body.user_insight}"\n'
                    f'Evidence URLs: {body.user_evidence_urls or []}\n'
                    f'Call submit_user_insight to add this to the knowledge graph, '
                    f'then present the updated build review.'
                )
            return "Unknown build decision."

    return "Unknown user input type."


async def _apply_user_input(
    body: UserInput, state: ForgeState, session, db: AsyncSession,
) -> None:
    """Apply user input to ForgeState, sync to DB, reset history on phase change."""
    match body.type:
        case "decompose_review":
            if body.selected_reframings:
                for idx in body.selected_reframings:
                    if idx < len(state.reframings):
                        state.reframings[idx]["selected"] = True
            if body.added_reframings:
                state.user_added_reframings.extend(body.added_reframings)
            if body.added_assumptions:
                state.user_added_assumptions.extend(body.added_assumptions)
            if body.confirmed_assumptions:
                for idx in body.confirmed_assumptions:
                    if idx < len(state.assumptions):
                        state.assumptions[idx]["confirmed"] = True
            if body.rejected_assumptions:
                for idx in body.rejected_assumptions:
                    if idx < len(state.assumptions):
                        state.assumptions[idx]["confirmed"] = False
            state.transition_to(Phase.EXPLORE)
            session.message_history = []
            await _sync_state_to_db(session, state, db)

        case "explore_review":
            if body.starred_analogies:
                for idx in body.starred_analogies:
                    if idx < len(state.cross_domain_analogies):
                        state.cross_domain_analogies[idx]["starred"] = True
            state.transition_to(Phase.SYNTHESIZE)
            session.message_history = []
            await _sync_state_to_db(session, state, db)

        case "claims_review":
            state.transition_to(Phase.VALIDATE)
            session.message_history = []
            await _sync_state_to_db(session, state, db)

        case "verdicts":
            if body.verdicts:
                for v in body.verdicts:
                    if v.claim_index < len(state.current_round_claims):
                        claim = state.current_round_claims[v.claim_index]
                        if v.verdict == "reject":
                            state.negative_knowledge.append({
                                "claim_text": claim.get("claim_text", ""),
                                "rejection_reason": v.rejection_reason,
                                "round": state.current_round,
                            })
                        claim["verdict"] = v.verdict
                        claim["qualification"] = v.qualification

                        # Persist verdict to DB
                        await _update_claim_verdict(
                            db, claim.get("claim_id"), v.verdict,
                            v.rejection_reason, v.qualification,
                        )
            state.transition_to(Phase.BUILD)
            session.message_history = []
            await _sync_state_to_db(session, state, db)

        case "build_decision":
            if body.decision == "continue":
                state.reset_for_new_round()
                state.transition_to(Phase.SYNTHESIZE)
                session.message_history = []
                await _sync_state_to_db(session, state, db)
            elif body.decision == "deep_dive":
                state.deep_dive_active = True
                state.deep_dive_target_claim_id = body.deep_dive_claim_id
            elif body.decision == "resolve":
                state.transition_to(Phase.CRYSTALLIZE)
                session.message_history = []
                await _sync_state_to_db(session, state, db)


async def _update_claim_verdict(
    db: AsyncSession, claim_id: str | None, verdict: str,
    rejection_reason: str | None, qualification: str | None,
) -> None:
    """Persist user verdict to KnowledgeClaim record. Never crashes."""
    if not claim_id:
        return
    try:
        _VERDICT_TO_STATUS = {
            "accept": "validated",
            "reject": "rejected",
            "qualify": "qualified",
            "merge": "superseded",
        }
        result = await db.execute(
            select(KnowledgeClaim).where(
                KnowledgeClaim.id == uuid_mod.UUID(claim_id),
            ),
        )
        db_claim = result.scalar_one_or_none()
        if db_claim:
            db_claim.status = _VERDICT_TO_STATUS.get(verdict, db_claim.status)
            if rejection_reason:
                db_claim.rejection_reason = rejection_reason
            if qualification:
                db_claim.qualification = qualification
    except Exception as e:
        logger.warning(f"Failed to update claim verdict: {e}")


async def _sync_state_to_db(
    session, state: ForgeState, db: AsyncSession,
) -> None:
    """Sync ForgeState -> DB for observability and crash recovery.

    ADR: ForgeState is in-memory but DB should reflect current phase/round/status
    so GET /sessions returns accurate data.
    """
    _PHASE_TO_STATUS = {
        Phase.DECOMPOSE: SessionStatus.DECOMPOSING,
        Phase.EXPLORE: SessionStatus.EXPLORING,
        Phase.SYNTHESIZE: SessionStatus.SYNTHESIZING,
        Phase.VALIDATE: SessionStatus.VALIDATING,
        Phase.BUILD: SessionStatus.BUILDING,
        Phase.CRYSTALLIZE: SessionStatus.CRYSTALLIZED,
    }
    phase_list = list(Phase)
    session.current_phase = phase_list.index(state.current_phase) + 1
    session.current_round = state.current_round
    session.status = _PHASE_TO_STATUS[state.current_phase].value
    session.forge_state_snapshot = state.to_snapshot()
    try:
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to sync state to DB: {e}")


def _build_review_event(state: ForgeState) -> dict | None:
    """Build the appropriate review SSE event based on current phase.

    After the agent finishes working in phase X, we emit the review event
    for that phase so the frontend can render the appropriate review UI.
    """
    match state.current_phase:
        case Phase.EXPLORE:
            return {
                "type": "review_explore",
                "data": {
                    "morphological_box": state.morphological_box,
                    "analogies": state.cross_domain_analogies,
                    "contradictions": state.contradictions,
                    "adjacent": state.adjacent_possible,
                },
            }
        case Phase.SYNTHESIZE:
            return {
                "type": "review_claims",
                "data": {"claims": state.current_round_claims},
            }
        case Phase.VALIDATE:
            return {
                "type": "review_verdicts",
                "data": {"claims": state.current_round_claims},
            }
        case Phase.BUILD:
            return {
                "type": "review_build",
                "data": {
                    "graph": {
                        "nodes": state.knowledge_graph_nodes,
                        "edges": state.knowledge_graph_edges,
                    },
                    "gaps": state.gaps,
                    "negative_knowledge": state.negative_knowledge,
                    "round": state.current_round,
                    "max_rounds_reached": state.max_rounds_reached,
                },
            }
        case Phase.CRYSTALLIZE:
            if state.knowledge_document_markdown:
                return {
                    "type": "knowledge_document",
                    "data": state.knowledge_document_markdown,
                }
    return None
