"""Structured Logging — JSON formatter and setup for production observability.

Invariants:
    - All logs include timestamp, level, logger name, and message
    - Extra fields (session_id, tool_name, error_code) surfaced when present
    - JSON format in production, human-readable in development

Design Decisions:
    - JSONFormatter over third-party libs: zero dependencies, full control (ADR: hackathon simplicity)
    - setup_logging called once on startup via lifespan
"""

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
        for key in (
            "session_id", "tool_name", "error_code", "attempt",
            "input_tokens", "output_tokens", "round_number",
        ):
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
            "%(asctime)s %(levelname)s %(name)s — %(message)s",
        ))
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))
