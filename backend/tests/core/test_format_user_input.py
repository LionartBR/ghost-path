"""Phase instruction formatting tests — verify locale prefix AND body translation.

Tests cover:
    - Every UserInput type gets locale prefix prepended
    - Problem excerpt included in prefix
    - EN locale works without disruption
    - Build decision variants all get prefix
    - PT_BR locale gets fully translated message bodies (not just prefix)
    - EN locale still produces English bodies

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
        "decompose_review", prefix, locale=Locale.PT_BR,
        selected_reframings=[0],
    )
    assert "Portugu" in result
    assert "reduzir" in result


def test_decompose_review_has_en_prefix():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        selected_reframings=[0],
    )
    assert "English" in result
    assert "reduce bugs" in result


def test_decompose_review_pt_br_body_is_portuguese():
    """PT_BR body must NOT contain English instructions."""
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.PT_BR,
        selected_reframings=[0],
    )
    assert "Proceed to Phase" not in result
    assert "Prossiga para a Fase" in result
    assert "revisou a decomposição" in result


def test_decompose_review_en_body_is_english():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        selected_reframings=[0],
    )
    assert "Proceed to Phase 2" in result
    assert "reviewed the decomposition" in result


# --- Explore review -----------------------------------------------------------


def test_explore_review_has_locale_prefix():
    prefix = get_phase_prefix(Locale.ES, "Problema de prueba")
    result = format_user_input(
        "explore_review", prefix, locale=Locale.ES,
        starred_analogies=[0, 1],
    )
    assert "espa" in result.lower()


def test_explore_review_pt_br_body_is_portuguese():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "explore_review", prefix, locale=Locale.PT_BR,
        starred_analogies=[0],
    )
    assert "Proceed to Phase" not in result
    assert "Prossiga para a Fase 3" in result
    assert "revisou a exploração" in result


# --- Claims review ------------------------------------------------------------


def test_claims_review_has_locale_prefix():
    prefix = get_phase_prefix(Locale.FR, "Probleme de test")
    feedback = [{"claim_index": 0, "evidence_valid": True}]
    result = format_user_input(
        "claims_review", prefix, locale=Locale.FR,
        claim_feedback=feedback,
    )
    assert "fran" in result.lower()


def test_claims_review_pt_br_body_is_portuguese():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    feedback = [{"claim_index": 0, "evidence_valid": True}]
    result = format_user_input(
        "claims_review", prefix, locale=Locale.PT_BR,
        claim_feedback=feedback,
    )
    assert "Proceed to Phase" not in result
    assert "Prossiga para a Fase 4" in result
    assert "revisou as afirmações" in result


# --- Verdicts -----------------------------------------------------------------


def test_verdicts_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    vlist = [{"claim_index": 0, "verdict": "accept"}]
    result = format_user_input(
        "verdicts", prefix, locale=Locale.PT_BR, verdicts=vlist,
    )
    assert "Portugu" in result


def test_verdicts_pt_br_body_is_portuguese():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    vlist = [{"claim_index": 0, "verdict": "accept"}]
    result = format_user_input(
        "verdicts", prefix, locale=Locale.PT_BR, verdicts=vlist,
    )
    assert "Proceed to Phase" not in result
    assert "Prossiga para a Fase 5" in result
    assert "emitiu veredictos" in result


# --- Build decisions ----------------------------------------------------------


def test_build_decision_continue_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="continue",
    )
    assert "Portugu" in result
    assert "get_negative_knowledge" in result


def test_build_decision_continue_pt_br_body():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="continue",
    )
    assert "The user wants" not in result
    assert "quer continuar" in result


def test_build_decision_resolve_has_locale_prefix():
    prefix = get_phase_prefix(Locale.DE, "Testproblem")
    result = format_user_input(
        "build_decision", prefix, locale=Locale.DE,
        decision="resolve",
    )
    assert "Deutsch" in result
    assert "CRYSTALLIZE" in result


def test_build_decision_resolve_pt_br_body():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="resolve",
    )
    assert "The user is satisfied" not in result
    assert "satisfeito com o grafo" in result


def test_build_decision_add_insight_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="add_insight",
        user_insight="Meu insight sobre o problema",
    )
    assert "Portugu" in result
    assert "Meu insight" in result


def test_build_decision_add_insight_pt_br_body():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="add_insight",
        user_insight="Meu insight",
    )
    assert "The user wants to add" not in result
    assert "quer adicionar" in result


def test_build_decision_deep_dive_has_locale_prefix():
    prefix = get_phase_prefix(Locale.JA, "テスト問題")
    result = format_user_input(
        "build_decision", prefix, locale=Locale.JA,
        decision="deep_dive",
        deep_dive_claim_id="abc-123",
    )
    assert "日本語" in result
    assert "abc-123" in result


def test_build_decision_deep_dive_pt_br_body():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "build_decision", prefix, locale=Locale.PT_BR,
        decision="deep_dive",
        deep_dive_claim_id="abc-123",
    )
    assert "The user wants to deep-dive" not in result
    assert "aprofundar" in result


# --- Problem excerpt in prefix ------------------------------------------------


def test_prefix_includes_problem_excerpt():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.PT_BR,
        selected_reframings=[0],
    )
    assert "reduzir bugs" in result


def test_prefix_truncates_long_problem():
    long_problem = "A" * 500
    prefix = get_phase_prefix(Locale.EN, long_problem)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        selected_reframings=[0],
    )
    assert "..." in result
    assert "A" * 500 not in result


# --- Initial stream message ---------------------------------------------------


def test_initial_stream_message_has_locale_prefix():
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = build_initial_stream_message(prefix, PT_PROBLEM, locale=Locale.PT_BR)
    assert "Portugu" in result
    assert PT_PROBLEM in result
    assert "DECOMPOSE" in result


def test_initial_stream_message_en():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = build_initial_stream_message(prefix, EN_PROBLEM, locale=Locale.EN)
    assert "English" in result
    assert EN_PROBLEM in result


def test_initial_stream_message_pt_br_body_is_portuguese():
    """PT_BR initial message must NOT contain English instructions."""
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = build_initial_stream_message(prefix, PT_PROBLEM, locale=Locale.PT_BR)
    assert "The user has submitted" not in result
    assert "submeteu o seguinte problema" in result
    assert "Begin Phase 1" not in result
    assert "Inicie a Fase 1" in result


def test_initial_stream_message_en_body_is_english():
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = build_initial_stream_message(prefix, EN_PROBLEM, locale=Locale.EN)
    assert "The user has submitted" in result
    assert "Begin Phase 1" in result


# --- Backward compat: locale defaults to EN -----------------------------------


def test_format_user_input_defaults_to_english():
    """Callers not passing locale= still get English (backward compat)."""
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix,
        selected_reframings=[0],
    )
    assert "Proceed to Phase 2" in result


def test_initial_stream_message_defaults_to_english():
    """Callers not passing locale= still get English (backward compat)."""
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = build_initial_stream_message(prefix, EN_PROBLEM)
    assert "The user has submitted" in result


# --- Phase 1 context injection in decompose_review ----------------------------


def test_decompose_review_injects_fundamentals_from_forge_state():
    """Phase 1 fundamentals appear in Phase 2 start message."""
    from app.core.forge_state import ForgeState
    state = ForgeState()
    state.fundamentals = ["latency bottleneck", "data consistency", "user trust"]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state, selected_reframings=[0],
    )
    assert "latency bottleneck" in result
    assert "data consistency" in result
    assert "Phase 1 findings" in result


def test_decompose_review_injects_selected_reframings_by_index():
    """Selected reframings picked by user indices, not state.selected flag.

    Bug prevention: at format time, state.reframings[i].selected is still
    False (set by _apply_user_input AFTER formatting). Must use indices.
    """
    from app.core.forge_state import ForgeState
    state = ForgeState()
    state.reframings = [
        {"text": "What if we invert the constraint?", "type": "scope_change",
         "reasoning": "...", "selected": False},
        {"text": "How might distributed systems help?", "type": "domain_change",
         "reasoning": "...", "selected": False},
        {"text": "Is the real problem trust?", "type": "entity_question",
         "reasoning": "...", "selected": False},
    ]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state,
        selected_reframings=[0, 2],
    )
    assert "invert the constraint" in result
    assert "real problem trust" in result
    assert "distributed systems" not in result


def test_decompose_review_injects_confirmed_assumptions_by_index():
    """Confirmed assumptions picked by user indices, not state.confirmed flag.

    Same timing issue as reframings: confirmed is None at format time.
    """
    from app.core.forge_state import ForgeState
    state = ForgeState()
    state.assumptions = [
        {"text": "Users need real-time updates", "source": "interviews", "confirmed": None},
        {"text": "Cost is the primary driver", "source": "market analysis", "confirmed": None},
        {"text": "Mobile-first is required", "source": "analytics", "confirmed": None},
    ]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state,
        confirmed_assumptions=[0, 2],
    )
    assert "real-time updates" in result
    assert "Mobile-first" in result
    assert "primary driver" not in result


def test_decompose_review_no_context_without_forge_state():
    """forge_state=None produces no Phase 1 context injection (backward compat)."""
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=None,
        selected_reframings=[0],
    )
    assert "Phase 1 findings" not in result
    assert "Fundamentals:" not in result
    assert "Proceed to Phase 2" in result


def test_decompose_review_phase1_context_pt_br():
    """PT_BR locale produces Portuguese labels in Phase 1 context."""
    from app.core.forge_state import ForgeState
    state = ForgeState()
    state.fundamentals = ["gargalo de latência", "consistência de dados"]
    state.reframings = [
        {"text": "E se invertêssemos a restrição?", "type": "scope_change",
         "reasoning": "...", "selected": False},
    ]
    prefix = get_phase_prefix(Locale.PT_BR, PT_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.PT_BR,
        forge_state=state,
        selected_reframings=[0],
    )
    assert "Fundamentos:" in result
    assert "gargalo de latência" in result
    assert "Reformulações selecionadas:" in result
    assert "invertêssemos" in result
    assert "Fundamentals:" not in result


def test_decompose_review_limits_fundamentals_to_5():
    """Prevent context explosion by capping fundamentals at 5."""
    from app.core.forge_state import ForgeState
    state = ForgeState()
    state.fundamentals = [f"element_{i}" for i in range(10)]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state,
    )
    assert "element_4" in result
    assert "element_5" not in result
