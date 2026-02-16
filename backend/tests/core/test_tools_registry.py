"""Tools Registry tests — verify phase-scoped tool lists and backward compat.

Tests cover:
    - Each phase gets correct tool count (phase + cross-cutting + research)
    - recall_phase_context excluded from DECOMPOSE (nothing to recall)
    - search_research_archive excluded from DECOMPOSE (nothing to search)
    - recall_phase_context + search_research_archive included in EXPLORE and later
    - research excluded from CRYSTALLIZE (write-only phase)
    - update_working_document available in all phases
    - ALL_TOOLS backward compat has 24 entries (23 custom + 1 research)

Design Decisions:
    - Tool counts validated per phase as integration-level contract
    - Tool name checks verify inclusion/exclusion of specific tools
    - research replaces web_search in Opus tool list (ADR: token optimization)
"""

from app.core.domain_types import Phase
from app.services.tools_registry import get_phase_tools, ALL_TOOLS


def _tool_names(phase: Phase) -> set[str]:
    return {t.get("name", "") for t in get_phase_tools(phase)}


def test_decompose_has_correct_tools():
    """4 decompose + 4 cross-cutting (no recall/search) + research = 9."""
    tools = get_phase_tools(Phase.DECOMPOSE)
    assert len(tools) == 9
    names = _tool_names(Phase.DECOMPOSE)
    assert "decompose_to_fundamentals" in names
    assert "map_state_of_art" in names
    assert "research" in names


def test_explore_has_correct_tools():
    """4 explore + 6 cross-cutting (incl recall + search_research + read_wd) + research = 11."""
    tools = get_phase_tools(Phase.EXPLORE)
    assert len(tools) == 11
    names = _tool_names(Phase.EXPLORE)
    assert "build_morphological_box" in names
    assert "recall_phase_context" in names
    assert "search_research_archive" in names


def test_synthesize_has_correct_tools():
    """3 synthesize + 6 cross-cutting (incl recall + search_research + read_wd) + research = 10."""
    tools = get_phase_tools(Phase.SYNTHESIZE)
    assert len(tools) == 10
    names = _tool_names(Phase.SYNTHESIZE)
    assert "state_thesis" in names
    assert "recall_phase_context" in names


def test_validate_has_correct_tools():
    """3 validate + 6 cross-cutting + research = 10."""
    tools = get_phase_tools(Phase.VALIDATE)
    assert len(tools) == 10


def test_build_has_correct_tools():
    """3 build + 6 cross-cutting + research = 10."""
    tools = get_phase_tools(Phase.BUILD)
    assert len(tools) == 10
    names = _tool_names(Phase.BUILD)
    assert "add_to_knowledge_graph" in names
    assert "recall_phase_context" in names
    assert "search_research_archive" in names


def test_crystallize_has_correct_tools():
    """1 crystallize + 6 cross-cutting (incl recall + search + read_wd) - research = 7."""
    tools = get_phase_tools(Phase.CRYSTALLIZE)
    assert len(tools) == 7
    names = _tool_names(Phase.CRYSTALLIZE)
    assert "generate_knowledge_document" in names
    assert "recall_phase_context" in names
    assert "search_research_archive" in names


def test_recall_excluded_from_decompose():
    """recall_phase_context not in DECOMPOSE tools (nothing to recall)."""
    names = _tool_names(Phase.DECOMPOSE)
    assert "recall_phase_context" not in names


def test_search_research_archive_excluded_from_decompose():
    """search_research_archive not in DECOMPOSE (nothing to search)."""
    names = _tool_names(Phase.DECOMPOSE)
    assert "search_research_archive" not in names


def test_recall_included_in_explore():
    """recall_phase_context available from EXPLORE onward."""
    names = _tool_names(Phase.EXPLORE)
    assert "recall_phase_context" in names


def test_search_research_archive_included_in_explore():
    """search_research_archive available from EXPLORE onward."""
    names = _tool_names(Phase.EXPLORE)
    assert "search_research_archive" in names


def test_research_excluded_from_crystallize():
    """No research in CRYSTALLIZE (write-only phase)."""
    names = _tool_names(Phase.CRYSTALLIZE)
    assert "research" not in names


def test_all_tools_backward_compat():
    """ALL_TOOLS has 25 entries (24 custom + 1 research)."""
    assert len(ALL_TOOLS) == 25
    names = {t.get("name", "") for t in ALL_TOOLS}
    assert "recall_phase_context" in names
    assert "search_research_archive" in names
    assert "research" in names
    assert "decompose_to_fundamentals" in names
    assert "generate_knowledge_document" in names
    assert "update_working_document" in names
    assert "read_working_document" in names


def test_update_working_document_available_in_all_phases():
    """update_working_document is a cross-cutting tool available everywhere."""
    for phase in Phase:
        names = _tool_names(phase)
        assert "update_working_document" in names, (
            f"update_working_document missing from {phase.value}"
        )
