"""Phase instruction formatting tests — verify locale prefix in agent messages.

Tests cover:
    - Every UserInput type gets locale prefix prepended
    - Problem excerpt included in prefix
    - EN locale works without disruption
    - Build decision variants all get prefix

Design Decisions:
    - Tests import from core/format_messages.py (pure, no shell deps)
    - Uses get_phase_prefix directly (same as shell wrapper)
"""

from app.core.domain_types import Locale
from app.core.language_strings import get_phase_prefix
from app.core.format_messages import format_user_input, build_initial_stream_message


PT_PROBLEM = "Como podemos reduzir bugs em producao de software?"
EN_PROBLEM = "How can we reduce bugs in production software?"


# --- Decompose review ---------------------------------------------------------


def test_decompose_review_has_pt_br_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, selected_reframings=[0],
    )
    assert "Portugu" in result
    assert "reduzir" in result


def test_decompose_review_has_en_prefix():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, selected_reframings=[0],
    )
    assert "English" in result
    assert "reduce bugs" in result


# --- Explore review -----------------------------------------------------------


def test_explore_review_has_locale_prefix():
    prefix = get_phase_prefix(Locale.ES, "Problema de prueba")
    result = format_user_input(
        "explore_review", prefix, starred_analogies=[0, 1],
    )
    assert "espa" in result.lower()


# --- Claims review ------------------------------------------------------------


def test_claims_review_has_locale_prefix():
    prefix = get_phase_prefix(Locale.FR, "Probleme de test")
    feedback = [{"claim_index": 0, "evidence_valid": True}]
    result = format_user_input(
        "claims_review", prefix, claim_feedback=feedback,
    )
    assert "fran" in result.lower()


# --- Verdicts -----------------------------------------------------------------


def test_verdicts_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    vlist = [{"claim_index": 0, "verdict": "accept"}]
    result = format_user_input("verdicts", prefix, verdicts=vlist)
    assert "Portugu" in result


# --- Build decisions ----------------------------------------------------------


def test_build_decision_continue_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, decision="continue",
    )
    assert "Portugu" in result
    assert "get_negative_knowledge" in result


def test_build_decision_resolve_has_locale_prefix():
    prefix = get_phase_prefix(Locale.DE, "Testproblem")
    result = format_user_input(
        "build_decision", prefix, decision="resolve",
    )
    assert "Deutsch" in result
    assert "CRYSTALLIZE" in result


def test_build_decision_add_insight_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix,
        decision="add_insight",
        user_insight="Meu insight sobre o problema",
    )
    assert "Portugu" in result
    assert "Meu insight" in result


def test_build_decision_deep_dive_has_locale_prefix():
    prefix = get_phase_prefix(Locale.JA, "テスト問題")
    result = format_user_input(
        "build_decision", prefix,
        decision="deep_dive",
        deep_dive_claim_id="abc-123",
    )
    assert "日本語" in result
    assert "abc-123" in result


# --- Problem excerpt in prefix ------------------------------------------------


def test_prefix_includes_problem_excerpt():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, selected_reframings=[0],
    )
    assert "reduzir bugs" in result


def test_prefix_truncates_long_problem():
    long_problem = "A" * 500
    prefix = get_phase_prefix(Locale.EN, long_problem)
    result = format_user_input(
        "decompose_review", prefix, selected_reframings=[0],
    )
    assert "..." in result
    assert "A" * 500 not in result


# --- Initial stream message ---------------------------------------------------


def test_initial_stream_message_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = build_initial_stream_message(prefix, PT_PROBLEM)
    assert "Portugu" in result
    assert PT_PROBLEM in result
    assert "DECOMPOSE" in result


def test_initial_stream_message_en():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = build_initial_stream_message(prefix, EN_PROBLEM)
    assert "English" in result
    assert EN_PROBLEM in result
