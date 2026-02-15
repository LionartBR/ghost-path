"""Phase Digest Builders — tests for decompose, explore, and synthesize contexts.

Tests cover:
    - Phase 1: fundamentals, reframings by index, truncation, PT_BR labels
    - Phase 2: starred analogies by index, selected reframings, contradictions, morph box
    - Phase 3: claims with falsifiability, evidence count, truncation
    - Empty state returns empty string for all builders

Design Decisions:
    - Split: phases 1-3 here; phases 4-crystallize in test_phase_digest_advanced.py (ExMA)
    - ForgeState populated inline per test (no shared fixtures to avoid coupling)
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core.phase_digest import (
    build_phase1_context,
    build_phase2_context,
    build_phase3_context,
)


# ---------------------------------------------------------------------------
# Phase 1 (DECOMPOSE -> EXPLORE)
# ---------------------------------------------------------------------------

def test_phase1_includes_fundamentals():
    state = ForgeState()
    state.fundamentals = ["latency bottleneck", "data consistency"]
    result = build_phase1_context(state, Locale.EN, selected_reframings=[0])
    assert "latency bottleneck" in result
    assert "data consistency" in result
    assert "Phase 1 findings" in result


def test_phase1_limits_fundamentals_to_5():
    state = ForgeState()
    state.fundamentals = [f"element_{i}" for i in range(10)]
    result = build_phase1_context(state, Locale.EN)
    assert "element_4" in result
    assert "element_5" not in result


def test_phase1_empty_state_returns_empty():
    state = ForgeState()
    result = build_phase1_context(state, Locale.EN)
    assert result == ""


def test_phase1_uses_indices_not_state_flags():
    state = ForgeState()
    state.reframings = [
        {"text": "Reframing A", "selected": False},
        {"text": "Reframing B", "selected": False},
        {"text": "Reframing C", "selected": False},
    ]
    result = build_phase1_context(state, Locale.EN, selected_reframings=[0, 2])
    assert "Reframing A" in result
    assert "Reframing C" in result
    assert "Reframing B" not in result


def test_phase1_pt_br_labels():
    state = ForgeState()
    state.fundamentals = ["gargalo"]
    result = build_phase1_context(state, Locale.PT_BR)
    assert "Fundamentos:" in result
    assert "Fundamentals:" not in result


# ---------------------------------------------------------------------------
# Phase 2 (EXPLORE -> SYNTHESIZE)
# ---------------------------------------------------------------------------

def test_phase2_includes_starred_analogies_by_index():
    state = ForgeState()
    state.cross_domain_analogies = [
        {"domain": "Biology", "description": "Immune system analogy", "starred": False},
        {"domain": "Music", "description": "Harmonic resonance", "starred": False},
        {"domain": "Architecture", "description": "Load bearing", "starred": False},
    ]
    result = build_phase2_context(state, Locale.EN, starred_analogies=[0, 2])
    assert "Biology" in result
    assert "Immune system" in result
    assert "Architecture" in result
    assert "Music" not in result


def test_phase2_includes_selected_reframings_from_state():
    """Reads state.selected_reframings property (already set by prior review)."""
    state = ForgeState()
    state.reframings = [
        {"text": "Selected one", "selected": True},
        {"text": "Not selected", "selected": False},
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "Selected one" in result
    assert "Not selected" not in result


def test_phase2_includes_contradictions():
    state = ForgeState()
    state.contradictions = [
        {"property_a": "Speed", "property_b": "Accuracy", "description": "..."},
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "Speed" in result
    assert "Accuracy" in result
    assert "vs" in result


def test_phase2_includes_morphological_box_params():
    state = ForgeState()
    state.morphological_box = {
        "parameters": [
            {"name": "Material", "values": ["steel", "wood"]},
            {"name": "Shape", "values": ["round", "square"]},
        ]
    }
    result = build_phase2_context(state, Locale.EN)
    assert "Material" in result
    assert "Shape" in result


def test_phase2_empty_state_returns_empty():
    state = ForgeState()
    result = build_phase2_context(state, Locale.EN)
    assert result == ""


def test_phase2_pt_br():
    state = ForgeState()
    state.contradictions = [
        {"property_a": "Velocidade", "property_b": "Precisão"},
    ]
    result = build_phase2_context(state, Locale.PT_BR)
    assert "Contradições:" in result
    assert "Achados da Fase 2" in result


def test_phase2_truncates_reframings_to_3():
    state = ForgeState()
    state.reframings = [
        {"text": f"Reframing {i}", "selected": True} for i in range(10)
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "Reframing 0" in result
    assert "Reframing 2" in result
    assert "Reframing 3" not in result


def test_phase2_truncates_contradictions_to_3():
    state = ForgeState()
    state.contradictions = [
        {"property_a": f"A{i}", "property_b": f"B{i}"} for i in range(5)
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "A0" in result
    assert "A2" in result
    assert "A3" not in result


def test_phase2_truncates_morph_params_to_5():
    state = ForgeState()
    state.morphological_box = {
        "parameters": [{"name": f"Param{i}", "values": []} for i in range(8)]
    }
    result = build_phase2_context(state, Locale.EN)
    assert "Param4" in result
    assert "Param5" not in result


# ---------------------------------------------------------------------------
# Phase 2 — Analogy Resonance (new path)
# ---------------------------------------------------------------------------

def test_phase2_resonance_includes_option_text():
    """analogy_responses with selected_option > 0 injects resonance text."""
    state = ForgeState()
    state.cross_domain_analogies = [
        {
            "domain": "Ant Colony",
            "description": "Pheromone coordination",
            "resonance_options": [
                "No structural connection",
                "Surface similarity",
                "Deep structural match — pheromone trail ≈ routing",
            ],
        },
    ]
    responses = [{"analogy_index": 0, "selected_option": 2}]
    result = build_phase2_context(
        state, Locale.EN, analogy_responses=responses,
    )
    assert "Ant Colony" in result
    assert "Deep structural match" in result
    assert "User resonance:" in result


def test_phase2_resonance_excludes_option_zero():
    """analogy_responses with selected_option == 0 are skipped (no connection)."""
    state = ForgeState()
    state.cross_domain_analogies = [
        {
            "domain": "Music",
            "description": "Harmonic patterns",
            "resonance_options": ["No connection", "Partial", "Deep"],
        },
        {
            "domain": "Biology",
            "description": "Immune response",
            "resonance_options": ["No connection", "Partial", "Deep"],
        },
    ]
    responses = [
        {"analogy_index": 0, "selected_option": 0},  # skipped
        {"analogy_index": 1, "selected_option": 1},  # included
    ]
    result = build_phase2_context(
        state, Locale.EN, analogy_responses=responses,
    )
    assert "Music" not in result
    assert "Biology" in result
    assert "Partial" in result


def test_phase2_resonance_falls_back_to_starred():
    """When analogy_responses is None, falls back to starred_analogies path."""
    state = ForgeState()
    state.cross_domain_analogies = [
        {"domain": "Architecture", "description": "Load bearing", "starred": False},
        {"domain": "Ecology", "description": "Ecosystem balance", "starred": False},
    ]
    result = build_phase2_context(
        state, Locale.EN, starred_analogies=[1],
    )
    assert "Ecology" in result
    assert "Architecture" not in result
    assert "User resonance:" not in result


# ---------------------------------------------------------------------------
# Phase 3 (SYNTHESIZE -> VALIDATE)
# ---------------------------------------------------------------------------

def test_phase3_includes_claims_with_falsifiability():
    state = ForgeState()
    state.current_round_claims = [
        {
            "claim_text": "Novel approach to caching",
            "falsifiability_condition": "Fails if latency > 100ms",
            "evidence": [{"url": "http://example.com"}],
        },
    ]
    result = build_phase3_context(state, Locale.EN)
    assert "Novel approach" in result
    assert "latency > 100ms" in result
    assert "Claims to validate:" in result


def test_phase3_includes_evidence_count():
    state = ForgeState()
    state.current_round_claims = [
        {
            "claim_text": "Some claim",
            "falsifiability_condition": "Some condition",
            "evidence": [{"url": "a"}, {"url": "b"}, {"url": "c"}],
        },
    ]
    result = build_phase3_context(state, Locale.EN)
    assert "3 evidence items" in result


def test_phase3_truncates_long_claims():
    state = ForgeState()
    long_text = "A" * 200
    state.current_round_claims = [
        {"claim_text": long_text, "falsifiability_condition": "", "evidence": []},
    ]
    result = build_phase3_context(state, Locale.EN)
    assert "A" * 120 in result
    assert "A" * 121 not in result


def test_phase3_empty_claims_returns_empty():
    state = ForgeState()
    result = build_phase3_context(state, Locale.EN)
    assert result == ""


def test_phase3_pt_br():
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": "Alguma afirmação", "falsifiability_condition": "Condição", "evidence": []},
    ]
    result = build_phase3_context(state, Locale.PT_BR)
    assert "Afirmações a validar:" in result
    assert "Condição de falsificabilidade" in result


# ---------------------------------------------------------------------------
# Phase 1 — Reframing Resonance (new path)
# ---------------------------------------------------------------------------

def test_phase1_reframing_responses_included_in_context():
    """reframing_responses with selected_option > 0 injects resonance text."""
    state = ForgeState()
    state.reframings = [
        {
            "text": "View as information problem",
            "type": "domain_change",
            "resonance_options": [
                "Doesn't shift my perspective",
                "Interesting angle",
                "Completely changes how I see it",
            ],
        },
    ]
    responses = [{"reframing_index": 0, "selected_option": 2}]
    result = build_phase1_context(
        state, Locale.EN, reframing_responses=responses,
    )
    assert "View as information problem" in result
    assert "Completely changes" in result
    assert "User resonance:" in result


def test_phase1_reframing_option_0_excluded_from_context():
    """reframing_responses with selected_option == 0 are skipped."""
    state = ForgeState()
    state.reframings = [
        {
            "text": "Zoom out to macro level",
            "type": "scope_change",
            "resonance_options": ["No shift", "Partial shift", "Major shift"],
        },
        {
            "text": "Redefine who the stakeholder is",
            "type": "entity_question",
            "resonance_options": ["No shift", "Partial shift", "Major shift"],
        },
    ]
    responses = [
        {"reframing_index": 0, "selected_option": 0},  # skipped
        {"reframing_index": 1, "selected_option": 1},  # included
    ]
    result = build_phase1_context(
        state, Locale.EN, reframing_responses=responses,
    )
    assert "Zoom out" not in result
    assert "Redefine who" in result
    assert "Partial shift" in result


def test_phase1_selected_reframings_fallback_when_no_responses():
    """When reframing_responses is None, falls back to selected_reframings path."""
    state = ForgeState()
    state.reframings = [
        {"text": "Reframing A", "selected": False},
        {"text": "Reframing B", "selected": False},
    ]
    result = build_phase1_context(
        state, Locale.EN, selected_reframings=[1],
    )
    assert "Reframing B" in result
    assert "Reframing A" not in result
    assert "User resonance:" not in result


# ---------------------------------------------------------------------------
# Research Digest Injection
# ---------------------------------------------------------------------------

def test_phase2_includes_phase1_research_digest():
    """Phase 2 context should include research from decompose phase."""
    state = ForgeState()
    state.contradictions = [{"property_a": "X", "property_b": "Y"}]
    state.research_archive = [
        {"query": "TRIZ methods", "summary": "Found methods", "phase": "decompose", "purpose": "state_of_art"},
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "TRIZ methods" in result
    assert "Previous phase research:" in result


def test_phase3_includes_phase2_research_digest():
    """Phase 3 context should include research from explore phase."""
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": "Some claim", "falsifiability_condition": "Cond", "evidence": []},
    ]
    state.research_archive = [
        {"query": "biology analogy", "summary": "Immune system", "phase": "explore", "purpose": "cross_domain"},
    ]
    result = build_phase3_context(state, Locale.EN)
    assert "biology analogy" in result


def test_phase2_no_research_omits_digest():
    """Phase 2 with no decompose research should not include research section."""
    state = ForgeState()
    state.contradictions = [{"property_a": "X", "property_b": "Y"}]
    state.research_archive = []
    result = build_phase2_context(state, Locale.EN)
    assert "Previous phase research:" not in result


def test_phase2_research_digest_excludes_other_phases():
    """Phase 2 should only show decompose research, not explore research."""
    state = ForgeState()
    state.contradictions = [{"property_a": "X", "property_b": "Y"}]
    state.research_archive = [
        {"query": "explore query", "summary": "Explore data", "phase": "explore", "purpose": "cross_domain"},
    ]
    result = build_phase2_context(state, Locale.EN)
    assert "explore query" not in result
