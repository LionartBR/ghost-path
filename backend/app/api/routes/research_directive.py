"""Research Directive — user steers agent exploration between iterations.

Invariants:
    - Directive is ephemeral (ForgeState only, no DB commit)
    - Session must exist and have an active ForgeState (stream running)
    - Returns 202 Accepted (fire-and-forget, directive consumed asynchronously)

Design Decisions:
    - Reads _forge_states directly (same in-memory dict the agent loop holds)
      (ADR: shared reference on same asyncio loop — writes visible immediately)
    - No DB write: directives are transient steering signals, not persisted state
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.routes.session_lifecycle import _forge_states

router = APIRouter(prefix="/api/v1/sessions", tags=["research-directive"])


class ResearchDirective(BaseModel):
    directive_type: str  # "explore_more" | "skip_domain"
    query: str
    domain: str


@router.post(
    "/{session_id}/research-directive",
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_research_directive(
    session_id: UUID, body: ResearchDirective,
):
    """Queue a research directive for injection between agent iterations."""
    forge_state = _forge_states.get(session_id)
    if not forge_state:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No active stream for this session",
        )
    if forge_state.cancelled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Session is cancelled",
        )
    forge_state.add_research_directive(
        body.directive_type, body.query, body.domain,
    )
    return {"status": "accepted"}
