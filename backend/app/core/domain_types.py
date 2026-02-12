"""Domain Types — rich types that replace bare primitives across the codebase.

Invariants:
    - SessionId, RoundId, PremiseId wrap UUIDs — never use bare UUID in domain logic
    - PremiseScore is bounded 0.0–10.0
    - ObviousnessScore is bounded 0.0–1.0
    - All valid states encoded as Enums — no raw string matching

Design Decisions:
    - NewType over dataclass wrappers: zero runtime cost, full type-checker support (ADR: hackathon speed)
    - str Enums: serialize to JSON without custom encoders (ADR: Anthropic tool_result is JSON)
"""

from enum import Enum
from typing import NewType
from uuid import UUID


# ─── Identity Types ──────────────────────────────────────────────

SessionId = NewType("SessionId", UUID)
RoundId = NewType("RoundId", UUID)
PremiseId = NewType("PremiseId", UUID)


# ─── Value Types ─────────────────────────────────────────────────

PremiseScore = NewType("PremiseScore", float)           # 0.0–10.0
ObviousnessScore = NewType("ObviousnessScore", float)   # 0.0–1.0
MutationStrength = NewType("MutationStrength", float)   # 0.1–1.0


# ─── Enums ───────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    """Session lifecycle states — maps to DB `status` column."""
    CREATED = "created"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class AnalysisGate(str, Enum):
    """The 3 mandatory analysis gates. All must complete before generation."""
    DECOMPOSE = "decompose_problem"
    CONVENTIONAL = "map_conventional_approaches"
    AXIOMS = "extract_hidden_axioms"


class PremiseType(str, Enum):
    """Premise classification — radical requires challenge_axiom prerequisite."""
    INITIAL = "initial"
    CONSERVATIVE = "conservative"
    RADICAL = "radical"
    COMBINATION = "combination"


class ToolCategory(str, Enum):
    """Tool groupings for registry and observability."""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    INNOVATION = "innovation"
    INTERACTION = "interaction"
    MEMORY = "memory"
