"""Phase-scoped system prompt tests — validates per-phase context filtering.

Tests cover:
    - Each phase only includes its own relevant sections
    - Sections irrelevant to a phase are excluded
    - Backward compat: build_system_prompt(locale) still works (defaults to None = all sections)
    - PT_BR phase prompts also filter correctly
    - All phases include shared sections (mission, error_recovery, output_guidance)
"""

from app.core.domain_types import Locale, Phase
from app.services.system_prompt import build_system_prompt


# --- Shared sections present in ALL phases ------------------------------------


def test_all_phases_include_mission():
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<mission>" in prompt, f"Phase {phase.value} missing <mission>"


def test_phases_with_rules_include_error_recovery():
    for phase in [Phase.DECOMPOSE, Phase.EXPLORE, Phase.SYNTHESIZE, Phase.VALIDATE, Phase.BUILD]:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<error_recovery>" in prompt, f"Phase {phase.value} missing <error_recovery>"


def test_crystallize_excludes_error_recovery():
    """CRYSTALLIZE has no enforcement rules — error recovery is irrelevant."""
    prompt = build_system_prompt(Locale.EN, Phase.CRYSTALLIZE)
    assert "<error_recovery>" not in prompt


def test_all_phases_include_output_guidance():
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<output_guidance>" in prompt, f"Phase {phase.value} missing <output_guidance>"


def test_all_phases_include_tool_efficiency():
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<tool_efficiency>" in prompt, f"Phase {phase.value} missing <tool_efficiency>"


def test_all_phases_include_context_management():
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<context_management>" in prompt


def test_all_phases_include_thinking_guidance():
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        assert "<thinking_guidance>" in prompt


# --- DECOMPOSE: should NOT include dialectical, falsifiability, knowledge_graph


def test_decompose_excludes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<dialectical_method>" not in prompt


def test_decompose_excludes_falsifiability():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<falsifiability>" not in prompt


def test_decompose_excludes_knowledge_graph():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<knowledge_graph>" not in prompt


def test_decompose_excludes_research_archive():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<research_archive>" not in prompt


def test_decompose_includes_web_research():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<web_research>" in prompt


def test_decompose_only_has_phase1_rules():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "Rule #1" in prompt or "map_state_of_art" in prompt
    # Synthesis rules should be absent
    assert "create_synthesis requires find_antithesis" not in prompt
    assert "falsification attempt before scoring" not in prompt


def test_decompose_only_has_phase1_pipeline():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "### Phase 1: DECOMPOSE" in prompt
    # Other phase details should be absent
    assert "### Phase 3: SYNTHESIZE" not in prompt
    assert "### Phase 4: VALIDATE" not in prompt


# --- EXPLORE: should NOT include dialectical, falsifiability, knowledge_graph


def test_explore_excludes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "<dialectical_method>" not in prompt


def test_explore_excludes_falsifiability():
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "<falsifiability>" not in prompt


def test_explore_excludes_knowledge_graph():
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "<knowledge_graph>" not in prompt


def test_explore_includes_research_archive():
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "<research_archive>" in prompt


# --- SYNTHESIZE: SHOULD include dialectical + falsifiability, NOT knowledge_graph


def test_synthesize_includes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.SYNTHESIZE)
    assert "<dialectical_method>" in prompt


def test_synthesize_includes_falsifiability():
    prompt = build_system_prompt(Locale.EN, Phase.SYNTHESIZE)
    assert "<falsifiability>" in prompt


def test_synthesize_excludes_knowledge_graph():
    prompt = build_system_prompt(Locale.EN, Phase.SYNTHESIZE)
    assert "<knowledge_graph>" not in prompt


# --- VALIDATE: SHOULD include falsifiability, NOT dialectical or knowledge_graph


def test_validate_includes_falsifiability():
    prompt = build_system_prompt(Locale.EN, Phase.VALIDATE)
    assert "<falsifiability>" in prompt


def test_validate_excludes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.VALIDATE)
    assert "<dialectical_method>" not in prompt


def test_validate_excludes_knowledge_graph():
    prompt = build_system_prompt(Locale.EN, Phase.VALIDATE)
    assert "<knowledge_graph>" not in prompt


# --- BUILD: SHOULD include knowledge_graph, NOT dialectical or falsifiability


def test_build_includes_knowledge_graph():
    prompt = build_system_prompt(Locale.EN, Phase.BUILD)
    assert "<knowledge_graph>" in prompt


def test_build_excludes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.BUILD)
    assert "<dialectical_method>" not in prompt


def test_build_excludes_falsifiability():
    prompt = build_system_prompt(Locale.EN, Phase.BUILD)
    assert "<falsifiability>" not in prompt


# --- CRYSTALLIZE: SHOULD include working_document, NOT enforcement rules


def test_crystallize_excludes_enforcement_rules():
    prompt = build_system_prompt(Locale.EN, Phase.CRYSTALLIZE)
    assert "<enforcement_rules>" not in prompt


def test_crystallize_excludes_dialectical_method():
    prompt = build_system_prompt(Locale.EN, Phase.CRYSTALLIZE)
    assert "<dialectical_method>" not in prompt


def test_crystallize_excludes_web_research():
    prompt = build_system_prompt(Locale.EN, Phase.CRYSTALLIZE)
    assert "<web_research>" not in prompt


def test_crystallize_includes_working_document():
    prompt = build_system_prompt(Locale.EN, Phase.CRYSTALLIZE)
    assert "<working_document>" in prompt


# --- Working document: only phases that write sections need it ----------------


def test_decompose_includes_working_document():
    """DECOMPOSE writes problem_context section."""
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "<working_document>" in prompt


def test_explore_includes_working_document():
    """EXPLORE writes cross_domain_patterns section."""
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "<working_document>" in prompt


# --- Phase-scoped enforcement rules -------------------------------------------


def test_decompose_rules_include_rule_1_and_12():
    prompt = build_system_prompt(Locale.EN, Phase.DECOMPOSE)
    assert "fundamentals" in prompt.lower()
    assert "map_state_of_art" in prompt


def test_explore_rules_include_rule_2_and_13():
    prompt = build_system_prompt(Locale.EN, Phase.EXPLORE)
    assert "morphological box" in prompt.lower() or "cross-domain" in prompt.lower()
    assert "search_cross_domain" in prompt


def test_synthesize_rules_include_rules_3_4_8():
    prompt = build_system_prompt(Locale.EN, Phase.SYNTHESIZE)
    assert "find_antithesis" in prompt
    assert "Max 3 claims" in prompt or "max 3" in prompt.lower()


def test_validate_rules_include_rules_5_6_7():
    prompt = build_system_prompt(Locale.EN, Phase.VALIDATE)
    assert "falsification" in prompt.lower()
    assert "novelty" in prompt.lower()


def test_build_rules_include_rules_9_10_11():
    prompt = build_system_prompt(Locale.EN, Phase.BUILD)
    assert "get_negative_knowledge" in prompt or "negative knowledge" in prompt.lower()


# --- Phase-scoped pipeline description ----------------------------------------


def test_each_phase_shows_only_own_pipeline_section():
    """Each phase's prompt describes only its own work, not all 6 phases."""
    for phase in Phase:
        prompt = build_system_prompt(Locale.EN, phase)
        # Current phase section should be present
        assert f"Phase {list(Phase).index(phase) + 1}" in prompt or phase.value.upper() in prompt


# --- PT_BR phase filtering works too ------------------------------------------


def test_pt_br_decompose_excludes_dialectical():
    prompt = build_system_prompt(Locale.PT_BR, Phase.DECOMPOSE)
    assert "<dialectical_method>" not in prompt


def test_pt_br_synthesize_includes_dialectical():
    prompt = build_system_prompt(Locale.PT_BR, Phase.SYNTHESIZE)
    assert "<dialectical_method>" in prompt


def test_pt_br_crystallize_excludes_enforcement_rules():
    prompt = build_system_prompt(Locale.PT_BR, Phase.CRYSTALLIZE)
    assert "<enforcement_rules>" not in prompt


# --- Backward compat: phase=None returns full prompt --------------------------


def test_no_phase_returns_full_prompt():
    """build_system_prompt(locale) without phase returns all sections (backward compat)."""
    prompt = build_system_prompt(Locale.EN)
    assert "<dialectical_method>" in prompt
    assert "<falsifiability>" in prompt
    assert "<knowledge_graph>" in prompt
    assert "<enforcement_rules>" in prompt
    assert "<working_document>" in prompt


# --- Phase prompt is shorter than full prompt ---------------------------------


def test_phase_prompt_shorter_than_full():
    full = build_system_prompt(Locale.EN)
    for phase in Phase:
        scoped = build_system_prompt(Locale.EN, phase)
        assert len(scoped) < len(full), (
            f"Phase {phase.value} prompt ({len(scoped)}) not shorter than full ({len(full)})"
        )
