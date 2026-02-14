"""Language Strings tests — pure data functions for locale-specific agent text.

Tests cover:
    - All 10 locales have entries for bookend, prefix, retry
    - Placeholders in retry messages format correctly
    - Phase prefix includes truncated problem excerpt
    - Functions are pure (no side effects, no IO)
"""

import pytest

from app.core.domain_types import Locale


# --- All locales covered ------------------------------------------------------


def test_bookend_closing_covers_all_locales():
    from app.core.language_strings import get_bookend_closing

    for locale in Locale:
        result = get_bookend_closing(locale)
        assert isinstance(result, str)
        assert len(result) > 0


def test_phase_prefix_covers_all_locales():
    from app.core.language_strings import get_phase_prefix

    problem = "How can we reduce bugs in production?"
    for locale in Locale:
        result = get_phase_prefix(locale, problem)
        assert isinstance(result, str)
        assert len(result) > 0


def test_retry_message_covers_all_locales():
    from app.core.language_strings import format_retry_message

    for locale in Locale:
        result = format_retry_message(locale, "en", 0.95)
        assert isinstance(result, str)
        assert len(result) > 0


# --- Retry message formatting -------------------------------------------------


def test_retry_message_includes_detected_locale():
    from app.core.language_strings import format_retry_message

    result = format_retry_message(Locale.PT_BR, "en", 0.87)
    assert "en" in result


def test_retry_message_includes_confidence_percentage():
    from app.core.language_strings import format_retry_message

    result = format_retry_message(Locale.PT_BR, "en", 0.87)
    assert "87%" in result


def test_retry_message_in_portuguese_for_pt_br():
    from app.core.language_strings import format_retry_message

    result = format_retry_message(Locale.PT_BR, "en", 0.87)
    assert "Portugu" in result  # "Português" (accent-safe match)


def test_retry_message_in_spanish_for_es():
    from app.core.language_strings import format_retry_message

    result = format_retry_message(Locale.ES, "en", 0.92)
    assert "espa" in result.lower()  # "español"


def test_retry_message_in_english_for_en():
    from app.core.language_strings import format_retry_message

    result = format_retry_message(Locale.EN, "pt-BR", 0.90)
    assert "English" in result


# --- Phase prefix with problem excerpt ----------------------------------------


def test_phase_prefix_includes_problem_excerpt():
    from app.core.language_strings import get_phase_prefix

    problem = "Como podemos reduzir bugs em produção?"
    result = get_phase_prefix(Locale.PT_BR, problem)
    assert "Como podemos reduzir" in result


def test_phase_prefix_truncates_long_problems():
    from app.core.language_strings import get_phase_prefix

    long_problem = "A" * 500
    result = get_phase_prefix(Locale.EN, long_problem)
    # Should not contain the full 500-char problem
    assert len(result) < 500
    assert "..." in result


def test_phase_prefix_handles_short_problems():
    from app.core.language_strings import get_phase_prefix

    result = get_phase_prefix(Locale.EN, "Short problem")
    assert "Short problem" in result


def test_phase_prefix_handles_empty_problem():
    from app.core.language_strings import get_phase_prefix

    result = get_phase_prefix(Locale.PT_BR, "")
    assert isinstance(result, str)
    assert len(result) > 0


def test_phase_prefix_pt_br_contains_portuguese_text():
    from app.core.language_strings import get_phase_prefix

    result = get_phase_prefix(Locale.PT_BR, "teste")
    # Should contain Portuguese instruction
    assert "Portugu" in result or "usu" in result.lower()


def test_phase_prefix_en_contains_english_text():
    from app.core.language_strings import get_phase_prefix

    result = get_phase_prefix(Locale.EN, "test")
    assert "user" in result.lower() or "English" in result
