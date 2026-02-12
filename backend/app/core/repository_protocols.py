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

from app.core.domain_types import SessionId, RoundId, PremiseId, PremiseScore


class PremiseRepository(Protocol):
    """Contract for premise persistence — implemented by shell."""
    async def save(
        self, premise_data: dict, round_id: RoundId, session_id: SessionId,
    ) -> PremiseId: ...
    async def get_by_session(self, session_id: SessionId) -> list[dict]: ...
    async def get_negative_context(self, session_id: SessionId) -> list[dict]: ...
    async def update_score(
        self, session_id: SessionId, title: str,
        score: PremiseScore, comment: str | None,
    ) -> None: ...


class SessionRepository(Protocol):
    """Contract for session persistence — implemented by shell."""
    async def get(self, session_id: SessionId) -> dict | None: ...
    async def save_message_history(
        self, session_id: SessionId, messages: list,
    ) -> None: ...
    async def update_token_usage(
        self, session_id: SessionId, tokens: int,
    ) -> None: ...
    async def mark_resolved(self, session_id: SessionId) -> None: ...


class RoundRepository(Protocol):
    """Contract for round persistence — implemented by shell."""
    async def create(
        self, session_id: SessionId, round_number: int,
    ) -> RoundId: ...
