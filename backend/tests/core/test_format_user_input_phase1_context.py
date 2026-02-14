"""Phase 1 context injection tests — verify decompose_review injects ForgeState data.

Tests cover:
    - Fundamentals appear in Phase 2 start message
    - Selected reframings picked by user indices (not state.selected flag)
    - Assumption responses inject option text into Phase 2 context
    - Backward compat: forge_state=None produces no injection
    - PT_BR locale uses Portuguese labels
    - Fundamentals capped at 5 to prevent context explosion

Design Decisions:
    - Separate from test_format_user_input.py to keep both files under ExMA 400-line limit
    - Tests verify timing-bug prevention: at format time, state flags are NOT yet set
      (_format_user_input runs BEFORE _apply_user_input in session_agent_stream.py)
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix
from app.core.format_messages import format_user_input


PT_PROBLEM = "Como podemos reduzir bugs em producao de software?"
EN_PROBLEM = "How can we reduce bugs in production software?"


def test_decompose_review_injects_fundamentals_from_forge_state():
    """Phase 1 fundamentals appear in Phase 2 start message."""
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


def test_decompose_review_injects_assumption_responses_with_option_text():
    """Assumption responses inject selected option text into Phase 2 context.

    Same timing issue as reframings: selected_option is None at format time.
    Uses raw response dicts (same shape as AssumptionResponse).
    """
    state = ForgeState()
    state.assumptions = [
        {"text": "Users need real-time updates", "source": "interviews",
         "options": ["Valid", "Partially — depends on use case", "Challenge"], "selected_option": None},
        {"text": "Cost is the primary driver", "source": "market analysis",
         "options": ["Agree", "Only for SMBs", "Not the main factor"], "selected_option": None},
        {"text": "Mobile-first is required", "source": "analytics",
         "options": ["Yes", "Desktop-first for B2B", "Multi-platform"], "selected_option": None},
    ]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    responses = [
        {"assumption_index": 0, "selected_option": 1},
        {"assumption_index": 2, "selected_option": 2},
    ]
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state,
        assumption_responses=responses,
    )
    assert "real-time updates" in result
    assert "depends on use case" in result
    assert "Mobile-first" in result
    assert "Multi-platform" in result
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
    state = ForgeState()
    state.fundamentals = [f"element_{i}" for i in range(10)]
    prefix = get_phase_prefix(Locale.EN, EN_PROBLEM)
    result = format_user_input(
        "decompose_review", prefix, locale=Locale.EN,
        forge_state=state,
    )
    assert "element_4" in result
    assert "element_5" not in result
