"""Tools Registry tests — verify phase-scoped tool lists and backward compat.

Tests cover:
    - Each phase gets correct tool count (phase + cross-cutting + web_search)
    - recall_phase_context excluded from DECOMPOSE (nothing to recall)
    - recall_phase_context included in EXPLORE and later phases
    - web_search excluded from CRYSTALLIZE (no research, just write)
    - ALL_TOOLS backward compat has 22 entries (21 custom + 1 built-in)

Design Decisions:
    - Tool counts validated per phase as integration-level contract
    - Tool name checks verify inclusion/exclusion of specific tools
"""

from app.core.domain_types import Phase
from app.services.tools_registry import get_phase_tools, ALL_TOOLS


def _tool_names(phase: Phase) -> set[str]:
    return {t.get("name", "") for t in get_phase_tools(phase)}


def test_decompose_has_correct_tools():
    """4 decompose + 2 cross-cutting (no recall) + web_search = 7."""
    tools = get_phase_tools(Phase.DECOMPOSE)
    assert len(tools) == 7
    names = _tool_names(Phase.DECOMPOSE)
    assert "decompose_to_fundamentals" in names
    assert "map_state_of_art" in names
    assert "web_search" in names


def test_explore_has_correct_tools():
    """4 explore + 3 cross-cutting (incl recall) + web_search = 8."""
    tools = get_phase_tools(Phase.EXPLORE)
    assert len(tools) == 8
    names = _tool_names(Phase.EXPLORE)
    assert "build_morphological_box" in names
    assert "recall_phase_context" in names


def test_synthesize_has_correct_tools():
    """3 synthesize + 3 cross-cutting (incl recall) + web_search = 7."""
    tools = get_phase_tools(Phase.SYNTHESIZE)
    assert len(tools) == 7
    names = _tool_names(Phase.SYNTHESIZE)
    assert "state_thesis" in names
    assert "recall_phase_context" in names


def test_validate_has_correct_tools():
    """3 validate + 3 cross-cutting + web_search = 7."""
    tools = get_phase_tools(Phase.VALIDATE)
    assert len(tools) == 7


def test_build_has_correct_tools():
    """3 build + 3 cross-cutting + web_search = 7."""
    tools = get_phase_tools(Phase.BUILD)
    assert len(tools) == 7
    names = _tool_names(Phase.BUILD)
    assert "add_to_knowledge_graph" in names
    assert "recall_phase_context" in names


def test_crystallize_has_correct_tools():
    """1 crystallize + 3 cross-cutting (incl recall) - web_search = 4."""
    tools = get_phase_tools(Phase.CRYSTALLIZE)
    assert len(tools) == 4
    names = _tool_names(Phase.CRYSTALLIZE)
    assert "generate_knowledge_document" in names
    assert "recall_phase_context" in names


def test_recall_excluded_from_decompose():
    """recall_phase_context not in DECOMPOSE tools (nothing to recall)."""
    names = _tool_names(Phase.DECOMPOSE)
    assert "recall_phase_context" not in names


def test_recall_included_in_explore():
    """recall_phase_context available from EXPLORE onward."""
    names = _tool_names(Phase.EXPLORE)
    assert "recall_phase_context" in names


def test_web_search_excluded_from_crystallize():
    """No web_search in CRYSTALLIZE (write-only phase)."""
    names = _tool_names(Phase.CRYSTALLIZE)
    assert "web_search" not in names


def test_all_tools_backward_compat():
    """ALL_TOOLS still has 22 entries (21 custom + 1 built-in)."""
    assert len(ALL_TOOLS) == 22
    names = {t.get("name", "") for t in ALL_TOOLS}
    assert "recall_phase_context" in names
    assert "web_search" in names
    assert "decompose_to_fundamentals" in names
    assert "generate_knowledge_document" in names
