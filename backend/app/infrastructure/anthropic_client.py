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
from collections.abc import Iterable
from contextlib import asynccontextmanager
from typing import Union

import anthropic
from anthropic import (
    APIError,
    APIConnectionError,
    APIStatusError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
)
from anthropic.types import TextBlockParam
from anthropic.types.beta import BetaTextBlockParam

from app.core.errors import AnthropicAPIError, ErrorContext

logger = logging.getLogger(__name__)

# Union of both SDK system param types — dispatched at runtime by self.betas
SystemParam = Union[str, Iterable[TextBlockParam], Iterable[BetaTextBlockParam]]

# ADR: OverloadedError (HTTP 529) exists in SDK but isn't re-exported in v0.79.
# Detect via status code on APIStatusError instead of relying on private import.
_OVERLOADED_STATUS = 529


def _is_overloaded(e: APIError) -> bool:
    """Check if error is Anthropic 529 Overloaded."""
    return isinstance(e, APIStatusError) and e.status_code == _OVERLOADED_STATUS


class ResilientAnthropicClient:
    """Wraps Anthropic client with retry logic, timeouts, and error mapping."""

    # ADR: 1M context window is beta — requires header "context-1m-2025-08-07".
    # Without this, Anthropic defaults to 200K. Tier 4 account required.
    # Premium pricing applies for prompts > 200K tokens (2x input, 1.5x output).
    CONTEXT_1M_BETA = "context-1m-2025-08-07"
    WEB_SEARCH_BETA = "web-search-2025-03-05"

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 60_000,
        timeout_seconds: int = 300,
        enable_1m_context: bool = True,
    ):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        # Always include web_search beta; conditionally add 1M context beta
        self.betas = [self.WEB_SEARCH_BETA]
        if enable_1m_context:
            self.betas.append(self.CONTEXT_1M_BETA)

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: SystemParam,
        tools: list,
        messages: list,
        context: ErrorContext | None = None,
    ):
        """Create message with automatic retry on transient failures.

        Supports prompt caching: system/tools/messages may include
        cache_control blocks per Anthropic's caching API.
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._call_api(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    tools=tools,
                    messages=messages,
                )
                self._log_success(response, attempt)
                return response

            except RateLimitError as e:
                await self._handle_rate_limit(e, attempt, context)

            except (APIConnectionError, InternalServerError) as e:
                await self._handle_transient_error(e, attempt, context)

            except APITimeoutError:
                raise AnthropicAPIError(
                    "API timeout", "timeout", context=context,
                )

            except APIError as e:
                if _is_overloaded(e):
                    await self._handle_transient_error(e, attempt, context)
                    continue
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

    @asynccontextmanager
    async def stream_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: SystemParam,
        tools: list,
        messages: list,
        context: ErrorContext | None = None,
    ):
        """Stream message with Anthropic error → AnthropicAPIError mapping.

        No retry — caller handles retries. Catches errors from both
        connection setup AND mid-stream (errors from caller's async for
        propagate through the yield in asynccontextmanager).
        CancelledError (BaseException) passes through uncaught.
        """
        try:
            cm = self._create_stream_manager(
                model=model, max_tokens=max_tokens,
                system=system, tools=tools, messages=messages,
            )
            async with cm as stream:
                yield stream
        except RateLimitError as e:
            raise AnthropicAPIError(
                "Rate limit exceeded (streaming)",
                "rate_limit",
                retry_after_ms=self._extract_retry_after(e),
                context=context,
            )
        except (APIConnectionError, InternalServerError) as e:
            raise AnthropicAPIError(
                f"Connection error during stream: {e}",
                "connection_error",
                context=context,
            )
        except APITimeoutError:
            raise AnthropicAPIError(
                "API timeout during stream", "timeout", context=context,
            )
        except APIError as e:
            if _is_overloaded(e):
                raise AnthropicAPIError(
                    "Anthropic API overloaded (529)",
                    "overloaded",
                    context=context,
                )
            raise AnthropicAPIError(
                str(e), "client_error", context=context,
            )

    async def create_message_raw(
        self,
        *,
        model: str,
        max_tokens: int,
        system: SystemParam,
        tools: list,
        messages: list,
        betas: list[str] | None = None,
        context: ErrorContext | None = None,
    ):
        """Create message with explicit betas (for Haiku research calls).

        Unlike create_message(), caller controls which betas are sent.
        Haiku needs web-search beta but NOT 1M-context beta.
        Reuses retry/backoff logic from create_message().
        """
        for attempt in range(self.max_retries + 1):
            try:
                response: object  # BetaMessage | Message — union avoids mypy narrowing
                if betas:
                    response = await self.client.beta.messages.create(
                        model=model, max_tokens=max_tokens,
                        system=system, tools=tools, messages=messages,
                        betas=betas,
                    )
                else:
                    response = await self.client.messages.create(
                        model=model, max_tokens=max_tokens,
                        system=system, tools=tools, messages=messages,
                    )
                self._log_success(response, attempt)
                return response
            except RateLimitError as e:
                await self._handle_rate_limit(e, attempt, context)
            except (APIConnectionError, InternalServerError) as e:
                await self._handle_transient_error(e, attempt, context)
            except APITimeoutError:
                raise AnthropicAPIError(
                    "API timeout", "timeout", context=context,
                )
            except APIError as e:
                if _is_overloaded(e):
                    await self._handle_transient_error(e, attempt, context)
                    continue
                raise AnthropicAPIError(
                    str(e), "client_error", context=context,
                )

    async def _call_api(self, **kwargs):
        """Route to beta or standard endpoint based on config."""
        if self.betas:
            return await self.client.beta.messages.create(
                **kwargs, betas=self.betas,
            )
        return await self.client.messages.create(**kwargs)

    def _log_success(self, response, attempt: int) -> None:
        """Log successful API call with cache metrics."""
        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_create = getattr(usage, "cache_creation_input_tokens", 0)
        logger.info(
            "Anthropic API success",
            extra={
                "attempt": attempt + 1,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
            },
        )

    async def _handle_rate_limit(
        self, e: RateLimitError, attempt: int, context: ErrorContext | None,
    ) -> None:
        """Handle rate limit error with retry or raise."""
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
            f"Rate limit hit, retry after {delay}ms (attempt {attempt + 1})",
        )
        await asyncio.sleep(delay / 1000)

    async def _handle_transient_error(
        self, e: Exception, attempt: int, context: ErrorContext | None,
    ) -> None:
        """Handle transient errors with retry or raise."""
        if attempt >= self.max_retries:
            raise AnthropicAPIError(
                f"Transient failure after {self.max_retries} retries: {e}",
                "connection_error",
                context=context,
            )
        delay = self._backoff(attempt)
        logger.warning(f"Transient error, retry after {delay}ms: {e}")
        await asyncio.sleep(delay / 1000)

    def _create_stream_manager(
        self,
        *,
        model: str,
        max_tokens: int,
        system: SystemParam,
        tools: list,
        messages: list,
    ):
        """Create stream manager (beta or standard endpoint)."""
        if self.betas:
            return self.client.beta.messages.stream(
                model=model, max_tokens=max_tokens,
                system=system, tools=tools, messages=messages,
                betas=self.betas,
            )
        return self.client.messages.stream(
            model=model, max_tokens=max_tokens,
            system=system, tools=tools, messages=messages,
        )

    def _backoff(self, attempt: int) -> int:
        """Exponential backoff with ±25% jitter."""
        delay = min(self.max_delay_ms, (2 ** attempt) * self.base_delay_ms)
        return int(delay * random.uniform(0.75, 1.25))  # nosec B311

    def _extract_retry_after(self, error: RateLimitError) -> int | None:
        """Extract Retry-After header (returns milliseconds)."""
        try:
            if hasattr(error, "response") and error.response:
                val = error.response.headers.get("retry-after")
                if val:
                    return int(val) * 1000
        except Exception:
            pass  # nosec B110
        return None
