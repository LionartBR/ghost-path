"""Session Stream Helpers — user input processing, state sync, and review events.

Invariants:
    - _apply_user_input mutates ForgeState + triggers phase transition (never commits)
    - _sync_state_to_db mirrors ForgeState phase/round/status to Session for observability
    - _build_review_event returns the correct SSE review event for current phase
    - _update_claim_verdict persists user verdict to KnowledgeClaim (never crashes)

Design Decisions:
    - Extracted from session_agent_stream.py to respect ExMA 200-400 line limit
    - Pure match-case dispatch: no inheritance, no polymorphism
    - _update_claim_verdict never crashes: errors logged, not raised (user flow > data consistency)
"""

import logging
import uuid as uuid_mod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_types import Phase, SessionStatus
from app.core.forge_state import ForgeState
from app.models.knowledge_claim import KnowledgeClaim
from app.schemas.session import UserInput


logger = logging.getLogger(__name__)


async def apply_user_input(
    body: UserInput, state: ForgeState, session, db: AsyncSession,
) -> None:
    """Apply user input to ForgeState, sync to DB, reset history on phase change."""
    state.awaiting_user_input = False
    state.awaiting_input_type = None
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
            await sync_state_to_db(session, state, db)

        case "explore_review":
            if body.starred_analogies:
                for idx in body.starred_analogies:
                    if idx < len(state.cross_domain_analogies):
                        state.cross_domain_analogies[idx]["starred"] = True
            state.transition_to(Phase.SYNTHESIZE)
            session.message_history = []
            await sync_state_to_db(session, state, db)

        case "claims_review":
            state.transition_to(Phase.VALIDATE)
            session.message_history = []
            await sync_state_to_db(session, state, db)

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
                        await update_claim_verdict(
                            db, claim.get("claim_id"), v.verdict,
                            v.rejection_reason, v.qualification,
                        )
            state.transition_to(Phase.BUILD)
            session.message_history = []
            await sync_state_to_db(session, state, db)

        case "build_decision":
            if body.decision == "continue":
                state.reset_for_new_round()
                state.transition_to(Phase.SYNTHESIZE)
                session.message_history = []
                await sync_state_to_db(session, state, db)
            elif body.decision == "deep_dive":
                state.deep_dive_active = True
                state.deep_dive_target_claim_id = body.deep_dive_claim_id
            elif body.decision == "resolve":
                state.transition_to(Phase.CRYSTALLIZE)
                session.message_history = []
                await sync_state_to_db(session, state, db)


async def update_claim_verdict(
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


async def sync_state_to_db(
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


def build_review_event(state: ForgeState) -> dict | None:
    """Build the appropriate review SSE event based on current phase.

    After the agent finishes working in phase X, we emit the review event
    for that phase so the frontend can render the appropriate review UI.
    """
    event = None
    match state.current_phase:
        case Phase.EXPLORE:
            event = {
                "type": "review_explore",
                "data": {
                    "morphological_box": state.morphological_box,
                    "analogies": state.cross_domain_analogies,
                    "contradictions": state.contradictions,
                    "adjacent": state.adjacent_possible,
                },
            }
        case Phase.SYNTHESIZE:
            event = {
                "type": "review_claims",
                "data": {"claims": state.current_round_claims},
            }
        case Phase.VALIDATE:
            event = {
                "type": "review_verdicts",
                "data": {"claims": state.current_round_claims},
            }
        case Phase.BUILD:
            event = {
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
                event = {
                    "type": "knowledge_document",
                    "data": state.knowledge_document_markdown,
                }

    return event
