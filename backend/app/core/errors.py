"""Error Hierarchy — typed, categorized exceptions for all O-Edger failure modes.

Invariants:
    - Every error has a code (str), category (ErrorCategory), severity (ErrorSeverity)
    - Domain errors (400-level) are recoverable; infrastructure errors (500-level) are critical
    - to_response() produces REST envelope; to_sse_event() produces SSE envelope
    - No internal details leaked in user-facing messages

Design Decisions:
    - Single hierarchy with OEdgerError base: FastAPI global handler catches all (ADR: uniform error shape)
    - ErrorContext as dataclass: rich observability without coupling to logging framework
    - All 15 enforcement error codes have dedicated classes for type safety
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime, timezone


class ErrorSeverity(str, Enum):
    """Error severity for observability and client handling."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """High-level error categories for routing and handling."""
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    RESOURCE_NOT_FOUND = "resource_not_found"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    INTERNAL = "internal"
    CONFLICT = "conflict"
    TIMEOUT = "timeout"


@dataclass
class ErrorContext:
    """Rich context for error observability and debugging."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str | None = None
    tool_name: str | None = None
    phase: str | None = None
    round_number: int | None = None
    user_message: str | None = None
    debug_info: dict[str, Any] | None = None
    retry_after_ms: int | None = None


class OEdgerError(Exception):
    """Base exception for all O-Edger errors."""

    def __init__(
        self,
        message: str,
        code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: ErrorContext | None = None,
        http_status: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.http_status = http_status

    def to_response(self) -> dict:
        """Convert to standardized REST error response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "timestamp": self.context.timestamp.isoformat(),
                "context": {
                    "session_id": self.context.session_id,
                    "tool_name": self.context.tool_name,
                    "phase": self.context.phase,
                    "round_number": self.context.round_number,
                    "retry_after_ms": self.context.retry_after_ms,
                },
            }
        }

    def to_sse_event(self) -> dict:
        """Convert to SSE error event."""
        return {
            "type": "error",
            "data": {
                "code": self.code,
                "message": self.context.user_message or self.message,
                "severity": self.severity.value,
                "recoverable": self.severity in (
                    ErrorSeverity.INFO, ErrorSeverity.WARNING,
                ),
                "tool_name": self.context.tool_name,
            },
        }


# Keep backward compat alias
GhostPathError = OEdgerError


# --- Phase Transition Errors (Rules #1, #2, #9, #10, #11) --------------------

class DecomposeIncompleteError(OEdgerError):
    """Rule #1: Cannot explore without decompose complete."""
    def __init__(self, detail: str, context: ErrorContext | None = None):
        super().__init__(
            f"Decompose phase incomplete: {detail}",
            "DECOMPOSE_INCOMPLETE", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class ExploreIncompleteError(OEdgerError):
    """Rule #2: Cannot synthesize without explore complete."""
    def __init__(self, detail: str, context: ErrorContext | None = None):
        super().__init__(
            f"Explore phase incomplete: {detail}",
            "EXPLORE_INCOMPLETE", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class SynthesisIncompleteError(OEdgerError):
    """Rule #4: Cannot validate without all claims having antithesis."""
    def __init__(self, detail: str, context: ErrorContext | None = None):
        super().__init__(
            f"Synthesis incomplete: {detail}",
            "SYNTHESIS_INCOMPLETE", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class NotCumulativeError(OEdgerError):
    """Rule #9: Round 2+ must reference previous claims."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Round 2+ must reference at least one previous claim.",
            "NOT_CUMULATIVE", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class NegativeKnowledgeMissingError(OEdgerError):
    """Rule #10: Round 2+ must consult negative knowledge."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Round 2+ must call get_negative_knowledge before synthesis.",
            "NEGATIVE_KNOWLEDGE_MISSING", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class MaxRoundsExceededError(OEdgerError):
    """Rule #11: Max 5 rounds per session."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Maximum 5 rounds reached. Must resolve session.",
            "MAX_ROUNDS_EXCEEDED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


# --- Claim Validation Errors (Rules #3, #5, #6, #7, #8) ----------------------

class AntithesisMissingError(OEdgerError):
    """Rule #3: Every synthesis must have antithesis searched."""
    def __init__(self, claim_index: int, context: ErrorContext | None = None):
        super().__init__(
            f"Claim #{claim_index} has no antithesis. Call find_antithesis first.",
            "ANTITHESIS_MISSING", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class FalsificationMissingError(OEdgerError):
    """Rule #5: Every claim must have falsification attempt."""
    def __init__(self, claim_index: int, context: ErrorContext | None = None):
        super().__init__(
            f"Claim #{claim_index} has not been falsification-tested.",
            "FALSIFICATION_MISSING", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class NoveltyUncheckedError(OEdgerError):
    """Rule #6: Every claim must have novelty check."""
    def __init__(self, claim_index: int, context: ErrorContext | None = None):
        super().__init__(
            f"Claim #{claim_index} has not been novelty-checked.",
            "NOVELTY_UNCHECKED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class UngroundedClaimError(OEdgerError):
    """Rule #7: Claims without external evidence are flagged."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Claim has no external evidence. Provide web-sourced evidence.",
            "UNGROUNDED_CLAIM", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.WARNING, context, 400,
        )


class ClaimLimitExceededError(OEdgerError):
    """Rule #8: Max 3 claims per synthesis round."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Round claim limit reached (3/3).",
            "CLAIM_LIMIT_EXCEEDED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


# --- web_search Enforcement Errors (Rules #12, #13, #14, #15) ----------------

class StateOfArtNotResearchedError(OEdgerError):
    """Rule #12: map_state_of_art requires web_search."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "map_state_of_art requires calling web_search first.",
            "STATE_OF_ART_NOT_RESEARCHED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class CrossDomainNotSearchedError(OEdgerError):
    """Rule #13: search_cross_domain requires web_search."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "search_cross_domain requires calling web_search for the target domain first.",
            "CROSS_DOMAIN_NOT_SEARCHED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class AntithesisNotSearchedError(OEdgerError):
    """Rule #14: find_antithesis requires web_search."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "find_antithesis requires calling web_search for counter-evidence first.",
            "ANTITHESIS_NOT_SEARCHED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class FalsificationNotSearchedError(OEdgerError):
    """Rule #15: attempt_falsification requires web_search."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "attempt_falsification requires calling web_search to disprove first.",
            "FALSIFICATION_NOT_SEARCHED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


# --- General Domain Errors ----------------------------------------------------

class ToolValidationError(OEdgerError):
    """Tool input validation failed."""
    def __init__(self, message: str, field_name: str, context: ErrorContext | None = None):
        super().__init__(
            message, "VALIDATION_ERROR", ErrorCategory.VALIDATION,
            ErrorSeverity.ERROR, context, 400,
        )
        self.field_name = field_name


class ResourceNotFoundError(OEdgerError):
    """Requested resource does not exist."""
    def __init__(
        self, resource_type: str, resource_id: str, context: ErrorContext | None = None,
    ):
        super().__init__(
            f"{resource_type} '{resource_id}' not found",
            "RESOURCE_NOT_FOUND", ErrorCategory.RESOURCE_NOT_FOUND,
            ErrorSeverity.ERROR, context, 404,
        )


class InvalidVerdictError(OEdgerError):
    """Invalid verdict for claim."""
    def __init__(self, verdict: str, context: ErrorContext | None = None):
        super().__init__(
            f"Invalid verdict: {verdict}. Must be accept/reject/qualify/merge.",
            "INVALID_VERDICT", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


# --- Infrastructure Errors (500-level) ----------------------------------------

class DatabaseError(OEdgerError):
    """Database operation failed."""
    def __init__(self, message: str, operation: str, context: ErrorContext | None = None):
        super().__init__(
            f"Database {operation} failed: {message}",
            "DATABASE_ERROR", ErrorCategory.DATABASE,
            ErrorSeverity.CRITICAL, context, 503,
        )
        self.operation = operation


class AnthropicAPIError(OEdgerError):
    """Anthropic API call failed."""
    def __init__(
        self,
        message: str,
        api_error_type: str,
        retry_after_ms: int | None = None,
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext()
        ctx.retry_after_ms = retry_after_ms
        super().__init__(
            f"Anthropic API error ({api_error_type}): {message}",
            "ANTHROPIC_API_ERROR", ErrorCategory.EXTERNAL_API,
            ErrorSeverity.CRITICAL, ctx, 503,
        )
        self.api_error_type = api_error_type


class ConcurrencyError(OEdgerError):
    """Concurrent modification detected."""
    def __init__(self, message: str, context: ErrorContext | None = None):
        super().__init__(
            message, "CONCURRENCY_CONFLICT", ErrorCategory.CONFLICT,
            ErrorSeverity.ERROR, context, 409,
        )


class AgentLoopExceededError(OEdgerError):
    """Agent exceeded maximum iteration limit."""
    def __init__(self, max_iterations: int, context: ErrorContext | None = None):
        super().__init__(
            f"Agent exceeded maximum iteration limit ({max_iterations})",
            "AGENT_LOOP_EXCEEDED", ErrorCategory.INTERNAL,
            ErrorSeverity.CRITICAL, context, 500,
        )
