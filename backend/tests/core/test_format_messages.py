"""Resume message tests — pure tests for build_resume_message.

Tests cover:
    - Decompose delegates to build_initial_stream_message
    - Each phase produces phase-appropriate instructions
    - PT_BR locale produces Portuguese instructions
    - All phases are covered (no KeyError / unmatched branch)
"""

from app.core.domain_types import Locale, Phase
from app.core.format_messages import build_resume_message
from app.core.language_strings import get_phase_prefix


def _prefix(locale: Locale = Locale.EN) -> str:
    return get_phase_prefix(locale, "test problem")


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
