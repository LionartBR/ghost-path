"""Document Gate Enforcement tests — pure tests for check_document_gate.

Tests cover:
    - Gate passes when document_updated_this_phase is True
    - Gate fails (returns nudge) when document_updated_this_phase is False
    - CRYSTALLIZE phase is exempt (always passes)
    - Nudge message contains section hint matching the current phase
    - All gated phases (DECOMPOSE through BUILD) fail when not updated
"""

from app.core.domain_types import Phase
from app.core.enforce_document import check_document_gate
from app.core.forge_state import ForgeState


def test_gate_passes_when_document_updated():
    """Gate returns None when agent has updated the document this phase."""
    state = ForgeState()
    state.document_updated_this_phase = True
    assert check_document_gate(state) is None


def test_gate_fails_when_document_not_updated():
    """Gate returns nudge message when agent hasn't updated the document."""
    state = ForgeState()
    state.document_updated_this_phase = False
    result = check_document_gate(state)
    assert result is not None
    assert "update_working_document" in result


def test_gate_skipped_for_crystallize():
    """CRYSTALLIZE phase always passes — document is finalized there."""
    state = ForgeState()
    state.current_phase = Phase.CRYSTALLIZE
    state.document_updated_this_phase = False
    assert check_document_gate(state) is None


def test_gate_nudge_contains_section_hint():
    """Nudge message includes the suggested section for the current phase."""
    state = ForgeState()
    state.current_phase = Phase.DECOMPOSE
    result = check_document_gate(state)
    assert result is not None
    assert "problem_context" in result

    state.current_phase = Phase.EXPLORE
    result = check_document_gate(state)
    assert "cross_domain_patterns" in result

    state.current_phase = Phase.SYNTHESIZE
    result = check_document_gate(state)
    assert "core_insight" in result

    state.current_phase = Phase.VALIDATE
    result = check_document_gate(state)
    assert "evidence_base" in result

    state.current_phase = Phase.BUILD
    result = check_document_gate(state)
    assert "boundaries" in result


def test_gate_fails_for_all_gated_phases():
    """All phases DECOMPOSE through BUILD fail when document not updated."""
    gated = [Phase.DECOMPOSE, Phase.EXPLORE, Phase.SYNTHESIZE,
             Phase.VALIDATE, Phase.BUILD]
    for phase in gated:
        state = ForgeState()
        state.current_phase = phase
        state.document_updated_this_phase = False
        result = check_document_gate(state)
        assert result is not None, f"Expected gate failure for {phase}"
