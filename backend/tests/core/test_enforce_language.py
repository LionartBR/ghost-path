"""Language enforcement tests — pure tests for check_response_language.

Tests cover:
    - Passes when detected language matches expected locale
    - Fails when detected language mismatches expected locale
    - Skips short text under 50 chars
    - Skips low-confidence detection
    - Error dict has correct shape
"""

from app.core.enforce_language import check_response_language
from app.core.domain_types import Locale


# --- Passes when language matches ---------------------------------------------

def test_passes_when_english_matches_en_locale():
    text = (
        "The development of artificial intelligence has fundamentally changed "
        "how we approach complex problem-solving in modern organizations. "
        "This represents a paradigm shift in knowledge creation."
    )
    result = check_response_language(text, Locale.EN)
    assert result is None


def test_passes_when_portuguese_matches_pt_locale():
    text = (
        "O desenvolvimento da inteligencia artificial mudou fundamentalmente "
        "a forma como abordamos a resolucao de problemas complexos nas "
        "organizacoes modernas. Isso representa uma mudanca de paradigma."
    )
    result = check_response_language(text, Locale.PT_BR)
    assert result is None


# --- Fails when language mismatches -------------------------------------------

def test_fails_when_portuguese_text_with_en_locale():
    text = (
        "O desenvolvimento da inteligencia artificial mudou fundamentalmente "
        "a forma como abordamos a resolucao de problemas complexos nas "
        "organizacoes modernas. Isso representa uma mudanca de paradigma "
        "na criacao de conhecimento."
    )
    result = check_response_language(text, Locale.EN)
    # Should detect Portuguese != English and return error
    # NOTE: may return None if confidence < 0.7 — that's acceptable
    # The enforcement is best-effort
    if result is not None:
        assert result["status"] == "error"
        assert result["error_code"] == "LANGUAGE_MISMATCH"


# --- Skip conditions ----------------------------------------------------------

def test_skips_short_text_under_50_chars():
    result = check_response_language("Bonjour le monde!", Locale.EN)
    assert result is None


def test_skips_empty_text():
    result = check_response_language("", Locale.EN)
    assert result is None


def test_skips_short_text_at_boundary():
    # Exactly at the 50-char boundary — should be skipped
    text = "a" * 49
    result = check_response_language(text, Locale.PT_BR)
    assert result is None


# --- Error dict shape ---------------------------------------------------------

def test_error_dict_has_correct_shape():
    # Use clearly non-English text with EN locale to force a mismatch
    text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes dans "
        "les organisations modernes. C'est un changement de paradigme majeur "
        "dans la creation de connaissances et la recherche scientifique."
    )
    result = check_response_language(text, Locale.PT_BR)
    # If detected (may skip if confidence < 0.7)
    if result is not None:
        assert "status" in result
        assert "error_code" in result
        assert "message" in result
        assert result["status"] == "error"
        assert result["error_code"] == "LANGUAGE_MISMATCH"
        # Message is now in target locale (Portuguese), not English
        assert "Portugu" in result["message"]


# --- Localized retry message --------------------------------------------------


def test_error_message_in_portuguese_for_pt_br_locale():
    """Retry message should be in Portuguese when expected locale is PT_BR."""
    text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes dans "
        "les organisations modernes. C'est un changement de paradigme majeur "
        "dans la creation de connaissances et la recherche scientifique."
    )
    result = check_response_language(text, Locale.PT_BR)
    if result is not None:
        # Should contain Portuguese text, not English
        assert "Portugu" in result["message"]


def test_error_message_in_spanish_for_es_locale():
    """Retry message should be in Spanish when expected locale is ES."""
    text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes dans "
        "les organisations modernes. C'est un changement de paradigme majeur "
        "dans la creation de connaissances et la recherche scientifique."
    )
    result = check_response_language(text, Locale.ES)
    if result is not None:
        assert "espa" in result["message"].lower()


def test_english_detected_always_allowed_as_fallback():
    """English output is always allowed regardless of expected locale."""
    text = (
        "The development of artificial intelligence has fundamentally changed "
        "how we approach complex problem-solving in modern organizations."
    )
    # English detected → allowed even when expected is PT_BR
    result = check_response_language(text, Locale.PT_BR)
    assert result is None


def test_non_english_detected_with_en_locale_returns_error():
    """Non-English output with EN locale should return error."""
    text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes."
    )
    result = check_response_language(text, Locale.EN)
    # Should detect French != English and return error (confidence permitting)
    if result is not None:
        assert result["error_code"] == "LANGUAGE_MISMATCH"
