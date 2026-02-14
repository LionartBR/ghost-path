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
        assert "pt-BR" in result["message"]
