"""Format message tests — pure tests for build_resume_message and format_user_input.

Tests cover:
    - Decompose delegates to build_initial_stream_message
    - Each phase produces phase-appropriate instructions
    - PT_BR locale produces Portuguese instructions
    - All phases are covered (no KeyError / unmatched branch)
    - claims_review with claim_responses (resonance) formats correctly
    - claims_review with added_claims (user custom) formats correctly
    - claims_review with feedback (legacy backward compat) formats correctly
    - claims_review PT_BR produces Portuguese labels
"""

from app.core.domain_types import Locale, Phase
from app.core.format_messages import build_resume_message, format_user_input
from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix


def _prefix(locale: Locale = Locale.EN) -> str:
    return get_phase_prefix(locale, "test problem")


def _make_state_with_claims() -> ForgeState:
    """ForgeState with 2 claims including resonance data."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    state.current_round_claims = [
        {
            "claim_text": "Distributed consensus as information routing",
            "resonance_prompt": "Does this shift how you see the problem?",
            "resonance_options": [
                "Doesn't resonate",
                "Interesting but incremental",
                "Opens a new direction",
                "Fundamentally changes my view",
            ],
        },
        {
            "claim_text": "Conflict resolution through structural alignment",
            "resonance_prompt": "Does this open new directions?",
            "resonance_options": [
                "No new directions",
                "Some new angles",
                "Significant shift",
            ],
        },
    ]
    return state


# --- Decompose delegates to initial message ----------------------------------

def test_resume_decompose_includes_begin_phase_1():
    msg = build_resume_message(_prefix(), Phase.DECOMPOSE, "test problem", Locale.EN)
    assert "Phase 1" in msg
    assert "DECOMPOSE" in msg


# --- Each phase produces correct instructions --------------------------------

def test_resume_explore_references_morphological_box():
    msg = build_resume_message(_prefix(), Phase.EXPLORE, "test problem", Locale.EN)
    assert "Phase 2" in msg or "EXPLORE" in msg
    assert "morphological" in msg.lower() or "web_search" in msg.lower()


def test_resume_synthesize_references_thesis():
    msg = build_resume_message(_prefix(), Phase.SYNTHESIZE, "test problem", Locale.EN)
    assert "Phase 3" in msg or "SYNTHESIZE" in msg


def test_resume_validate_references_falsification():
    msg = build_resume_message(_prefix(), Phase.VALIDATE, "test problem", Locale.EN)
    assert "Phase 4" in msg or "VALIDATE" in msg
    assert "falsif" in msg.lower()


def test_resume_build_references_knowledge_graph():
    msg = build_resume_message(_prefix(), Phase.BUILD, "test problem", Locale.EN)
    assert "Phase 5" in msg or "BUILD" in msg
    assert "graph" in msg.lower() or "knowledge" in msg.lower()


def test_resume_crystallize_references_document():
    msg = build_resume_message(_prefix(), Phase.CRYSTALLIZE, "test problem", Locale.EN)
    assert "Phase 6" in msg or "CRYSTALLIZE" in msg
    assert "document" in msg.lower()


# --- All phases covered (no unhandled branch) --------------------------------

def test_resume_message_covers_all_phases():
    for phase in Phase:
        msg = build_resume_message(_prefix(), phase, "test problem", Locale.EN)
        assert isinstance(msg, str)
        assert len(msg) > 20


# --- PT_BR locale produces Portuguese instructions ---------------------------

def test_resume_explore_pt_br():
    msg = build_resume_message(
        _prefix(Locale.PT_BR), Phase.EXPLORE, "test problem", Locale.PT_BR,
    )
    assert "Fase 2" in msg or "EXPLORE" in msg


def test_resume_synthesize_pt_br():
    msg = build_resume_message(
        _prefix(Locale.PT_BR), Phase.SYNTHESIZE, "test problem", Locale.PT_BR,
    )
    assert "Fase 3" in msg or "SYNTHESIZE" in msg


# --- claims_review with resonance (claim_responses) --------------------------

def test_claims_review_resonance_formats_selected_option_text():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        claim_responses=[
            {"claim_index": 0, "selected_option": 2},
            {"claim_index": 1, "selected_option": 0},
        ],
    )
    assert "Opens a new direction" in msg
    assert "No resonance" in msg


def test_claims_review_resonance_no_resonance_option_zero():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        claim_responses=[{"claim_index": 0, "selected_option": 0}],
    )
    assert "No resonance (user rejected)" in msg


def test_claims_review_resonance_includes_phase_instruction():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        claim_responses=[{"claim_index": 0, "selected_option": 1}],
    )
    assert "Phase 4" in msg or "VALIDATE" in msg


# --- claims_review with added_claims -----------------------------------------

def test_claims_review_added_claims_included():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        claim_responses=[{"claim_index": 0, "selected_option": 1}],
        added_claims=["My custom claim about AI safety"],
    )
    assert "My custom claim about AI safety" in msg
    assert "User-contributed claims:" in msg


def test_claims_review_added_claims_strips_whitespace():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        added_claims=["  valid claim  ", "  ", ""],
    )
    assert "valid claim" in msg
    # empty/whitespace-only claims should NOT appear
    assert msg.count("- ") == 1


# --- claims_review with legacy feedback (backward compat) --------------------

def test_claims_review_legacy_feedback_formats_evidence_valid():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(), locale=Locale.EN, forge_state=state,
        claim_feedback=[
            {"claim_index": 0, "evidence_valid": True, "counter_example": "X"},
        ],
    )
    assert "Evidence valid:" in msg
    assert "Counter-example: X" in msg


# --- claims_review PT_BR locale ---------------------------------------------

def test_claims_review_resonance_pt_br():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(Locale.PT_BR),
        locale=Locale.PT_BR, forge_state=state,
        claim_responses=[{"claim_index": 0, "selected_option": 2}],
    )
    assert "Opens a new direction" in msg
    assert "Sem ressonância" not in msg  # option 2 is not zero


def test_claims_review_no_resonance_pt_br():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(Locale.PT_BR),
        locale=Locale.PT_BR, forge_state=state,
        claim_responses=[{"claim_index": 0, "selected_option": 0}],
    )
    assert "Sem ressonância (usuário rejeitou)" in msg


def test_claims_review_added_claims_pt_br():
    state = _make_state_with_claims()
    msg = format_user_input(
        "claims_review", _prefix(Locale.PT_BR),
        locale=Locale.PT_BR, forge_state=state,
        added_claims=["Minha afirmação sobre IA"],
    )
    assert "Afirmações contribuídas pelo usuário:" in msg
    assert "Minha afirmação sobre IA" in msg


# --- verdicts: all-rejected bypass ------------------------------------------

def _make_state_for_verdicts() -> ForgeState:
    """ForgeState in VALIDATE phase with 3 claims."""
    state = ForgeState()
    state.current_phase = Phase.VALIDATE
    state.current_round_claims = [
        {"claim_text": f"Claim {i}", "claim_id": f"id-{i}"} for i in range(3)
    ]
    return state


def test_format_verdicts_all_rejected_emits_synthesize_instruction():
    """When all verdicts are reject, message should instruct SYNTHESIZE, not BUILD."""
    state = _make_state_for_verdicts()
    verdicts = [
        {"claim_index": 0, "verdict": "reject", "rejection_reason": "weak"},
        {"claim_index": 1, "verdict": "reject", "rejection_reason": "no evidence"},
        {"claim_index": 2, "verdict": "reject", "rejection_reason": "redundant"},
    ]
    msg = format_user_input(
        "verdicts", _prefix(), locale=Locale.EN, forge_state=state,
        verdicts=verdicts,
    )
    assert "Phase 3" in msg or "SYNTHESIZE" in msg
    assert "get_negative_knowledge" in msg
    assert "Phase 5" not in msg
    assert "BUILD" not in msg


def test_format_verdicts_mixed_emits_build_instruction():
    """When some verdicts are accept, message should instruct BUILD."""
    state = _make_state_for_verdicts()
    verdicts = [
        {"claim_index": 0, "verdict": "accept"},
        {"claim_index": 1, "verdict": "reject", "rejection_reason": "weak"},
        {"claim_index": 2, "verdict": "qualify", "qualification": "only if X"},
    ]
    msg = format_user_input(
        "verdicts", _prefix(), locale=Locale.EN, forge_state=state,
        verdicts=verdicts,
    )
    assert "Phase 5" in msg or "BUILD" in msg


def test_format_verdicts_all_rejected_at_max_rounds_emits_build_instruction():
    """At max rounds, even all-rejected should route to BUILD (user must resolve)."""
    state = _make_state_for_verdicts()
    state.current_round = 4  # MAX_ROUNDS_PER_SESSION - 1 = 4
    verdicts = [
        {"claim_index": 0, "verdict": "reject", "rejection_reason": "R1"},
        {"claim_index": 1, "verdict": "reject", "rejection_reason": "R2"},
        {"claim_index": 2, "verdict": "reject", "rejection_reason": "R3"},
    ]
    msg = format_user_input(
        "verdicts", _prefix(), locale=Locale.EN, forge_state=state,
        verdicts=verdicts,
    )
    assert "Phase 5" in msg or "BUILD" in msg


def test_format_verdicts_all_rejected_pt_br_emits_synthesize_instruction():
    """PT_BR: all-rejected should emit Portuguese synthesize instruction."""
    state = _make_state_for_verdicts()
    verdicts = [
        {"claim_index": 0, "verdict": "reject", "rejection_reason": "fraca"},
    ]
    msg = format_user_input(
        "verdicts", _prefix(Locale.PT_BR), locale=Locale.PT_BR,
        forge_state=state, verdicts=verdicts,
    )
    assert "Fase 3" in msg or "SYNTHESIZE" in msg
    assert "get_negative_knowledge" in msg
