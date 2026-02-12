"""Error Hierarchy — typed, categorized exceptions for all GhostPath failure modes.

Invariants:
    - Every error has a code (str), category (ErrorCategory), severity (ErrorSeverity)
    - Domain errors (400-level) are recoverable; infrastructure errors (500-level) are critical
    - to_response() produces REST envelope; to_sse_event() produces SSE envelope
    - No internal details leaked in user-facing messages

Design Decisions:
    - Single hierarchy with GhostPathError base: FastAPI global handler catches all (ADR: uniform error shape)
    - ErrorContext as dataclass: rich observability without coupling to logging framework
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
    round_number: int | None = None
    user_message: str | None = None
    debug_info: dict[str, Any] | None = None
    retry_after_ms: int | None = None


class GhostPathError(Exception):
    """Base exception for all GhostPath errors."""

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


# ─── Domain Errors (400-level) ──────────────────────────────────

class ToolValidationError(GhostPathError):
    """Tool input validation failed."""
    def __init__(self, message: str, field: str, context: ErrorContext | None = None):
        super().__init__(
            message, "VALIDATION_ERROR", ErrorCategory.VALIDATION,
            ErrorSeverity.ERROR, context, 400,
        )
        self.field = field


class GateNotSatisfiedError(GhostPathError):
    """Analysis gate prerequisite not met."""
    def __init__(self, missing_gates: list[str], context: ErrorContext | None = None):
        super().__init__(
            f"Missing mandatory analysis gates: {', '.join(missing_gates)}",
            "GATES_NOT_SATISFIED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )
        self.missing_gates = missing_gates


class BufferFullError(GhostPathError):
    """Round buffer already contains 3 premises."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Round buffer is full (3/3). Call present_round or discard a premise.",
            "ROUND_BUFFER_FULL", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class AxiomNotChallengedError(GhostPathError):
    """Radical premise attempted without calling challenge_axiom."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Radical premises require calling challenge_axiom first.",
            "AXIOM_NOT_CHALLENGED", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class NegativeContextMissingError(GhostPathError):
    """Rounds 2+ attempted without calling get_negative_context."""
    def __init__(self, context: ErrorContext | None = None):
        super().__init__(
            "Rounds 2+ require calling get_negative_context before generating premises.",
            "NEGATIVE_CONTEXT_MISSING", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class IncompleteRoundError(GhostPathError):
    """present_round called with fewer than 3 premises."""
    def __init__(self, count: int, context: ErrorContext | None = None):
        super().__init__(
            f"Round requires exactly 3 premises. Current buffer: {count}/3.",
            "INCOMPLETE_ROUND", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class UntestedPremisesError(GhostPathError):
    """present_round called with untested premises."""
    def __init__(self, untested: int, context: ErrorContext | None = None):
        super().__init__(
            f"{untested} premise(s) have not passed the obviousness_test.",
            "UNTESTED_PREMISES", ErrorCategory.BUSINESS_RULE,
            ErrorSeverity.ERROR, context, 400,
        )


class ResourceNotFoundError(GhostPathError):
    """Requested resource does not exist."""
    def __init__(
        self, resource_type: str, resource_id: str, context: ErrorContext | None = None,
    ):
        super().__init__(
            f"{resource_type} '{resource_id}' not found",
            "RESOURCE_NOT_FOUND", ErrorCategory.RESOURCE_NOT_FOUND,
            ErrorSeverity.ERROR, context, 404,
        )


# ─── Infrastructure Errors (500-level) ──────────────────────────

class DatabaseError(GhostPathError):
    """Database operation failed."""
    def __init__(self, message: str, operation: str, context: ErrorContext | None = None):
        super().__init__(
            f"Database {operation} failed: {message}",
            "DATABASE_ERROR", ErrorCategory.DATABASE,
            ErrorSeverity.CRITICAL, context, 503,
        )
        self.operation = operation


class AnthropicAPIError(GhostPathError):
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


class ConcurrencyError(GhostPathError):
    """Concurrent modification detected."""
    def __init__(self, message: str, context: ErrorContext | None = None):
        super().__init__(
            message, "CONCURRENCY_CONFLICT", ErrorCategory.CONFLICT,
            ErrorSeverity.ERROR, context, 409,
        )


class AgentLoopExceededError(GhostPathError):
    """Agent exceeded maximum iteration limit."""
    def __init__(self, max_iterations: int, context: ErrorContext | None = None):
        super().__init__(
            f"Agent exceeded maximum iteration limit ({max_iterations})",
            "AGENT_LOOP_EXCEEDED", ErrorCategory.INTERNAL,
            ErrorSeverity.CRITICAL, context, 500,
        )
