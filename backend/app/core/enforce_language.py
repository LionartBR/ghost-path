"""Language Enforcement — validates agent text output matches user's locale.

Invariants:
    - Only validates agent output, never user input
    - Skips enforcement on short text (<50 chars) or low confidence (<0.7)
    - Returns standard error dict or None (matches enforce_phases/enforce_claims pattern)

Design Decisions:
    - Confidence threshold 0.7: avoids false positives on code snippets, URLs, proper nouns
    - Reuses detect_locale for consistency (same library, same seed)
"""

from app.core.domain_types import Locale
from app.core.detect_language import detect_locale
from app.core.language_strings import format_retry_message


def check_response_language(text: str, expected_locale: Locale) -> dict | None:
    """Rule #16: Agent text output must match user's locale.

    Returns error dict if language mismatch detected, None if OK.
    Skips check for short text or low-confidence detection.
    Retry message is in the TARGET locale (not English) to reinforce
    the desired output language.
    """
    if not text or len(text.strip()) < 50:
        return None

    detected_locale, confidence = detect_locale(text)

    if confidence < 0.7:
        return None

    if detected_locale == expected_locale:
        return None

    # English is always allowed as fallback (tool names, citations, code)
    if detected_locale == Locale.EN:
        return None

    return {
        "status": "error",
        "error_code": "LANGUAGE_MISMATCH",
        "message": format_retry_message(
            expected_locale, detected_locale.value, confidence,
        ),
    }
