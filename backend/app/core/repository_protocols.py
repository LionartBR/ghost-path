"""Boundary Protocols — contracts between core and shell.

Invariants:
    - Core NEVER imports from shell — dependency arrows point inward only
    - All IO operations accessed through Protocol types
    - Implementations provided by shell via dependency injection

Design Decisions:
    - Protocol over ABC: structural subtyping, no inheritance hierarchy (ADR: ExMA anti-pattern)
    - Async in Protocol: boundary methods are async because implementations do IO,
      but core pure functions that USE these protocols are never async themselves —
      the shell orchestrates the async calls around the pure logic
"""

from typing import Protocol
from uuid import UUID

from app.core.domain_types import SessionId, ClaimId, EvidenceId, EdgeId, Phase


class SessionLike(Protocol):
    """Structural contract for Session objects passed to handlers and agent runner.

    Avoids coupling shell handlers to the ORM model while giving mypy
    real type information (unlike Any).
    """
    id: UUID
    problem: str
    total_tokens_used: int
    total_input_tokens: int
    total_output_tokens: int
    message_history: list
    forge_state_snapshot: dict | None


class ClaimRepository(Protocol):
    """Contract for knowledge claim persistence — implemented by shell."""
    async def save(self, claim_data: dict, session_id: SessionId) -> ClaimId: ...
    async def get_by_session(self, session_id: SessionId) -> list[dict]: ...
    async def get_by_id(self, claim_id: ClaimId) -> dict | None: ...
    async def update_status(
        self, claim_id: ClaimId, status: str, **fields: object,
    ) -> None: ...
    async def get_negative_knowledge(self, session_id: SessionId) -> list[dict]: ...


class EvidenceRepository(Protocol):
    """Contract for evidence persistence — implemented by shell."""
    async def save(
        self, evidence_data: dict, claim_id: ClaimId, session_id: SessionId,
    ) -> EvidenceId: ...
    async def get_by_claim(self, claim_id: ClaimId) -> list[dict]: ...


class EdgeRepository(Protocol):
    """Contract for knowledge graph edge persistence — implemented by shell."""
    async def save(
        self, edge_data: dict, session_id: SessionId,
    ) -> EdgeId: ...
    async def get_by_session(self, session_id: SessionId) -> list[dict]: ...


class SessionRepository(Protocol):
    """Contract for session persistence — implemented by shell."""
    async def get(self, session_id: SessionId) -> dict | None: ...
    async def save_message_history(
        self, session_id: SessionId, messages: list,
    ) -> None: ...
    async def update_token_usage(
        self, session_id: SessionId, tokens: int,
    ) -> None: ...
    async def update_phase(
        self, session_id: SessionId, phase: Phase, status: str,
    ) -> None: ...
    async def mark_resolved(self, session_id: SessionId) -> None: ...
