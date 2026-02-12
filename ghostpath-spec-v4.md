# GhostPath — Technical Spec v4.0 (Agent Architecture + Guardrails)

## Stack

- **Backend**: Python 3.13 + FastAPI 0.128 + Uvicorn 0.40
- **Frontend**: React 19 + TypeScript 5.9 + Vite 7 + Tailwind 4
- **LLM**: Anthropic Claude Opus 4.6 (`claude-opus-4-6`, 1M context)
- **Agent Runtime**: Anthropic Tool Use (native function calling)
- **Database**: PostgreSQL 18 (SQLAlchemy 2.0 + Alembic 1.18)
- **Streaming**: SSE (Server-Sent Events)
- **Containerization**: Docker + Docker Compose

---

## Agent Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CLAUDE OPUS 4.6                         │
│                     (Agent Runtime)                           │
│                                                              │
│  The agent decides the flow, but tools enforce guardrails:   │
│  - Error if trying to generate premise without prior analysis│
│  - Forced premise count per round                            │
│  - User interaction via ask_user (choice/response)           │
│  - Mandatory final report upon resolution                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ ANALYSIS TOOLS (mandatory gates)                    │     │
│  │  • decompose_problem                                │     │
│  │  • map_conventional_approaches                      │     │
│  │  • extract_hidden_axioms                            │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │ GENERATION TOOLS (with prerequisite enforcement)    │     │
│  │  • generate_premise        ← ERROR if gates missing │     │
│  │  • mutate_premise          ← ERROR if gates missing │     │
│  │  • cross_pollinate         ← ERROR if gates missing │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │ INNOVATION TOOLS (enforce originality)              │     │
│  │  • challenge_axiom                                  │     │
│  │  • import_foreign_domain                            │     │
│  │  • obviousness_test                                 │     │
│  │  • invert_problem                                   │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │ BUILT-IN TOOLS (Anthropic server-side)             │     │
│  │  • web_search            ← real-time web research   │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │ INTERACTION TOOLS                                   │     │
│  │  • ask_user               ← question/options style  │     │
│  │  • present_round          ← requires 3 premises     │     │
│  │  • generate_final_spec    ← generates .md of winner │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │ MEMORY TOOLS                                        │     │
│  │  • store_premise                                    │     │
│  │  • query_premises                                   │     │
│  │  • get_negative_context                             │     │
│  │  • get_context_usage                                │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## 0. Error Architecture & Standardized Responses

GhostPath uses a layered error architecture that maps domain errors to HTTP responses and SSE events. Every error is typed, categorized, and carries rich context for observability.

### Error Envelope (REST)

All API error responses follow this envelope:

```json
{
  "error": {
    "code": "GATES_NOT_SATISFIED",
    "message": "Missing mandatory analysis gates: decompose_problem, extract_hidden_axioms",
    "category": "business_rule",
    "severity": "error",
    "timestamp": "2026-02-11T14:30:00Z",
    "context": {
      "session_id": "abc-123",
      "tool_name": "generate_premise",
      "round_number": 1,
      "retry_after_ms": null
    }
  }
}
```

### Error Envelope (SSE)

Tool and system errors within the SSE stream follow this format:

```json
{
  "type": "error",
  "data": {
    "code": "ANTHROPIC_API_ERROR",
    "message": "API rate limit exceeded, retrying...",
    "severity": "critical",
    "recoverable": false,
    "tool_name": "generate_premise"
  }
}
```

### Core Error Types

```python
# app/core/errors.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime, timezone


class ErrorSeverity(str, Enum):
    """Error severity for observability and client handling."""
    INFO = "info"          # Expected flow (e.g., obviousness rejection)
    WARNING = "warning"    # Non-fatal (e.g., axiom not in list)
    ERROR = "error"        # Recoverable (e.g., gates not satisfied)
    CRITICAL = "critical"  # System failure (e.g., database down)


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
                "recoverable": self.severity in (ErrorSeverity.INFO, ErrorSeverity.WARNING),
                "tool_name": self.context.tool_name,
            },
        }


# ─── Domain Errors (400-level) ──────────────────────────────────

class ToolValidationError(GhostPathError):
    """Tool input validation failed."""
    def __init__(self, message: str, field: str, context: ErrorContext | None = None):
        super().__init__(message, "VALIDATION_ERROR", ErrorCategory.VALIDATION,
                         ErrorSeverity.ERROR, context, 400)
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
    def __init__(self, resource_type: str, resource_id: str, context: ErrorContext | None = None):
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
        super().__init__(message, "CONCURRENCY_CONFLICT", ErrorCategory.CONFLICT,
                         ErrorSeverity.ERROR, context, 409)


class AgentLoopExceededError(GhostPathError):
    """Agent exceeded maximum iteration limit."""
    def __init__(self, max_iterations: int, context: ErrorContext | None = None):
        super().__init__(
            f"Agent exceeded maximum iteration limit ({max_iterations})",
            "AGENT_LOOP_EXCEEDED", ErrorCategory.INTERNAL,
            ErrorSeverity.CRITICAL, context, 500,
        )
```

### Error Code Quick Reference

| Code | HTTP | Severity | Trigger |
|------|------|----------|---------|
| `VALIDATION_ERROR` | 400 | error | Invalid tool/API input |
| `GATES_NOT_SATISFIED` | 400 | error | Generation without analysis |
| `ROUND_BUFFER_FULL` | 400 | error | 4th premise in buffer |
| `AXIOM_NOT_CHALLENGED` | 400 | error | Radical without challenge_axiom |
| `NEGATIVE_CONTEXT_MISSING` | 400 | error | Round 2+ without get_negative_context |
| `INCOMPLETE_ROUND` | 400 | error | present_round with <3 premises |
| `UNTESTED_PREMISES` | 400 | error | present_round without obviousness_test |
| `TOO_OBVIOUS` | 200 | info | Obviousness score > 0.6 (auto-removed) |
| `INVALID_INDEX` | 400 | error | Invalid premise_buffer_index |
| `RESOURCE_NOT_FOUND` | 404 | error | Session/spec not found |
| `DATABASE_ERROR` | 503 | critical | DB commit/query failure |
| `ANTHROPIC_API_ERROR` | 503 | critical | LLM API failure |
| `CONCURRENCY_CONFLICT` | 409 | error | Concurrent session mutation |
| `AGENT_LOOP_EXCEEDED` | 500 | critical | Agent > 50 iterations |
| `TOOL_EXECUTION_ERROR` | 500 | critical | Unexpected error in tool handler |
| `UNKNOWN_TOOL` | 400 | error | Agent called nonexistent tool |

---

## 0.1 Anthropic API Resilience

The Anthropic client is wrapped with exponential backoff, jitter, rate limit detection, and timeout handling.

```python
# app/infrastructure/anthropic_client.py

import asyncio
import random
import logging

import anthropic
from anthropic import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
)

from app.core.errors import AnthropicAPIError, ErrorContext

logger = logging.getLogger(__name__)


class ResilientAnthropicClient:
    """
    Wraps Anthropic client with retry logic, timeouts, and error mapping.

    Retry strategy:
    - Rate limits (429): exponential backoff with jitter, respects Retry-After
    - Transient errors (5xx, connection): exponential backoff, max 3 retries
    - Client errors (4xx): immediate failure, no retry
    - Timeouts: configurable, immediate failure
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 60_000,
        timeout_seconds: int = 300,
    ):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        tools: list,
        messages: list,
        context: ErrorContext | None = None,
    ):
        """Create message with automatic retry on transient failures."""
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    tools=tools,
                    messages=messages,
                )
                logger.info(
                    "Anthropic API success",
                    extra={
                        "attempt": attempt + 1,
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                )
                return response

            except RateLimitError as e:
                retry_after_ms = self._extract_retry_after(e)
                if attempt >= self.max_retries:
                    raise AnthropicAPIError(
                        "Rate limit exceeded after retries",
                        "rate_limit",
                        retry_after_ms=retry_after_ms,
                        context=context,
                    )
                delay = retry_after_ms or self._backoff(attempt)
                logger.warning(f"Rate limit hit, retry after {delay}ms (attempt {attempt + 1})")
                await asyncio.sleep(delay / 1000)

            except (APIConnectionError, InternalServerError) as e:
                if attempt >= self.max_retries:
                    raise AnthropicAPIError(
                        f"Transient failure after {self.max_retries} retries: {e}",
                        "connection_error",
                        context=context,
                    )
                delay = self._backoff(attempt)
                logger.warning(f"Transient error, retry after {delay}ms: {e}")
                await asyncio.sleep(delay / 1000)

            except APITimeoutError:
                raise AnthropicAPIError("API timeout", "timeout", context=context)

            except APIError as e:
                raise AnthropicAPIError(str(e), "client_error", context=context)

            except Exception as e:
                logger.error(f"Unexpected Anthropic error: {e}", exc_info=True)
                raise AnthropicAPIError(str(e), "unknown", context=context)

    def _backoff(self, attempt: int) -> int:
        """Exponential backoff with ±25% jitter."""
        delay = min(self.max_delay_ms, (2 ** attempt) * self.base_delay_ms)
        return int(delay * random.uniform(0.75, 1.25))

    def _extract_retry_after(self, error: RateLimitError) -> int | None:
        """Extract Retry-After header (returns milliseconds)."""
        try:
            if hasattr(error, "response") and error.response:
                val = error.response.headers.get("retry-after")
                if val:
                    return int(val) * 1000
        except Exception:
            pass
        return None
```

---

## 0.2 Database Resilience

All database operations use a session manager with automatic rollback, connection pooling, and health checks.

```python
# app/infrastructure/database.py

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError, SQLAlchemyError

from app.core.errors import DatabaseError, ErrorContext

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """
    Manages async database sessions with:
    - Connection pooling (pool_pre_ping for stale connection detection)
    - Automatic rollback on exception
    - Typed exception mapping to DatabaseError
    """

    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 10):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide session with auto-rollback on exception."""
        session = self._session_factory()
        try:
            yield session
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"DB integrity error: {e}")
            raise DatabaseError("Integrity constraint violated", "commit")
        except OperationalError as e:
            await session.rollback()
            logger.error(f"DB operational error: {e}")
            raise DatabaseError("Connection or operational error", "execute")
        except DBAPIError as e:
            await session.rollback()
            logger.error(f"DB driver error: {e}")
            raise DatabaseError("Database driver error", "query")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"SQLAlchemy error: {e}")
            raise DatabaseError("Database operation failed", "unknown")
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity (for readiness probes)."""
        try:
            async with self.session() as db:
                await db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return False


# Singleton (initialized on startup)
db_manager: DatabaseSessionManager | None = None


def init_db(database_url: str, **kwargs):
    global db_manager
    db_manager = DatabaseSessionManager(database_url, **kwargs)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    async with db_manager.session() as session:
        yield session
```

---

## 0.3 Structured Logging

All modules use structured JSON logging with context fields.

```python
# app/infrastructure/observability.py

import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields (session_id, tool_name, etc.)
        for key in ("session_id", "tool_name", "error_code", "attempt",
                     "input_tokens", "output_tokens", "round_number"):
            val = record.__dict__.get(key)
            if val is not None:
                log[key] = val
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def setup_logging(level: str = "INFO", fmt: str = "json"):
    """Configure logging for the application."""
    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s — %(message)s"
        ))
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))
```

---

## 0.4 Configuration

```python
# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    database_url: str = "postgresql+asyncpg://ghostpath:ghostpath@db:5432/ghostpath"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Anthropic
    anthropic_api_key: str
    anthropic_max_retries: int = 3
    anthropic_timeout_seconds: int = 300
    anthropic_base_delay_ms: int = 1000
    anthropic_max_delay_ms: int = 60_000

    # Agent
    agent_max_iterations: int = 50
    agent_model: str = "claude-opus-4-6"

    # API
    cors_origins: list[str] = ["http://localhost:5173"]

    # Observability
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 1. Prerequisite Enforcement (Gate System)

The backend maintains a **per-session state machine** that tracks which analysis tools have already been called. Generation tools return an error if the gates have not been satisfied.

### Session State Machine

```python
# app/services/session_state.py

from dataclasses import dataclass, field
from enum import Enum


class AnalysisGate(str, Enum):
    DECOMPOSE = "decompose_problem"
    CONVENTIONAL = "map_conventional_approaches"
    AXIOMS = "extract_hidden_axioms"


@dataclass
class SessionState:
    """Internal session state for rule enforcement."""

    # Completed analysis gates
    completed_gates: set[AnalysisGate] = field(default_factory=set)

    # Current round premises (buffer before present_round)
    current_round_buffer: list[dict] = field(default_factory=list)

    # Current round
    current_round_number: int = 0

    # Whether the agent has run obviousness_test on buffer premises
    obviousness_tested: set[int] = field(default_factory=set)  # buffer indices

    # Extracted axioms (to validate that challenge_axiom uses real axioms)
    extracted_axioms: list[str] = field(default_factory=list)

    # Whether challenge_axiom has been called (required for radical premises)
    axiom_challenged: bool = False

    # Whether get_negative_context was called this round (required for rounds 2+)
    negative_context_fetched: bool = False

    # User interaction status
    awaiting_user_input: bool = False
    awaiting_input_type: str | None = None  # "scores" | "ask_user" | "resolved"

    @property
    def all_gates_satisfied(self) -> bool:
        return {
            AnalysisGate.DECOMPOSE,
            AnalysisGate.CONVENTIONAL,
            AnalysisGate.AXIOMS,
        }.issubset(self.completed_gates)

    @property
    def missing_gates(self) -> list[str]:
        required = {
            AnalysisGate.DECOMPOSE,
            AnalysisGate.CONVENTIONAL,
            AnalysisGate.AXIOMS,
        }
        missing = required - self.completed_gates
        return [g.value for g in missing]

    @property
    def premises_in_buffer(self) -> int:
        return len(self.current_round_buffer)

    @property
    def premises_remaining(self) -> int:
        return 3 - self.premises_in_buffer

    @property
    def all_premises_tested(self) -> bool:
        return len(self.obviousness_tested) == len(self.current_round_buffer)
```

### Gate Enforcement in Tool Handlers

```python
# app/services/tool_handlers.py

class ToolHandlers:
    def __init__(self, db: AsyncSession, session_state: SessionState):
        self.db = db
        self.state = session_state

    # ─────────────────────────────────────
    # ANALYSIS TOOLS (mark gates)
    # ─────────────────────────────────────

    async def decompose_problem(self, session, input_data) -> dict:
        session.problem_decomposition = input_data
        self.state.completed_gates.add(AnalysisGate.DECOMPOSE)
        await self.db.commit()
        return {
            "status": "ok",
            "gates_completed": [g.value for g in self.state.completed_gates],
            "gates_remaining": self.state.missing_gates,
            "message": (
                "Decomposition completed. "
                f"Remaining gates: {self.state.missing_gates or 'None — ready to generate premises.'}"
            ),
        }

    async def map_conventional_approaches(self, session, input_data) -> dict:
        self.state.completed_gates.add(AnalysisGate.CONVENTIONAL)
        return {
            "status": "ok",
            "gates_completed": [g.value for g in self.state.completed_gates],
            "gates_remaining": self.state.missing_gates,
            "message": (
                "Conventional approaches mapped. "
                f"Remaining gates: {self.state.missing_gates or 'None — ready to generate premises.'}"
            ),
        }

    async def extract_hidden_axioms(self, session, input_data) -> dict:
        self.state.completed_gates.add(AnalysisGate.AXIOMS)
        # Store axiom STRINGS for later validation by challenge_axiom
        if "axioms" in input_data:
            self.state.extracted_axioms.extend(
                a["axiom"] for a in input_data["axioms"]
            )
        return {
            "status": "ok",
            "gates_completed": [g.value for g in self.state.completed_gates],
            "gates_remaining": self.state.missing_gates,
            "message": (
                "Axioms extracted. "
                f"Remaining gates: {self.state.missing_gates or 'None — ready to generate premises.'}"
            ),
        }

    # ─────────────────────────────────────
    # GENERATION TOOLS (check gates)
    # ─────────────────────────────────────

    async def generate_premise(self, session, input_data) -> dict:
        # GATE CHECK — return error if prerequisites not satisfied
        if not self.state.all_gates_satisfied:
            return {
                "status": "error",
                "error_code": "GATES_NOT_SATISFIED",
                "message": (
                    f"ERROR: You cannot generate premises yet. "
                    f"Missing mandatory tools: {self.state.missing_gates}. "
                    f"Call these tools first before generating any premise."
                ),
                "missing_gates": self.state.missing_gates,
            }

        # RADICAL CHECK — radical premises require challenge_axiom first
        if input_data.get("premise_type") == "radical" and not self.state.axiom_challenged:
            return {
                "status": "error",
                "error_code": "AXIOM_NOT_CHALLENGED",
                "message": (
                    "ERROR: Radical premises require calling challenge_axiom first. "
                    "Challenge an axiom from extract_hidden_axioms before generating a radical premise."
                ),
            }

        # NEGATIVE CONTEXT CHECK — rounds 2+ require get_negative_context
        if self.state.current_round_number >= 1 and not self.state.negative_context_fetched:
            return {
                "status": "error",
                "error_code": "NEGATIVE_CONTEXT_MISSING",
                "message": (
                    "ERROR: Rounds 2+ require calling get_negative_context before generating premises. "
                    "This ensures you learn from previous low-scored premises."
                ),
            }

        # BUFFER CHECK — do not accept more than 3 per round
        if self.state.premises_in_buffer >= 3:
            return {
                "status": "error",
                "error_code": "ROUND_BUFFER_FULL",
                "message": (
                    "ERROR: There are already 3 premises in the current round buffer. "
                    "Call present_round to present to the user or "
                    "discard a premise before generating another."
                ),
            }

        # Add to buffer
        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)

        remaining = self.state.premises_remaining
        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Premise #{premise_index + 1} generated and added to buffer. "
                f"{str(remaining) + ' premise(s) remaining to complete the round.' if remaining > 0 else 'Buffer complete! Run obviousness_test on each premise then call present_round.'}"
            ),
        }

    async def mutate_premise(self, session, input_data) -> dict:
        if not self.state.all_gates_satisfied:
            return {
                "status": "error",
                "error_code": "GATES_NOT_SATISFIED",
                "message": f"ERROR: Missing mandatory tools: {self.state.missing_gates}.",
                "missing_gates": self.state.missing_gates,
            }

        if input_data.get("premise_type") == "radical" and not self.state.axiom_challenged:
            return {
                "status": "error",
                "error_code": "AXIOM_NOT_CHALLENGED",
                "message": "ERROR: Radical premises require calling challenge_axiom first.",
            }

        if self.state.current_round_number >= 1 and not self.state.negative_context_fetched:
            return {
                "status": "error",
                "error_code": "NEGATIVE_CONTEXT_MISSING",
                "message": "ERROR: Rounds 2+ require calling get_negative_context first.",
            }

        if self.state.premises_in_buffer >= 3:
            return {
                "status": "error",
                "error_code": "ROUND_BUFFER_FULL",
                "message": "ERROR: Round buffer is already full (3/3).",
            }

        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)
        remaining = self.state.premises_remaining

        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Mutation applied. Premise #{premise_index + 1} in buffer. "
                f"{str(remaining) + ' remaining.' if remaining > 0 else 'Buffer complete!'}"
            ),
        }

    async def cross_pollinate(self, session, input_data) -> dict:
        if not self.state.all_gates_satisfied:
            return {
                "status": "error",
                "error_code": "GATES_NOT_SATISFIED",
                "message": f"ERROR: Missing mandatory tools: {self.state.missing_gates}.",
                "missing_gates": self.state.missing_gates,
            }

        if self.state.current_round_number >= 1 and not self.state.negative_context_fetched:
            return {
                "status": "error",
                "error_code": "NEGATIVE_CONTEXT_MISSING",
                "message": "ERROR: Rounds 2+ require calling get_negative_context first.",
            }

        if self.state.premises_in_buffer >= 3:
            return {
                "status": "error",
                "error_code": "ROUND_BUFFER_FULL",
                "message": "ERROR: Round buffer is already full (3/3).",
            }

        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)
        remaining = self.state.premises_remaining

        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Cross-pollination completed. Premise #{premise_index + 1} in buffer. "
                f"{str(remaining) + ' remaining.' if remaining > 0 else 'Buffer complete!'}"
            ),
        }

    # ─────────────────────────────────────
    # INNOVATION TOOLS
    # ─────────────────────────────────────

    async def challenge_axiom(self, session, input_data) -> dict:
        # Validate that the axiom was previously extracted
        axiom = input_data.get("axiom", "")
        if self.state.extracted_axioms and axiom not in self.state.extracted_axioms:
            return {
                "status": "warning",
                "message": (
                    f"WARNING: The axiom '{axiom}' was not identified by extract_hidden_axioms. "
                    f"Available axioms: {self.state.extracted_axioms}. "
                    f"Proceeding anyway, but consider using a previously mapped axiom."
                ),
            }
        # Mark that an axiom has been challenged (unlocks radical premises)
        self.state.axiom_challenged = True
        return {
            "status": "ok",
            "message": f"Axiom '{axiom}' challenged with strategy '{input_data.get('violation_strategy')}'.",
        }

    async def import_foreign_domain(self, session, input_data) -> dict:
        return {
            "status": "ok",
            "source_domain": input_data["source_domain"],
            "message": f"Analogy imported from {input_data['source_domain']}.",
        }

    async def obviousness_test(self, session, input_data) -> dict:
        premise_index = input_data.get("premise_buffer_index")
        score = input_data.get("obviousness_score", 0.0)

        if premise_index is None or premise_index >= self.state.premises_in_buffer:
            return {
                "status": "error",
                "error_code": "INVALID_INDEX",
                "message": (
                    f"ERROR: Invalid premise_buffer_index={premise_index}. "
                    f"Buffer has {self.state.premises_in_buffer} premise(s) (indices 0–{self.state.premises_in_buffer - 1})."
                ),
            }

        # ENFORCE: reject premises with score > 0.6
        if score > 0.6:
            self.state.current_round_buffer.pop(premise_index)
            # Re-index tested set after removal
            self.state.obviousness_tested = {
                (i if i < premise_index else i - 1)
                for i in self.state.obviousness_tested
                if i != premise_index
            }
            return {
                "status": "rejected",
                "error_code": "TOO_OBVIOUS",
                "message": (
                    f"REJECTED: Premise #{premise_index + 1} scored {score} (> 0.6 threshold). "
                    f"Removed from buffer. Generate a replacement."
                ),
                "premises_in_buffer": self.state.premises_in_buffer,
                "premises_remaining": self.state.premises_remaining,
            }

        self.state.obviousness_tested.add(premise_index)
        return {
            "status": "ok",
            "tested_count": len(self.state.obviousness_tested),
            "total_in_buffer": self.state.premises_in_buffer,
            "all_tested": self.state.all_premises_tested,
            "message": (
                f"Obviousness test PASSED for premise #{premise_index + 1} (score {score}). "
                f"{'All tested — ready for present_round.' if self.state.all_premises_tested else f'{self.state.premises_in_buffer - len(self.state.obviousness_tested)} test(s) remaining.'}"
            ),
        }

    async def invert_problem(self, session, input_data) -> dict:
        return {
            "status": "ok",
            "inversion_type": input_data["inversion_type"],
            "message": "Problem inverted. Use the insights to generate non-obvious premises.",
        }

    # ─────────────────────────────────────
    # INTERACTION TOOLS
    # ─────────────────────────────────────

    async def ask_user(self, session, input_data) -> dict:
        """
        Presents a question to the user with selectable options.
        The flow PAUSES here and awaits user response.
        """
        self.state.awaiting_user_input = True
        self.state.awaiting_input_type = "ask_user"
        return {
            "status": "awaiting_user_response",
            "message": "Question presented to user. Awaiting response.",
        }

    async def present_round(self, session, input_data) -> dict:
        """
        Presents the round of 3 premises to the user for evaluation.
        Validates that we have exactly 3 premises in the buffer and all tested.
        """
        # VALIDATION: exactly 3 premises
        if self.state.premises_in_buffer != 3:
            return {
                "status": "error",
                "error_code": "INCOMPLETE_ROUND",
                "message": (
                    f"ERROR: The round requires exactly 3 premises. "
                    f"Current buffer: {self.state.premises_in_buffer}/3. "
                    f"Generate {self.state.premises_remaining} more premise(s) before presenting."
                ),
            }

        # VALIDATION: all passed obviousness_test
        if not self.state.all_premises_tested:
            untested = self.state.premises_in_buffer - len(self.state.obviousness_tested)
            return {
                "status": "error",
                "error_code": "UNTESTED_PREMISES",
                "message": (
                    f"ERROR: {untested} premise(s) in the buffer have not passed the obviousness_test. "
                    f"All premises MUST be tested before presenting to the user."
                ),
            }

        # Create round in DB
        self.state.current_round_number += 1
        new_round = Round(
            session_id=session.id,
            round_number=self.state.current_round_number,
        )
        self.db.add(new_round)
        await self.db.flush()

        # Store premises FROM THE BUFFER (source of truth, not input_data)
        premises_data = []
        for p_data in self.state.current_round_buffer:
            premise = Premise(
                round_id=new_round.id,
                session_id=session.id,
                title=p_data["title"],
                body=p_data["body"],
                premise_type=p_data["premise_type"],
                violated_axiom=p_data.get("violated_axiom"),
                cross_domain_source=p_data.get("cross_domain_source"),
            )
            self.db.add(premise)
            premises_data.append({
                "title": p_data["title"],
                "body": p_data["body"],
                "premise_type": p_data["premise_type"],
                "violated_axiom": p_data.get("violated_axiom"),
                "cross_domain_source": p_data.get("cross_domain_source"),
            })

        await self.db.commit()

        # Clear buffer and per-round flags for next round
        self.state.current_round_buffer.clear()
        self.state.obviousness_tested.clear()
        self.state.axiom_challenged = False
        self.state.negative_context_fetched = False

        # Mark that we are awaiting user input
        self.state.awaiting_user_input = True
        self.state.awaiting_input_type = "scores"

        return {
            "status": "awaiting_user_scores",
            "round_number": self.state.current_round_number,
            # Include premises in result so agent_runner can forward to frontend
            "premises": premises_data,
            "message": (
                f"Round {self.state.current_round_number} presented to the user with 3 premises. "
                f"Awaiting evaluation. The user will provide scores (0.0–10.0) for each premise "
                f"and optionally comments. They can also trigger 'Problem Resolved' to "
                f"finish with a winning premise."
            ),
        }

    async def generate_final_spec(self, session, input_data) -> dict:
        """
        Generates the final .md spec from the winning premise.
        Called after the user triggers 'Problem Resolved'.
        """
        session.status = "resolved"
        session.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "status": "ok",
            "message": (
                "Session closed. Generate the final spec content in Markdown. "
                "The backend will save it as .md and deliver it to the user."
            ),
        }

    # ─────────────────────────────────────
    # MEMORY TOOLS (same as v3)
    # ─────────────────────────────────────

    async def store_premise(self, session, input_data) -> dict:
        premise = await self.db.execute(
            select(Premise)
            .where(Premise.session_id == session.id)
            .where(Premise.title == input_data["title"])
            .order_by(Premise.created_at.desc())
            .limit(1)
        )
        premise = premise.scalar_one_or_none()
        if premise:
            premise.score = input_data.get("score")
            premise.user_comment = input_data.get("user_comment")
            premise.is_winner = input_data.get("is_winner", False)
            await self.db.commit()
        return {"status": "stored"}

    async def query_premises(self, session, input_data) -> dict:
        query = select(Premise).where(Premise.session_id == session.id)
        filter_type = input_data["filter"]
        if filter_type == "winners":
            query = query.where(Premise.is_winner == True)
        elif filter_type == "top_scored":
            query = query.where(Premise.score >= 7.0).order_by(Premise.score.desc())
        elif filter_type == "low_scored":
            query = query.where(Premise.score < 5.0)
        elif filter_type == "by_type":
            query = query.where(Premise.premise_type == input_data.get("premise_type"))
        query = query.limit(input_data.get("limit", 10))
        result = await self.db.execute(query)
        premises = result.scalars().all()
        return {
            "premises": [
                {
                    "title": p.title,
                    "body": p.body[:200],
                    "score": float(p.score) if p.score else None,
                    "premise_type": p.premise_type,
                    "user_comment": p.user_comment,
                }
                for p in premises
            ]
        }

    async def get_negative_context(self, session, input_data) -> dict:
        # Mark that negative context was fetched (unlocks generation for rounds 2+)
        self.state.negative_context_fetched = True

        result = await self.db.execute(
            select(Premise)
            .where(Premise.session_id == session.id)
            .where(Premise.score < 5.0)
            .where(Premise.score.isnot(None))
            .order_by(Premise.score.asc())
        )
        premises = result.scalars().all()
        if not premises:
            return {"negative_premises": [], "message": "No negative context yet."}
        return {
            "negative_premises": [
                {
                    "title": p.title,
                    "score": float(p.score),
                    "user_comment": p.user_comment,
                }
                for p in premises
            ],
            "message": (
                "Avoid repeating the conceptual mistakes of these premises, "
                "but do not avoid the same conceptual space."
            ),
        }

    async def get_context_usage(self, session, input_data) -> dict:
        max_tokens = 1_000_000
        used = session.total_tokens_used
        num_rounds = max(len(session.rounds), 1)
        avg = used / num_rounds
        return {
            "tokens_used": used,
            "tokens_limit": max_tokens,
            "tokens_remaining": max_tokens - used,
            "usage_percentage": round((used / max_tokens) * 100, 2),
            "estimated_rounds_left": int((max_tokens - used) / avg) if avg > 0 else 999,
        }
```

---

## 2. Complete Tool Definitions (Anthropic Tool Use Format)

### Analysis Tools

```python
TOOLS_ANALYSIS = [
    {
        "name": "decompose_problem",
        "description": (
            "Decomposes the user's problem into key dimensions. "
            "MANDATORY GATE: must be called before any generation tool. "
            "Without this tool, generate_premise/mutate_premise/cross_pollinate return ERROR."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_statement": {
                    "type": "string",
                    "description": "The problem as described by the user"
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key dimensions identified in the problem"
                },
                "constraints_real": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Real constraints of the problem"
                },
                "constraints_assumed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Constraints that are ASSUMED but may not be real"
                },
                "success_metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "How to measure if the problem has been solved"
                }
            },
            "required": ["problem_statement", "dimensions"]
        }
    },
    {
        "name": "map_conventional_approaches",
        "description": (
            "Maps conventional approaches that most people would try. "
            "MANDATORY GATE: must be called before generating premises. "
            "The goal is to know WHAT TO AVOID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "approaches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "limitations": {"type": "string"},
                            "why_common": {"type": "string"}
                        }
                    },
                    "description": "List of conventional approaches with their limitations"
                }
            },
            "required": ["approaches"]
        }
    },
    {
        "name": "extract_hidden_axioms",
        "description": (
            "Identifies hidden axioms — assumptions everyone takes for granted. "
            "MANDATORY GATE: must be called before generating premises. "
            "The returned axioms become available for challenge_axiom."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "axioms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "axiom": {"type": "string"},
                            "why_assumed": {"type": "string"},
                            "what_if_violated": {"type": "string"}
                        }
                    },
                    "description": "List of axioms with justification and violation consequences"
                },
                "existing_axioms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Previously identified axioms (to avoid repetition)"
                }
            },
            "required": ["axioms"]
        }
    },
]
```

### Generation Tools

```python
TOOLS_GENERATION = [
    {
        "name": "generate_premise",
        "description": (
            "Generates ONE premise. Adds it to the current round buffer. "
            "RETURNS ERROR if analysis gates have not been satisfied. "
            "RETURNS ERROR if the buffer already has 3 premises. "
            "The return informs how many premises are left to complete the round. "
            "After generating 3 premises, run obviousness_test on each one "
            "then call present_round."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Concise premise title (1 line)"
                },
                "body": {
                    "type": "string",
                    "description": "Premise body (2-3 paragraphs)"
                },
                "premise_type": {
                    "type": "string",
                    "enum": ["initial", "conservative", "radical", "combination"]
                },
                "direction_hint": {
                    "type": "string",
                    "description": "Conceptual direction being explored"
                },
                "violated_axiom": {
                    "type": "string",
                    "description": "Violated axiom (required for radical type)"
                },
                "cross_domain_source": {
                    "type": "string",
                    "description": "Inspiration source domain (when applicable)"
                }
            },
            "required": ["title", "body", "premise_type"]
        }
    },
    {
        "name": "mutate_premise",
        "description": (
            "Applies mutation to an existing premise and adds the result to the buffer. "
            "RETURNS ERROR if gates not satisfied or buffer full. "
            "The return informs how many premises are left."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_title": {
                    "type": "string",
                    "description": "Source premise title"
                },
                "source_body": {
                    "type": "string",
                    "description": "Source premise body"
                },
                "title": {
                    "type": "string",
                    "description": "Mutated premise title"
                },
                "body": {
                    "type": "string",
                    "description": "Mutated premise body"
                },
                "premise_type": {
                    "type": "string",
                    "enum": ["conservative", "radical", "combination"]
                },
                "mutation_strength": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 1.0,
                    "description": "0.1 = subtle refinement, 1.0 = complete inversion"
                },
                "violated_axiom": {"type": "string"},
                "cross_domain_source": {"type": "string"}
            },
            "required": ["source_title", "title", "body", "premise_type", "mutation_strength"]
        }
    },
    {
        "name": "cross_pollinate",
        "description": (
            "Combines premises and adds the result to the buffer. "
            "RETURNS ERROR if gates not satisfied or buffer full. "
            "The return informs how many premises are left."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "primary_title": {"type": "string"},
                "primary_body": {"type": "string"},
                "secondary_premises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "element_to_extract": {"type": "string"}
                        }
                    }
                },
                "title": {
                    "type": "string",
                    "description": "Title of the resulting combined premise"
                },
                "body": {
                    "type": "string",
                    "description": "Body of the resulting combined premise"
                },
                "premise_type": {
                    "type": "string",
                    "enum": ["combination"],
                    "description": "Always 'combination' for cross-pollinated premises"
                },
                "synthesis_strategy": {"type": "string"},
                "violated_axiom": {"type": "string"},
                "cross_domain_source": {"type": "string"}
            },
            "required": ["primary_title", "title", "body", "premise_type", "synthesis_strategy"]
        }
    },
]
```

### Innovation Tools

```python
TOOLS_INNOVATION = [
    {
        "name": "challenge_axiom",
        "description": (
            "Challenges an axiom identified by extract_hidden_axioms. "
            "If the axiom was not previously extracted, returns WARNING. "
            "The agent CANNOT generate a radical variation without calling this tool first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "axiom": {"type": "string"},
                "violation_strategy": {
                    "type": "string",
                    "enum": ["negate", "invert", "remove", "replace", "exaggerate"]
                },
                "resulting_insight": {
                    "type": "string",
                    "description": "The insight that emerges from violating the axiom"
                }
            },
            "required": ["axiom", "violation_strategy", "resulting_insight"]
        }
    },
    {
        "name": "import_foreign_domain",
        "description": (
            "Finds an analogy from a completely different domain than the problem. "
            "The source domain MUST have maximum semantic distance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_domain": {"type": "string"},
                "source_domain": {"type": "string"},
                "analogy_seed": {"type": "string"},
                "translated_insight": {
                    "type": "string",
                    "description": "How the analogy translates to the original problem"
                }
            },
            "required": ["problem_domain", "source_domain", "analogy_seed", "translated_insight"]
        }
    },
    {
        "name": "obviousness_test",
        "description": (
            "Tests whether a premise in the buffer is obvious. "
            "MANDATORY for each premise before present_round. "
            "Returns how many premises still need testing. "
            "Score > 0.6 = discard and regenerate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "premise_buffer_index": {
                    "type": "integer",
                    "description": "Premise index in the buffer (0, 1, or 2)"
                },
                "premise_title": {"type": "string"},
                "obviousness_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "0.0 = completely novel, 1.0 = totally obvious"
                },
                "justification": {
                    "type": "string",
                    "description": "Why this premise is or is not obvious"
                }
            },
            "required": ["premise_buffer_index", "premise_title", "obviousness_score", "justification"]
        }
    },
    {
        "name": "invert_problem",
        "description": (
            "Inverts the problem to find non-obvious solutions. "
            "Charlie Munger's technique: 'Invert, always invert.'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "original_problem": {"type": "string"},
                "inversion_type": {
                    "type": "string",
                    "enum": ["cause_problem", "maximize_failure", "remove_solution", "reverse_stakeholders"]
                },
                "inverted_framing": {
                    "type": "string",
                    "description": "The problem reframed in inverted form"
                },
                "insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-3 insights that emerge from the inversion"
                }
            },
            "required": ["original_problem", "inversion_type", "inverted_framing", "insights"]
        }
    },
]
```

### Interaction Tools

```python
TOOLS_INTERACTION = [
    {
        "name": "ask_user",
        "description": (
            "Asks the user a question with selectable options. "
            "Similar to Claude Code's AskUserTool: displays the question, "
            "the user selects an option or types a free-form response. "
            "Use to align direction, capture preferences, validate "
            "meta-analysis, or any moment that needs directed user input. "
            "The flow PAUSES until the user responds."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to display to the user"
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short option text displayed as a button"
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional option description (displayed below the label)"
                            }
                        },
                        "required": ["label"]
                    },
                    "minItems": 2,
                    "maxItems": 5,
                    "description": "Selectable options. The last option can be 'Other (type your response)'."
                },
                "allow_free_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "If true, displays a free text field in addition to the options"
                },
                "context": {
                    "type": "string",
                    "description": "Optional context displayed above the question (e.g., meta-analysis)"
                }
            },
            "required": ["question", "options"]
        }
    },
    {
        "name": "present_round",
        "description": (
            "Presents the round of 3 premises to the user. "
            "Premises are read from the internal buffer (filled by generate_premise / "
            "mutate_premise / cross_pollinate). Do NOT re-pass the premises. "
            "RETURNS ERROR if buffer does not have exactly 3 premises. "
            "RETURNS ERROR if any premise has not passed the obviousness_test. "
            "The flow PAUSES until the user submits scores. "
            "The user can also trigger 'Problem Resolved' "
            "to finish with a winning premise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "round_summary": {
                    "type": "string",
                    "description": "Brief summary of the strategy used for this round's premises"
                }
            },
            "required": []
        }
    },
    {
        "name": "generate_final_spec",
        "description": (
            "Generates the final .md spec from the winning premise. "
            "Called ONLY after the user triggers 'Problem Resolved' "
            "and indicates the winning premise. "
            "The agent should respond with a positive message before calling, "
            "informing the user that it will develop the idea in depth. "
            "The generated content is saved as a .md file and delivered to the user."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "winning_premise_title": {"type": "string"},
                "winning_premise_body": {"type": "string"},
                "winning_score": {"type": "number"},
                "problem_statement": {"type": "string"},
                "evolution_summary": {
                    "type": "string",
                    "description": "Summary of the evolutionary journey (rounds, pivots, key insights)"
                },
                "spec_content": {
                    "type": "string",
                    "description": (
                        "The COMPLETE spec content in Markdown. Must include: "
                        "1) Executive Summary, "
                        "2) The Problem (original context), "
                        "3) The Solution (premise expanded into actionable details), "
                        "4) How It Works (mechanisms, architecture, flows), "
                        "5) Implementation (concrete steps, suggested timeline), "
                        "6) Risks and Mitigations, "
                        "7) Success Metrics, "
                        "8) Evolutionary Journey (how we got here). "
                        "Be thorough and actionable. The user should be able to "
                        "act based on this document."
                    )
                }
            },
            "required": [
                "winning_premise_title",
                "winning_premise_body",
                "problem_statement",
                "spec_content"
            ]
        }
    },
]
```

### Memory Tools

```python
TOOLS_MEMORY = [
    {
        "name": "store_premise",
        "description": "Stores a premise with user score and comment in the database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "premise_type": {"type": "string"},
                "score": {"type": "number"},
                "user_comment": {"type": "string"},
                "is_winner": {"type": "boolean"},
                "round_number": {"type": "integer"}
            },
            "required": ["title", "premise_type", "round_number"]
        }
    },
    {
        "name": "query_premises",
        "description": "Queries premises from the database. Filters by score, type, round.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "enum": ["all", "winners", "top_scored", "low_scored", "by_type", "by_round"]
                },
                "premise_type": {"type": "string"},
                "round_number": {"type": "integer"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["filter"]
        }
    },
    {
        "name": "get_negative_context",
        "description": (
            "Returns premises with score < 5.0 as negative context. "
            "MUST be called before generating premises in rounds 2+."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_context_usage",
        "description": "Returns usage metrics for the 1M token context window.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]
```

### Tools Registry

```python
# app/services/tools_registry.py

from app.services.tool_definitions import (
    TOOLS_ANALYSIS,
    TOOLS_GENERATION,
    TOOLS_INNOVATION,
    TOOLS_INTERACTION,
    TOOLS_MEMORY,
)

# ADR: web_search is an Anthropic built-in tool (server-side, not custom).
# Uses a different schema format (type instead of name+input_schema).
# Anthropic handles execution — no ToolHandlers method needed.
# Pricing: $10/1000 searches, billed to the same ANTHROPIC_API_KEY.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,  # per agent turn — controls cost and context usage
}

ALL_TOOLS = (
    TOOLS_ANALYSIS
    + TOOLS_GENERATION
    + TOOLS_INNOVATION
    + TOOLS_INTERACTION
    + TOOLS_MEMORY
    + [WEB_SEARCH_TOOL]
)
```

---

## 3. Agent Runner with Resilience

```python
# app/services/agent_runner.py

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tool_handlers import ToolHandlers
from app.services.session_state import SessionState
from app.services.tools_registry import ALL_TOOLS
from app.services.system_prompt import AGENT_SYSTEM_PROMPT
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.core.errors import GhostPathError, AgentLoopExceededError, ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Agent runner with:
    - MAX_ITERATIONS guard against infinite loops
    - Tool error isolation (_execute_tool_safe)
    - SSE stream error boundary (asyncio.CancelledError, generic Exception)
    - Non-fatal fallbacks for token usage and message history commits
    """

    MAX_ITERATIONS = 50

    def __init__(self, db: AsyncSession, anthropic_client: ResilientAnthropicClient):
        self.client = anthropic_client
        self.model = "claude-opus-4-6"
        self.db = db

    async def run(self, session, user_message: str, session_state: SessionState):
        """
        Async generator yielding SSE events.

        Events:
        - agent_text:    agent text to display
        - tool_call:     agent calling a tool (name + input preview)
        - tool_error:    tool returned error (code + message)
        - premises:      3 premises ready to display as cards
        - ask_user:      question with options for the user
        - final_spec:    .md spec final content
        - context_usage: context usage update
        - error:         system-level error (API, DB, loop exceeded)
        - done:          agent finished turn {error: bool, awaiting_input: bool}
        """
        iteration = 0

        try:
            messages = self._build_messages(session, user_message)

            while iteration < self.MAX_ITERATIONS:
                iteration += 1

                # ── Call Anthropic API (with retry in client) ──
                try:
                    response = await self.client.create_message(
                        model=self.model,
                        max_tokens=16384,
                        system=AGENT_SYSTEM_PROMPT,
                        tools=ALL_TOOLS,
                        messages=messages,
                        context=ErrorContext(session_id=str(session.id)),
                    )
                except GhostPathError as e:
                    logger.error(f"Anthropic API error: {e.message}",
                                 extra={"session_id": str(session.id)})
                    yield e.to_sse_event()
                    yield {"type": "done", "data": {"error": True, "awaiting_input": False}}
                    return

                # ── Update token usage (non-fatal if fails) ──
                try:
                    tokens = response.usage.input_tokens + response.usage.output_tokens
                    session.total_tokens_used += tokens
                    # Track web search requests for cost observability
                    web_searches = getattr(response.usage, "server_tool_use", {})
                    if web_searches:
                        logger.info(f"Web searches this turn: {web_searches.get('web_search_requests', 0)}",
                                    extra={"session_id": str(session.id)})
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Failed to update token usage: {e}")

                yield {"type": "context_usage", "data": self._get_context_usage(session)}

                # ── Process response blocks ──
                assistant_content = []
                has_tool_use = False
                should_pause = False

                for block in response.content:
                    assistant_content.append(block)
                    if block.type == "text":
                        yield {"type": "agent_text", "data": block.text}
                    elif block.type == "tool_use":
                        has_tool_use = True
                        yield {
                            "type": "tool_call",
                            "data": {"tool": block.name, "input_preview": str(block.input)[:300]},
                        }
                    elif block.type == "server_tool_use":
                        # web_search — executed server-side by Anthropic, no client handling needed
                        yield {
                            "type": "tool_call",
                            "data": {"tool": block.name, "input_preview": str(block.input)[:300]},
                        }
                    elif block.type == "web_search_tool_result":
                        # Search results — already resolved, just forward to frontend
                        result_urls = [
                            r.get("url", "") for r in getattr(block, "content", [])
                            if hasattr(r, "get") and r.get("type") == "web_search_result"
                        ]
                        yield {
                            "type": "tool_result",
                            "data": f"Web search returned {len(result_urls)} result(s)",
                        }

                # Handle pause_turn stop reason (long-running web search)
                if response.stop_reason == "pause_turn":
                    serialized_content = [block.model_dump() for block in assistant_content]
                    messages.append({"role": "assistant", "content": serialized_content})
                    continue  # let Claude continue its turn

                if not has_tool_use:
                    yield {"type": "done", "data": {"error": False, "awaiting_input": False}}
                    return

                # ── Execute tools with error isolation ──
                serialized_content = [block.model_dump() for block in assistant_content]
                messages.append({"role": "assistant", "content": serialized_content})
                tool_results = []
                handlers = ToolHandlers(self.db, session_state)

                for block in assistant_content:
                    if block.type != "tool_use":
                        continue

                    result = await self._execute_tool_safe(
                        handlers, session, block.name, block.input
                    )

                    # Forward errors to frontend
                    if result.get("status") == "error":
                        yield {
                            "type": "tool_error",
                            "data": {
                                "tool": block.name,
                                "error_code": result.get("error_code") or result.get("error", {}).get("code"),
                                "message": result.get("message") or result.get("error", {}).get("message"),
                            },
                        }

                    # Intercept interaction events
                    if block.name == "present_round" and result.get("status") == "awaiting_user_scores":
                        yield {"type": "premises", "data": result["premises"]}
                        should_pause = True

                    if block.name == "ask_user":
                        yield {"type": "ask_user", "data": block.input}
                        should_pause = True

                    if block.name == "generate_final_spec" and result.get("status") == "ok":
                        yield {"type": "final_spec", "data": block.input.get("spec_content", "")}
                        should_pause = True

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                messages.append({"role": "user", "content": tool_results})

                # ── Pause for user interaction ──
                if should_pause:
                    try:
                        session.message_history = messages
                        await self.db.commit()
                    except Exception as e:
                        logger.error(f"Failed to save message history: {e}")
                    yield {"type": "done", "data": {"error": False, "awaiting_input": True}}
                    return

            # ── Max iterations exceeded ──
            error = AgentLoopExceededError(
                self.MAX_ITERATIONS,
                ErrorContext(session_id=str(session.id)),
            )
            logger.error(f"Agent loop exceeded: {iteration} iterations",
                         extra={"session_id": str(session.id)})
            yield error.to_sse_event()
            yield {"type": "done", "data": {"error": True, "awaiting_input": False}}

        except asyncio.CancelledError:
            logger.info("Stream cancelled (client disconnect)",
                        extra={"session_id": str(session.id)})
            raise  # Re-raise for proper cleanup

        except Exception as e:
            logger.error(f"Unexpected error in agent runner: {e}",
                         extra={"session_id": str(session.id)}, exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "severity": ErrorSeverity.CRITICAL.value,
                    "recoverable": False,
                },
            }
            yield {"type": "done", "data": {"error": True, "awaiting_input": False}}

    async def _execute_tool_safe(self, handlers, session, tool_name, tool_input) -> dict:
        """
        Execute tool with error boundary — never raises, always returns dict.

        - Unknown tool → UNKNOWN_TOOL error
        - GhostPathError → converted to response dict
        - Any exception → logged + TOOL_EXECUTION_ERROR
        """
        try:
            handler = getattr(handlers, tool_name, None)
            if handler is None:
                logger.warning(f"Unknown tool called: {tool_name}")
                return {
                    "status": "error",
                    "error_code": "UNKNOWN_TOOL",
                    "message": f"Tool '{tool_name}' does not exist.",
                }
            return await handler(session, tool_input)

        except GhostPathError as e:
            logger.warning(f"Tool error: {e.message}",
                           extra={"tool_name": tool_name, "error_code": e.code})
            return e.to_response()

        except Exception as e:
            logger.error(f"Unexpected error in tool '{tool_name}': {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "TOOL_EXECUTION_ERROR",
                "message": f"Internal error executing {tool_name}",
            }

    def _build_messages(self, session, user_message: str) -> list:
        messages = list(session.message_history or [])
        messages.append({"role": "user", "content": user_message})
        return messages

    def _get_context_usage(self, session) -> dict:
        max_t = 1_000_000
        used = session.total_tokens_used
        n = max(len(session.rounds), 1)
        avg = used / n
        return {
            "tokens_used": used,
            "tokens_limit": max_t,
            "tokens_remaining": max_t - used,
            "usage_percentage": round((used / max_t) * 100, 2),
            "estimated_rounds_left": int((max_t - used) / avg) if avg > 0 else 999,
        }
```

---

## 4. Frontend — Interaction Components

### AskUser Component

```tsx
// src/components/AskUser.tsx

interface AskUserOption {
  label: string;
  description?: string;
}

interface AskUserData {
  question: string;
  options: AskUserOption[];
  allow_free_text?: boolean;
  context?: string;
}

interface Props {
  data: AskUserData;
  onRespond: (response: string) => void;
}

export function AskUser({ data, onRespond }: Props) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  const handleSubmit = () => {
    const response =
      selectedOption === "__free_text__" ? freeText : selectedOption;
    if (response) onRespond(response);
  };

  return (
    <div className="rounded-2xl border-2 border-blue-200 bg-blue-50/50 p-6 space-y-4">
      {/* Optional context (meta-analysis, etc) */}
      {data.context && (
        <div className="text-sm text-gray-600 bg-white rounded-lg p-4 border border-gray-100">
          {data.context}
        </div>
      )}

      {/* Question */}
      <h3 className="text-lg font-semibold text-gray-900">{data.question}</h3>

      {/* Options as buttons */}
      <div className="space-y-2">
        {data.options.map((opt) => (
          <button
            key={opt.label}
            onClick={() => setSelectedOption(opt.label)}
            className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all
              ${
                selectedOption === opt.label
                  ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
          >
            <span className="font-medium text-gray-900">{opt.label}</span>
            {opt.description && (
              <span className="block text-sm text-gray-500 mt-0.5">
                {opt.description}
              </span>
            )}
          </button>
        ))}

        {/* Free text field */}
        {data.allow_free_text !== false && (
          <div>
            <button
              onClick={() => setSelectedOption("__free_text__")}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all
                ${
                  selectedOption === "__free_text__"
                    ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
            >
              <span className="font-medium text-gray-500">
                Type my own response...
              </span>
            </button>

            {selectedOption === "__free_text__" && (
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                className="w-full mt-2 p-3 border-2 border-blue-300 rounded-xl text-sm
                           resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                placeholder="Your response..."
                autoFocus
              />
            )}
          </div>
        )}
      </div>

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={
          !selectedOption ||
          (selectedOption === "__free_text__" && !freeText.trim())
        }
        className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl
                   hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors"
      >
        Submit response
      </button>
    </div>
  );
}
```

### RoundView with "Problem Resolved" Button

```tsx
// src/components/RoundView.tsx

interface Props {
  premises: Premise[];
  roundNumber: number;
  onSubmitScores: (scores: PremiseScore[]) => void;
  onResolve: (winnerIndex: number) => void;
  isStreaming: boolean;
}

export function RoundView({
  premises,
  roundNumber,
  onSubmitScores,
  onResolve,
  isStreaming,
}: Props) {
  const [scores, setScores] = useState<Record<number, number>>({});
  const [comments, setComments] = useState<Record<number, string>>({});
  const [resolveMode, setResolveMode] = useState(false);

  const allScored = premises.every((_, i) => scores[i] !== undefined);

  const handleNextRound = () => {
    const result: PremiseScore[] = premises.map((p, i) => ({
      premise_id: p.id,
      premise_title: p.title,
      score: scores[i] ?? 5.0,
      comment: comments[i] || undefined,
    }));
    onSubmitScores(result);
  };

  const handleResolve = (index: number) => {
    // Send scores + mark the winner
    onResolve(index);
  };

  return (
    <div className="space-y-6">
      {/* Round header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Round {roundNumber}</h2>
        <span className="text-sm text-gray-500">
          Rate each premise from 0.0 to 10.0
        </span>
      </div>

      {/* Premise cards */}
      <div className="space-y-4">
        {premises.map((premise, index) => (
          <PremiseCard
            key={premise.id || index}
            premise={premise}
            isStreaming={isStreaming}
            onScore={(score) =>
              setScores((prev) => ({ ...prev, [index]: score }))
            }
            onComment={(comment) =>
              setComments((prev) => ({ ...prev, [index]: comment }))
            }
          />
        ))}
      </div>

      {/* Actions */}
      {!isStreaming && (
        <div className="flex gap-3">
          {/* Next Round */}
          <button
            onClick={handleNextRound}
            disabled={!allScored}
            className="flex-1 py-3 bg-gray-900 text-white font-medium rounded-xl
                       hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            Next Round →
          </button>

          {/* Problem Resolved */}
          {!resolveMode ? (
            <button
              onClick={() => setResolveMode(true)}
              className="px-6 py-3 bg-green-600 text-white font-medium rounded-xl
                         hover:bg-green-700 transition-colors"
            >
              ✓ Problem Resolved
            </button>
          ) : (
            <div className="flex-1 p-4 bg-green-50 border-2 border-green-200 rounded-xl space-y-3">
              <p className="text-sm font-medium text-green-800">
                Which premise solves your problem?
              </p>
              {premises.map((p, i) => (
                <button
                  key={i}
                  onClick={() => handleResolve(i)}
                  className="w-full text-left px-4 py-2 bg-white border border-green-300
                             rounded-lg hover:bg-green-50 transition-colors"
                >
                  <span className="font-medium">{p.title}</span>
                  {scores[i] !== undefined && (
                    <span className="ml-2 text-sm text-gray-500">
                      ({scores[i]?.toFixed(1)})
                    </span>
                  )}
                </button>
              ))}
              <button
                onClick={() => setResolveMode(false)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 5. Complete Message Flow Between Frontend and Backend

### Creation → First Round

```
Frontend                        Backend                           Agent
   │                              │                                 │
   │ POST /sessions               │                                 │
   │  {problem: "..."}            │                                 │
   │ ────────────────────────────>│                                 │
   │                              │ GET /sessions/{id}/stream       │
   │                              │ ───────────────────────────────>│
   │                              │                                 │
   │  SSE: tool_call              │<── decompose_problem ──────────│
   │  "Decomposing problem..."    │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │  SSE: tool_call              │<── extract_hidden_axioms ──────│
   │  "Extracting axioms..."      │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │  SSE: tool_call              │<── map_conventional_approaches │
   │  "Mapping the obvious..."    │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │                              │<── generate_premise ───────────│
   │  SSE: tool_result            │    returns: "1/3, 2 remaining" │
   │  "Premise 1 generated"       │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │                              │<── generate_premise ───────────│
   │  SSE: tool_result            │    returns: "2/3, 1 remaining" │
   │  "Premise 2 generated"       │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │                              │<── generate_premise ───────────│
   │  SSE: tool_result            │    returns: "3/3, buffer full" │
   │  "Premise 3 generated"       │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │                              │<── obviousness_test (×3) ──────│
   │                              │    returns: "all tested"       │
   │                              │                                 │
   │                              │<── present_round ──────────────│
   │  SSE: premises [3 cards]     │    returns: "awaiting user"    │
   │<─────────────────────────────│                                 │
   │  SSE: done                   │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │ [User sees 3 cards,          │                                 │
   │  slides sliders,             │                                 │
   │  writes comments]            │                                 │
```

### User Submits Scores → Next Round

```
Frontend                        Backend                           Agent
   │                              │                                 │
   │ POST /sessions/{id}/         │                                 │
   │  user-input                  │                                 │
   │  {type: "scores",            │                                 │
   │   scores: [...]}             │                                 │
   │ ────────────────────────────>│                                 │
   │                              │ ───────────────────────────────>│
   │                              │   "User scored:                 │
   │                              │    P1: 7.2, P2: 4.1, P3: 8.5   │
   │                              │    Winner: P3 (8.5)"            │
   │                              │                                 │
   │                              │<── store_premise (×3) ─────────│
   │                              │                                 │
   │                              │<── ask_user ───────────────────│
   │  SSE: ask_user               │   "I noticed you value         │
   │  {question: "...",           │    X and reject Y. Correct?"   │
   │   options: [...]}            │                                 │
   │<─────────────────────────────│                                 │
   │  SSE: done                   │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │ [User selects option         │                                 │
   │  or types response]          │                                 │
   │                              │                                 │
   │ POST user-input              │                                 │
   │  {type: "ask_user_response", │                                 │
   │   response: "Yes, correct"}  │                                 │
   │ ────────────────────────────>│                                 │
   │                              │ ───────────────────────────────>│
   │                              │                                 │
   │                              │<── get_negative_context ───────│
   │                              │<── challenge_axiom ────────────│
   │                              │<── import_foreign_domain ──────│
   │                              │<── generate_premise ───────────│
   │                              │    "1/3, 2 remaining"          │
   │                              │<── generate_premise ───────────│
   │                              │    "2/3, 1 remaining"          │
   │                              │<── generate_premise ───────────│
   │                              │    "3/3, buffer full"          │
   │                              │<── obviousness_test (×3) ──────│
   │                              │<── present_round ──────────────│
   │  SSE: premises [3 cards]     │                                 │
   │<─────────────────────────────│                                 │
   │  SSE: done                   │                                 │
   │<─────────────────────────────│                                 │
```

### User Triggers "Problem Resolved" → Final Spec

```
Frontend                        Backend                           Agent
   │                              │                                 │
   │ POST user-input              │                                 │
   │  {type: "resolved",          │                                 │
   │   winner_title: "...",       │                                 │
   │   winner_index: 2}           │                                 │
   │ ────────────────────────────>│                                 │
   │                              │ ───────────────────────────────>│
   │                              │   "User resolved!               │
   │                              │    Winner: 'Title X'"           │
   │                              │                                 │
   │  SSE: agent_text             │<── (agent text) ───────────────│
   │  "Excellent choice! The      │   "Excellent choice! This      │
   │   premise X... I'll generate │    premise has real potential.  │
   │   a detailed spec."          │    I'll develop a complete      │
   │<─────────────────────────────│    spec for you."               │
   │                              │                                 │
   │                              │<── store_premise (winner) ─────│
   │                              │<── query_premises (journey) ───│
   │                              │                                 │
   │                              │<── generate_final_spec ────────│
   │  SSE: final_spec             │    {spec_content: "# Spec..."}  │
   │  (markdown content)          │                                 │
   │<─────────────────────────────│                                 │
   │                              │                                 │
   │ [Frontend renders .md        │                                 │
   │  and offers download]        │                                 │
   │                              │                                 │
   │  SSE: done                   │                                 │
   │<─────────────────────────────│                                 │
```

---

## 6. Backend — API Routes, Schemas, and Delivery

### Schemas (with validation)

```python
# app/schemas/session.py

from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
from typing import Literal


class SessionCreate(BaseModel):
    """Session creation — validates problem length and whitespace."""
    problem: str = Field(min_length=10, max_length=10_000)

    @field_validator("problem")
    @classmethod
    def strip_problem(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("problem cannot be empty or whitespace")
        return v


class SessionResponse(BaseModel):
    id: UUID
    problem: str
    status: str


class PremiseScore(BaseModel):
    """Score for a single premise — enforces 0.0–10.0 range."""
    premise_title: str = Field(min_length=1, max_length=200)
    score: float = Field(ge=0.0, le=10.0)
    comment: str | None = Field(None, max_length=2000)

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 1)


class WinnerInfo(BaseModel):
    """Winning premise — index must be 0, 1, or 2."""
    title: str = Field(min_length=1, max_length=200)
    score: float | None = Field(None, ge=0.0, le=10.0)
    index: int = Field(ge=0, le=2)


class UserInput(BaseModel):
    """User input — uses Literal for type, cross-field validation."""
    type: Literal["scores", "ask_user_response", "resolved"]
    scores: list[PremiseScore] | None = None
    response: str | None = Field(None, max_length=5000)
    winner: WinnerInfo | None = None
    raw_text: str | None = Field(None, max_length=10_000)

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "scores":
            if not self.scores or len(self.scores) != 3:
                raise ValueError("scores input requires exactly 3 premise scores")
        elif self.type == "ask_user_response":
            if not self.response:
                raise ValueError("ask_user_response requires a response")
        elif self.type == "resolved":
            if not self.winner:
                raise ValueError("resolved input requires winner info")
        return self
```

### Health & Monitoring Routes

```python
# app/api/routes/health.py

import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.infrastructure.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic liveness probe. Returns 200 if the process is up."""
    return {"status": "healthy", "service": "ghostpath-api", "version": "4.0.0"}


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe — includes database connectivity.

    Returns:
        200: Service is ready
        503: Database unavailable
    """
    db_ok = await db_manager.health_check() if db_manager else False
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "database_unavailable"},
        )
    return {"status": "ready", "checks": {"database": "healthy"}}
```

### Session Routes (Complete API)

```python
# app/api/routes/sessions.py

import json
import os
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.models.session import Session as SessionModel
from app.models.premise import Premise
from app.schemas.session import SessionCreate, SessionResponse, UserInput
from app.services.agent_runner import AgentRunner
from app.services.session_state import SessionState
from app.core.errors import ResourceNotFoundError
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# In-memory session states (production → Redis/DB)
_session_states: dict[UUID, SessionState] = {}


# ─── CRUD ────────────────────────────────────────────────────────

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new GhostPath session.

    Returns 201 on success. Pydantic validates problem length (10-10000 chars).
    """
    try:
        session = SessionModel(problem=body.problem, status="created")
        db.add(session)
        await db.commit()
        await db.refresh(session)
        _session_states[session.id] = SessionState()
        return SessionResponse(id=session.id, problem=session.problem, status=session.status)
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create session")


@router.get("")
async def list_sessions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List sessions with pagination.

    Query params: ?limit=10&offset=0&status=created
    """
    query = select(SessionModel).order_by(SessionModel.created_at.desc())
    if status_filter:
        query = query.where(SessionModel.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": str(s.id),
                "problem": s.problem[:200] + ("..." if len(s.problem) > 200 else ""),
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
        "pagination": {"limit": limit, "offset": offset},
    }


@router.get("/{session_id}")
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get session details. Returns 404 if not found."""
    session = await _get_session_or_404(session_id, db)
    return {
        "id": str(session.id),
        "problem": session.problem,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "resolved_at": session.resolved_at.isoformat() if session.resolved_at else None,
        "total_tokens_used": session.total_tokens_used,
    }


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a session and associated data.

    Returns:
        204: Deleted
        404: Not found
        409: Cannot delete active session
    """
    session = await _get_session_or_404(session_id, db)
    if session.status == "active":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Cannot delete active session")
    await db.delete(session)
    await db.commit()
    _session_states.pop(session_id, None)


@router.post("/{session_id}/cancel")
async def cancel_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Cancel an active session.

    Returns:
        200: Cancelled
        400: Session not active
        404: Not found
    """
    session = await _get_session_or_404(session_id, db)
    if session.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot cancel session with status '{session.status}'")
    session.status = "cancelled"
    await db.commit()
    return {"message": "Session cancelled"}


# ─── SSE STREAMS ─────────────────────────────────────────────────

@router.get("/{session_id}/stream")
async def stream_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Initial SSE stream: triggers the agent to analyze the problem and generate round 1.

    Returns 404 if session not found, otherwise streams SSE events.
    """
    session = await _get_session_or_404(session_id, db)
    session_state = _session_states.setdefault(session_id, SessionState())
    settings = get_settings()
    client = ResilientAnthropicClient(
        api_key=settings.anthropic_api_key,
        max_retries=settings.anthropic_max_retries,
        timeout_seconds=settings.anthropic_timeout_seconds,
    )
    runner = AgentRunner(db, client)

    async def event_generator():
        message = (
            f"The user has submitted the following problem:\n\n"
            f"\"{session.problem}\"\n\n"
            f"Begin by calling decompose_problem, map_conventional_approaches, "
            f"and extract_hidden_axioms. Then generate 3 premises for the first round."
        )
        async for event in runner.run(session, message, session_state):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{session_id}/user-input")
async def send_user_input(
    session_id: UUID,
    body: UserInput,
    db: AsyncSession = Depends(get_db),
):
    """
    Send user input (scores, ask_user response, or resolved).

    Pydantic validates:
    - type must be "scores" | "ask_user_response" | "resolved"
    - scores requires exactly 3 items with score in 0.0–10.0
    - resolved requires winner info with index 0–2
    """
    session = await _get_session_or_404(session_id, db)
    session_state = _session_states.setdefault(session_id, SessionState())
    settings = get_settings()
    client = ResilientAnthropicClient(
        api_key=settings.anthropic_api_key,
        max_retries=settings.anthropic_max_retries,
        timeout_seconds=settings.anthropic_timeout_seconds,
    )
    runner = AgentRunner(db, client)

    # Format message based on input type
    match body.type:
        case "scores":
            message = _format_scores_message(body.scores)
            for s in body.scores:
                await _update_premise_score(db, session_id, s)

        case "ask_user_response":
            message = f"The user responded: \"{body.response}\""

        case "resolved":
            winner = body.winner
            message = (
                f"The user triggered 'Problem Resolved'. "
                f"The winning premise is: \"{winner.title}\" (score: {winner.score}). "
                f"Respond with a positive and enthusiastic message about the choice, "
                f"say you will generate a detailed spec from the winning premise, "
                f"then call generate_final_spec with the complete content in Markdown."
            )

    async def event_generator():
        spec_content = None

        async for event in runner.run(session, message, session_state):
            if event["type"] == "final_spec":
                spec_content = event["data"]
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # Save spec as .md file
        if spec_content:
            file_path = f"/tmp/ghostpath/specs/{session_id}.md"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(spec_content)
            yield f"data: {json.dumps({'type': 'spec_file_ready', 'data': {'download_url': f'/api/v1/sessions/{session_id}/spec'}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── SPEC DOWNLOAD ───────────────────────────────────────────────

@router.get("/{session_id}/spec")
async def download_spec(session_id: UUID):
    """Download the final spec as a .md file. Returns 404 if not generated yet."""
    file_path = f"/tmp/ghostpath/specs/{session_id}.md"
    if not os.path.exists(file_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Spec not found")
    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=f"ghostpath-spec-{session_id}.md",
    )


# ─── HELPERS ─────────────────────────────────────────────────────

async def _get_session_or_404(session_id: UUID, db: AsyncSession) -> SessionModel:
    """Get session or raise 404 with standardized error."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=ResourceNotFoundError("Session", str(session_id)).to_response(),
        )
    return session


def _format_scores_message(scores: list) -> str:
    lines = []
    for s in scores:
        line = f"- \"{s.premise_title}\": {s.score}/10"
        if s.comment:
            line += f" — \"{s.comment}\""
        lines.append(line)
    best = max(scores, key=lambda s: s.score)
    return (
        f"The user scored the premises:\n"
        + "\n".join(lines)
        + f"\n\nHighest scored: \"{best.premise_title}\" ({best.score}/10).\n"
        f"Use this feedback to evolve the next round. "
        f"Call get_negative_context first, then generate 3 new premises."
    )


async def _update_premise_score(db: AsyncSession, session_id: UUID, score_data) -> None:
    try:
        result = await db.execute(
            select(Premise)
            .where(Premise.session_id == session_id)
            .where(Premise.title == score_data.premise_title)
            .order_by(Premise.created_at.desc())
            .limit(1)
        )
        premise = result.scalar_one_or_none()
        if premise:
            premise.score = score_data.score
            premise.user_comment = score_data.comment
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to update premise score: {e}")
        await db.rollback()
```

### Complete API Map

| Method | Path | Status Codes | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/health/` | 200 | Liveness probe |
| `GET` | `/api/v1/health/ready` | 200, 503 | Readiness (includes DB) |
| `POST` | `/api/v1/sessions` | 201, 400, 500 | Create session |
| `GET` | `/api/v1/sessions` | 200 | List sessions (pagination) |
| `GET` | `/api/v1/sessions/{id}` | 200, 404 | Get session details |
| `DELETE` | `/api/v1/sessions/{id}` | 204, 404, 409 | Delete session |
| `POST` | `/api/v1/sessions/{id}/cancel` | 200, 400, 404 | Cancel active session |
| `GET` | `/api/v1/sessions/{id}/stream` | 200, 404 | SSE stream (round 1) |
| `POST` | `/api/v1/sessions/{id}/user-input` | 200, 400, 404 | User input (scores/resolved) |
| `GET` | `/api/v1/sessions/{id}/spec` | 200, 404 | Download spec .md |

---

## 6.1 FastAPI Application Setup & Global Error Handlers

```python
# app/main.py

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import GhostPathError, ErrorSeverity
from app.infrastructure.database import init_db
from app.infrastructure.observability import setup_logging
from app.config import get_settings
from app.api.routes import health, sessions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    init_db(settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow)
    logger.info("GhostPath API started")
    yield
    logger.info("GhostPath API shutting down")


app = FastAPI(title="GhostPath API", version="4.0.0", lifespan=lifespan)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(sessions.router)


# ─── GLOBAL ERROR HANDLERS ──────────────────────────────────────

@app.exception_handler(GhostPathError)
async def ghostpath_error_handler(request: Request, exc: GhostPathError):
    """Handle all GhostPath domain/infrastructure errors."""
    logger.error(f"GhostPathError: {exc.message}",
                 extra={"error_code": exc.code, "path": request.url.path})
    return JSONResponse(status_code=exc.http_status, content=exc.to_response())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with structured response."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "category": "validation",
                "severity": ErrorSeverity.ERROR.value,
                "details": [
                    {
                        "field": ".".join(str(loc) for loc in e["loc"]),
                        "message": e["msg"],
                        "type": e["type"],
                    }
                    for e in exc.errors()
                ],
            }
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all — never leaks internal details."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "category": "internal",
                "severity": ErrorSeverity.CRITICAL.value,
            }
        },
    )
```

---

## 7. Agent System Prompt (v4)

```python
AGENT_SYSTEM_PROMPT = """You are GhostPath, a semi-autonomous agent for evolutionary idea generation.

## Your Objective
Help the user solve complex problems by generating innovative premises that
evolve iteratively based on human feedback.

## How You Operate
You have tools at your disposal. You decide when to use each one, in what order,
and how many times. There is no fixed pipeline — you adapt your flow to the problem.

## Inviolable Rules (Enforced by the System)

The system BLOCKS your actions if you violate these rules. You will receive
an ERROR message and must correct before proceeding.

1. ANALYSIS GATES: generate_premise, mutate_premise, and cross_pollinate
   return ERROR if you have not called beforehand:
   - decompose_problem
   - map_conventional_approaches
   - extract_hidden_axioms
   Call all 3 before any generation.

2. ROUND BUFFER: each round accepts exactly 3 premises.
   - After each generate_premise/mutate_premise/cross_pollinate, the system
     informs how many are left ("2/3, 1 remaining", "3/3, buffer full").
   - Trying to generate with a full buffer returns ERROR.

3. OBVIOUSNESS TEST: present_round returns ERROR if any premise
   in the buffer has not passed obviousness_test.
   - Premises with score > 0.6 are AUTOMATICALLY removed from the buffer
     by the system. You must generate a replacement.

4. RADICAL VARIATION: whenever generating a "radical" type premise,
   MUST have called challenge_axiom beforehand.

5. ROUNDS 2+: MUST call get_negative_context before generating premises.

## Web Research (web_search — Anthropic built-in)

You have access to web_search, a built-in tool that searches the web in real time.
This is NOT a mandatory gate — use it strategically when external data adds value:

- BEFORE generating premises in fast-moving domains (tech, market, regulation):
  search for existing solutions to avoid reinventing the wheel.
- AFTER generating a premise that scores borderline on obviousness_test (0.4–0.6):
  search to validate that the premise doesn't already exist in the real world.
- WHEN using import_foreign_domain: search for real case studies from other domains
  instead of relying solely on your training data.
- WHEN the problem involves current data (market size, adoption rates, regulations):
  search for up-to-date stats and research to anchor premises in reality.

Be strategic with research — each search costs $0.01 and consumes context tokens.
Prefer targeted, specific queries over broad ones. Use max_uses to limit searches.

## User Interaction Rules

- Use ask_user when you need to align direction or capture preferences.
  Formulate questions with clear options + a free-form response option.
- After present_round, the flow PAUSES. The user will:
  (a) submit scores → you continue with the next round, or
  (b) trigger "Problem Resolved" → you generate the final spec.

## When the User Resolves

Upon receiving "Problem Resolved" with the winning premise:
1. Respond with a positive and enthusiastic message about the choice.
2. Say you will generate a detailed spec from the premise.
3. Call generate_final_spec with a COMPLETE Markdown document containing:
   - Executive Summary
   - The Problem (original context)
   - The Solution (premise expanded into actionable details)
   - How It Works (mechanisms, architecture, flows)
   - Implementation (concrete steps, timeline)
   - Risks and Mitigations
   - Success Metrics
   - Evolutionary Journey (how we got here)

## Personality
Direct, no fluff. Each premise should make the user think
"I wouldn't have thought of that". Never generate the obvious."""
```

---

## 8. Session State Diagram

```
                    ┌──────────────┐
                    │   CREATED    │
                    │ (problem     │
                    │  received)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  ANALYZING   │  ← agent calling gates
                    │ (gates in    │    (decompose, axioms, conventional)
                    │  progress)   │
                    └──────┬───────┘
                           │ all gates satisfied
                    ┌──────▼───────┐
                    │  GENERATING  │  ← agent generating premises
                    │ (buffer      │    (generate, mutate, cross_pollinate)
                    │  filling)    │    system reports: "1/3", "2/3", "3/3"
                    └──────┬───────┘
                           │ buffer = 3 + all tested
                    ┌──────▼───────┐
                    │  PRESENTING  │  ← present_round called
                    │ (awaiting    │    frontend displays 3 cards
                    │  user input) │
                    └──────┬───────┘
                           │
                ┌──────────┼──────────┐
                │                     │
         ┌──────▼───────┐     ┌──────▼───────┐
         │   SCORING    │     │   RESOLVED   │
         │ (user sent   │     │ (user clicked│
         │  scores)     │     │  "resolved") │
         └──────┬───────┘     └──────┬───────┘
                │                     │
                │ back to             │
                │ GENERATING          │
                │ (round N+1)   ┌─────▼────────┐
                │               │ GENERATING   │
                └───────────>   │ FINAL SPEC   │
                                │ (.md created)│
                                └──────────────┘
```

---

## Final Directory Structure

```
ghost-path/
├── docker-compose.yml
├── .env
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                          # FastAPI app + global error handlers
│   │   ├── config.py                        # pydantic-settings configuration
│   │   ├── core/
│   │   │   └── errors.py                    # Error hierarchy (GhostPathError + subtypes)
│   │   ├── infrastructure/
│   │   │   ├── anthropic_client.py          # Resilient Anthropic wrapper (retry/backoff)
│   │   │   ├── database.py                  # DB session manager (pool/rollback)
│   │   │   └── observability.py             # Structured JSON logging
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── session.py
│   │   │   ├── round.py
│   │   │   ├── premise.py
│   │   │   └── tool_call.py
│   │   ├── schemas/
│   │   │   ├── session.py                   # Validated Pydantic models (Field constraints)
│   │   │   └── agent.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py                # Health/readiness probes
│   │   │       └── sessions.py              # Session CRUD + SSE streams
│   │   └── services/
│   │       ├── agent_runner.py              # Resilient runner (MAX_ITERATIONS, error isolation)
│   │       ├── tool_handlers.py
│   │       ├── tool_definitions.py
│   │       ├── tools_registry.py
│   │       ├── session_state.py
│   │       └── system_prompt.py
│   └── tests/
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   └── client.ts
        ├── types/
        │   └── index.ts
        ├── hooks/
        │   ├── useAgentStream.ts
        │   ├── useSession.ts
        │   └── useContextUsage.ts
        ├── components/
        │   ├── ProblemInput.tsx
        │   ├── RoundView.tsx
        │   ├── PremiseCard.tsx
        │   ├── ScoreSlider.tsx
        │   ├── AskUser.tsx
        │   ├── ContextMeter.tsx
        │   ├── AgentActivityIndicator.tsx
        │   ├── EvoTree.tsx
        │   ├── ReportView.tsx
        │   └── SpecDownload.tsx
        └── pages/
            ├── HomePage.tsx
            ├── SessionPage.tsx
            └── ReportPage.tsx
```
