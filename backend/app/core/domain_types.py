"""Domain Types — rich types replacing bare primitives across the O-Edger codebase.

Invariants:
    - SessionId, ClaimId, EvidenceId wrap UUIDs — never use bare UUID in domain logic
    - All valid states encoded as Enums — no raw string matching
    - Phase enum defines the 6-phase pipeline order

Design Decisions:
    - NewType over dataclass wrappers: zero runtime cost, full type-checker support (ADR: hackathon speed)
    - str Enums: serialize to JSON without custom encoders (ADR: Anthropic tool_result is JSON)
"""

from enum import Enum
from typing import NewType
from uuid import UUID


# --- Identity Types -----------------------------------------------------------

SessionId = NewType("SessionId", UUID)
ClaimId = NewType("ClaimId", UUID)
EvidenceId = NewType("EvidenceId", UUID)
EdgeId = NewType("EdgeId", UUID)
ReframingId = NewType("ReframingId", UUID)
AnalogyId = NewType("AnalogyId", UUID)
ContradictionId = NewType("ContradictionId", UUID)


# --- Enums --------------------------------------------------------------------

class Phase(str, Enum):
    """The 6-phase O-Edger pipeline. Order matters."""
    DECOMPOSE = "decompose"
    EXPLORE = "explore"
    SYNTHESIZE = "synthesize"
    VALIDATE = "validate"
    BUILD = "build"
    CRYSTALLIZE = "crystallize"


class SessionStatus(str, Enum):
    """Session lifecycle states — maps to DB `status` column."""
    DECOMPOSING = "decomposing"
    EXPLORING = "exploring"
    SYNTHESIZING = "synthesizing"
    VALIDATING = "validating"
    BUILDING = "building"
    CRYSTALLIZED = "crystallized"
    CANCELLED = "cancelled"


class ClaimStatus(str, Enum):
    """Knowledge claim lifecycle."""
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    QUALIFIED = "qualified"
    SUPERSEDED = "superseded"


class ClaimType(str, Enum):
    """How the claim was produced."""
    THESIS = "thesis"
    ANTITHESIS = "antithesis"
    SYNTHESIS = "synthesis"
    USER_CONTRIBUTED = "user_contributed"
    MERGED = "merged"


class ClaimConfidence(str, Enum):
    """Epistemic confidence level."""
    SPECULATIVE = "speculative"
    EMERGING = "emerging"
    GROUNDED = "grounded"


class EvidenceType(str, Enum):
    """Relationship between evidence and its claim."""
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"


class EdgeType(str, Enum):
    """Typed edges in the knowledge graph DAG."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    MERGED_FROM = "merged_from"


class VerdictType(str, Enum):
    """User's epistemic decision on a claim."""
    ACCEPT = "accept"
    REJECT = "reject"
    QUALIFY = "qualify"
    MERGE = "merge"


class ReframingType(str, Enum):
    """Types of problem reframing (Phase 1)."""
    SCOPE_CHANGE = "scope_change"
    ENTITY_QUESTION = "entity_question"
    VARIABLE_CHANGE = "variable_change"
    DOMAIN_CHANGE = "domain_change"


class EvidenceContributor(str, Enum):
    """Who contributed the evidence."""
    AGENT = "agent"
    USER = "user"


class SemanticDistance(str, Enum):
    """Distance between source and target domain for analogies."""
    NEAR = "near"
    MEDIUM = "medium"
    FAR = "far"


class ToolCategory(str, Enum):
    """Tool groupings for registry and observability."""
    DECOMPOSE = "decompose"
    EXPLORE = "explore"
    SYNTHESIZE = "synthesize"
    VALIDATE = "validate"
    BUILD = "build"
    CRYSTALLIZE = "crystallize"
    CROSS_CUTTING = "cross_cutting"


# --- Constants ----------------------------------------------------------------

MAX_CLAIMS_PER_ROUND: int = 3
MAX_ROUNDS_PER_SESSION: int = 5
PHASE_ORDER: list[Phase] = list(Phase)
