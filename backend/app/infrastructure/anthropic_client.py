"""Resilient Anthropic Client — wraps AsyncAnthropic with retry, backoff, and error mapping.

Invariants:
    - Rate limits (429): exponential backoff with jitter, respects Retry-After header
    - Transient errors (5xx, connection): max 3 retries with exponential backoff
    - Client errors (4xx except 429): immediate failure, no retry
    - All failures mapped to AnthropicAPIError (core/errors.py)

Design Decisions:
    - Wrapper over raw client: isolates retry logic from agent_runner (ADR: single responsibility)
    - ±25% jitter on backoff: prevents thundering herd on shared rate limits
"""

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
    """Wraps Anthropic client with retry logic, timeouts, and error mapping."""

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
                logger.warning(
                    f"Rate limit hit, retry after {delay}ms "
                    f"(attempt {attempt + 1})",
                )
                await asyncio.sleep(delay / 1000)

            except (APIConnectionError, InternalServerError) as e:
                if attempt >= self.max_retries:
                    raise AnthropicAPIError(
                        f"Transient failure after {self.max_retries} retries: {e}",
                        "connection_error",
                        context=context,
                    )
                delay = self._backoff(attempt)
                logger.warning(
                    f"Transient error, retry after {delay}ms: {e}",
                )
                await asyncio.sleep(delay / 1000)

            except APITimeoutError:
                raise AnthropicAPIError(
                    "API timeout", "timeout", context=context,
                )

            except APIError as e:
                raise AnthropicAPIError(
                    str(e), "client_error", context=context,
                )

            except Exception as e:
                logger.error(
                    f"Unexpected Anthropic error: {e}", exc_info=True,
                )
                raise AnthropicAPIError(
                    str(e), "unknown", context=context,
                )

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
