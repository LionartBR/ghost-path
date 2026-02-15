"""Session Stream Helpers — user input processing, state sync, review events, and SSE wiring.

Invariants:
    - apply_user_input mutates ForgeState + triggers phase transition (never commits)
    - sync_state_to_db mirrors ForgeState phase/round/status to Session for observability
    - build_review_event returns the correct SSE review event for current phase
    - update_claim_verdict persists user verdict to KnowledgeClaim (never crashes)

Design Decisions:
    - Extracted from session_agent_stream.py to respect ExMA import fan-out < 10
    - All SSE wiring helpers live here (client, runner, format) so routes stay thin
    - Pure match-case dispatch: no inheritance, no polymorphism
    - update_claim_verdict never crashes: errors logged, not raised (user flow > data consistency)
"""

import json
import logging
import uuid as uuid_mod
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_types import Locale, Phase, SessionStatus
from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix
from app.core.format_messages import (
    format_user_input as _format_user_input_pure,
    build_initial_stream_message,
    build_resume_message,
)
from app.models.session import Session as SessionModel
from app.models.knowledge_claim import KnowledgeClaim
from app.schemas.session import UserInput
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.services.agent_runner import AgentRunner
from app.config import get_settings


logger = logging.getLogger(__name__)

# ADR: SSE headers prevent proxy/browser buffering of streamed events.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# -- ForgeState management -----------------------------------------------------

def get_or_restore_forge_state(
    session_id, session: SessionModel, forge_states: dict,
) -> ForgeState:
    """Return in-memory ForgeState or restore from DB snapshot.

    Lookup order: forge_states dict -> session.forge_state_snapshot -> new default.
    Always syncs locale from Session (DB is source of truth for locale).
    """
    if session_id in forge_states:
        state = forge_states[session_id]
    elif session.forge_state_snapshot:
        state = ForgeState.from_snapshot(session.forge_state_snapshot)
        forge_states[session_id] = state
        logger.info("Restored ForgeState from DB snapshot (session=%s)", session_id)
    else:
        state = ForgeState()
        forge_states[session_id] = state

    # ADR: Session.locale (DB) is source of truth
    if session.locale:
        db_locale = Locale(session.locale)
        if state.locale != db_locale:
            logger.info(
                "Synced ForgeState locale: %s -> %s (session=%s)",
                state.locale.value, db_locale.value, session_id,
            )
            state.locale = db_locale
            state.locale_confidence = session.locale_confidence or 1.0
    return state


# -- SSE formatting helpers ----------------------------------------------------

def sse_line(event: dict) -> str:
    """Format event as SSE data line."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def done_event(error: bool = False, awaiting_input: bool = False) -> dict:
    """SSE done event."""
    return {"type": "done", "data": {"error": error, "awaiting_input": awaiting_input}}


def patch_snapshot_awaiting(session) -> None:
    """Patch awaiting_user_input in existing snapshot — avoids full rebuild.

    ADR: agent_runner already committed the full snapshot. Dict spread copies
    only top-level keys — cheaper than re-serializing 30+ ForgeState fields.
    """
    if session.forge_state_snapshot:
        session.forge_state_snapshot = {
            **session.forge_state_snapshot,
            "awaiting_user_input": True,
        }


# -- Runner + message helpers --------------------------------------------------

_anthropic_client: ResilientAnthropicClient | None = None


def create_runner(db: AsyncSession) -> AgentRunner:
    """Create AgentRunner with shared Anthropic client singleton."""
    global _anthropic_client
    if _anthropic_client is None:
        settings = get_settings()
        _anthropic_client = ResilientAnthropicClient(
            api_key=settings.anthropic_api_key,
            max_retries=settings.anthropic_max_retries,
            timeout_seconds=settings.anthropic_timeout_seconds,
            enable_1m_context=settings.anthropic_context_1m,
        )
    return AgentRunner(db, _anthropic_client)


def format_user_input(body: UserInput, state: ForgeState, problem: str) -> str:
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
        assumption_responses=body.assumption_responses,
        added_assumptions=body.added_assumptions,
        reframing_responses=body.reframing_responses,
        selected_reframings=body.selected_reframings,
        added_reframings=body.added_reframings,
        analogy_responses=body.analogy_responses,
        starred_analogies=body.starred_analogies,
        suggested_domains=body.suggested_domains,
        added_contradictions=body.added_contradictions,
        claim_responses=body.claim_responses,
        added_claims=body.added_claims,
        claim_feedback=body.claim_feedback,
        verdicts=body.verdicts,
        decision=body.decision,
        deep_dive_claim_id=body.deep_dive_claim_id,
        user_insight=body.user_insight,
        user_evidence_urls=body.user_evidence_urls,
    )


def build_stream_message(session, forge_state: ForgeState) -> str:
    """Build the appropriate stream message for current session state."""
    prefix = get_phase_prefix(forge_state.locale, session.problem)
    if (session.message_history
            and forge_state.current_phase != Phase.DECOMPOSE):
        return build_resume_message(
            prefix, forge_state.current_phase,
            session.problem, forge_state.locale,
        )
    return build_initial_stream_message(
        prefix, session.problem, locale=forge_state.locale,
    )


# -- Review event builders -----------------------------------------------------

def _to_react_flow_graph(state: ForgeState) -> dict:
    """Transform flat ForgeState nodes/edges into React Flow format.

    ADR: knowledge_graph_nodes are stored as flat dicts in ForgeState,
    but the frontend expects React Flow format with nested 'data' object.
    The /graph endpoint does this via Pydantic schemas; SSE events need
    the same transform inline.
    """
    nodes = []
    for n in state.knowledge_graph_nodes:
        scores = n.get("scores", {})
        nodes.append({
            "id": n.get("id", ""),
            "type": n.get("status", "proposed"),
            "data": {
                "claim_text": n.get("claim_text", ""),
                "confidence": n.get("confidence"),
                "scores": {
                    "novelty": scores.get("novelty"),
                    "groundedness": scores.get("groundedness"),
                    "falsifiability": scores.get("falsifiability"),
                    "significance": scores.get("significance"),
                },
                "qualification": n.get("qualification"),
                "rejection_reason": n.get("rejection_reason"),
                "evidence_count": n.get("evidence_count", 0),
                "round_created": n.get("round_created", 0),
            },
        })
    edges = [
        {
            "id": f"edge-{i}",
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "type": e.get("type", "supports"),
        }
        for i, e in enumerate(state.knowledge_graph_edges)
    ]
    return {"nodes": nodes, "edges": edges}


def build_resume_review_event(
    state: ForgeState, session=None,
) -> dict | None:
    """Build review event covering ALL phases (including DECOMPOSE).

    Extends build_review_event (which skips DECOMPOSE) so reconnect
    can re-emit the correct review for any phase.
    """
    if state.current_phase == Phase.DECOMPOSE:
        return {
            "type": "review_decompose",
            "data": {
                "fundamentals": state.fundamentals,
                "assumptions": state.assumptions,
                "reframings": state.reframings,
            },
        }
    return build_review_event(state, session)


def build_review_event(state: ForgeState, session=None) -> dict | None:
    """Build the appropriate review SSE event based on current phase."""
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
                    "graph": _to_react_flow_graph(state),
                    "gaps": state.gaps,
                    "negative_knowledge": state.negative_knowledge,
                    "round": state.current_round,
                    "max_rounds_reached": state.max_rounds_reached,
                },
            }
        case Phase.CRYSTALLIZE:
            if state.knowledge_document_markdown:
                from app.core.session_stats import compute_session_stats
                stats = compute_session_stats(state)
                if session:
                    stats["total_tokens_used"] = getattr(
                        session, "total_tokens_used", 0,
                    )
                    created = getattr(session, "created_at", None)
                    resolved = getattr(session, "resolved_at", None)
                    if created and resolved:
                        stats["duration_seconds"] = int(
                            (resolved - created).total_seconds(),
                        )
                event = {
                    "type": "knowledge_document",
                    "data": {
                        "markdown": state.knowledge_document_markdown,
                        "stats": stats,
                        "graph": _to_react_flow_graph(state),
                        "problem": (
                            getattr(session, "problem", "")
                            if session else ""
                        ),
                    },
                }
    return event


# -- User input processing -----------------------------------------------------

async def apply_user_input(
    body: UserInput, state: ForgeState, session, db: AsyncSession,
) -> None:
    """Apply user input to ForgeState, sync to DB, reset history."""
    state.awaiting_user_input = False
    state.awaiting_input_type = None
    match body.type:
        case "decompose_review":
            _apply_decompose(body, state)
            state.transition_to(Phase.EXPLORE)
            session.message_history = []
            await sync_state_to_db(session, state, db)
        case "explore_review":
            if body.analogy_responses:
                for a_resp in body.analogy_responses:
                    idx = a_resp.analogy_index
                    if idx < len(state.cross_domain_analogies):
                        analogy = state.cross_domain_analogies[idx]
                        if a_resp.selected_option > 0:
                            analogy["starred"] = True
                            options = analogy.get("resonance_options", [])
                            opt_idx = a_resp.selected_option
                            if opt_idx < len(options):
                                analogy["user_resonance"] = options[opt_idx]
                            analogy["selected_resonance_option"] = opt_idx
            elif body.starred_analogies:
                for idx in body.starred_analogies:
                    if idx < len(state.cross_domain_analogies):
                        state.cross_domain_analogies[idx]["starred"] = True
            state.transition_to(Phase.SYNTHESIZE)
            session.message_history = []
            await sync_state_to_db(session, state, db)
        case "claims_review":
            if body.claim_responses:
                for c_resp in body.claim_responses:
                    idx = c_resp.claim_index
                    if idx < len(state.current_round_claims):
                        state.current_round_claims[idx][
                            "user_resonance"
                        ] = c_resp.selected_option
            if body.added_claims:
                state.user_added_claims = [
                    c.strip() for c in body.added_claims if c.strip()
                ]
            state.transition_to(Phase.VALIDATE)
            session.message_history = []
            await sync_state_to_db(session, state, db)
        case "verdicts":
            await _apply_verdicts(body, state, db)
            all_rejected = (
                body.verdicts
                and all(v.verdict == "reject" for v in body.verdicts)
            )
            if all_rejected and not state.max_rounds_reached:
                state.reset_for_new_round()
                state.transition_to(Phase.SYNTHESIZE)
            else:
                state.transition_to(Phase.BUILD)
            session.message_history = []
            await sync_state_to_db(session, state, db)
        case "build_decision":
            await _apply_build_decision(body, state, session, db)


def _apply_decompose(body: UserInput, state: ForgeState) -> None:
    """Apply decompose review selections to ForgeState."""
    if body.reframing_responses:
        for r_resp in body.reframing_responses:
            idx = r_resp.reframing_index
            if idx < len(state.reframings):
                reframing = state.reframings[idx]
                if r_resp.selected_option > 0:
                    reframing["selected"] = True
                    options = reframing.get("resonance_options", [])
                    opt_idx = r_resp.selected_option
                    if opt_idx < len(options):
                        reframing["user_resonance"] = options[opt_idx]
                    reframing["selected_resonance_option"] = opt_idx
    elif body.selected_reframings:
        for idx in body.selected_reframings:
            if idx < len(state.reframings):
                state.reframings[idx]["selected"] = True
    if body.added_reframings:
        state.user_added_reframings.extend(body.added_reframings)
    if body.added_assumptions:
        state.user_added_assumptions.extend(body.added_assumptions)
    if body.assumption_responses:
        for as_resp in body.assumption_responses:
            idx = as_resp.assumption_index
            if idx < len(state.assumptions):
                state.assumptions[idx]["selected_option"] = as_resp.selected_option


async def _apply_verdicts(
    body: UserInput, state: ForgeState, db: AsyncSession,
) -> None:
    """Apply verdicts to claims, persist to DB."""
    if not body.verdicts:
        return
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
            await update_claim_verdict(
                db, claim.get("claim_id"), v.verdict,
                v.rejection_reason, v.qualification,
            )


async def _apply_build_decision(
    body: UserInput, state: ForgeState, session, db: AsyncSession,
) -> None:
    """Apply build decision to ForgeState."""
    if body.decision == "continue":
        state.reset_for_new_round()
        state.transition_to(Phase.SYNTHESIZE)
        session.message_history = []
        await sync_state_to_db(session, state, db)
    elif body.decision == "deep_dive":
        state.deep_dive_active = True
        state.deep_dive_target_claim_id = body.deep_dive_claim_id
    elif body.decision == "resolve":
        session.resolved_at = datetime.now(timezone.utc)
        state.transition_to(Phase.CRYSTALLIZE)
        session.message_history = []
        await sync_state_to_db(session, state, db)


# -- DB sync helpers -----------------------------------------------------------

async def update_claim_verdict(
    db: AsyncSession, claim_id: str | None, verdict: str,
    rejection_reason: str | None, qualification: str | None,
) -> None:
    """Persist user verdict to KnowledgeClaim record. Never crashes."""
    if not claim_id:
        return
    try:
        _VERDICT_TO_STATUS = {
            "accept": "validated", "reject": "rejected",
            "qualify": "qualified", "merge": "superseded",
        }
        result = await db.execute(
            select(KnowledgeClaim).where(
                KnowledgeClaim.id == uuid_mod.UUID(claim_id),
            ),
        )
        db_claim = result.scalar_one_or_none()
        if db_claim:
            db_claim.status = _VERDICT_TO_STATUS.get(
                verdict, db_claim.status,
            )
            if rejection_reason:
                db_claim.rejection_reason = rejection_reason
            if qualification:
                db_claim.qualification = qualification
    except Exception as e:
        logger.warning(f"Failed to update claim verdict: {e}")


async def sync_state_to_db(
    session, state: ForgeState, db: AsyncSession,
) -> None:
    """Sync ForgeState -> DB for observability and crash recovery."""
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
