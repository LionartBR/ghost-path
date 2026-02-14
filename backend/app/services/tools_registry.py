"""Tools Registry — flat list and per-phase filtering of TRIZ tools.

Invariants:
    - get_phase_tools() returns only relevant tools for current phase
    - ALL_TOOLS preserved for backward compatibility
    - recall_phase_context excluded from DECOMPOSE (nothing to recall)
    - web_search excluded from CRYSTALLIZE (no research, just write)

Design Decisions:
    - Phase-scoped tools reduce model confusion: 4-8 tools vs 22
    - Prompt caching works within a phase (tools identical across iterations)
    - Explicit imports from each define_*_tools.py: no auto-discovery (ADR: ExMA)
"""

from app.core.domain_types import Phase
from app.services.define_decompose_tools import TOOLS_DECOMPOSE
from app.services.define_explore_tools import TOOLS_EXPLORE
from app.services.define_synthesize_tools import TOOLS_SYNTHESIZE
from app.services.define_validate_tools import TOOLS_VALIDATE
from app.services.define_build_tools import TOOLS_BUILD
from app.services.define_crystallize_tools import TOOLS_CRYSTALLIZE
from app.services.define_cross_cutting_tools import TOOLS_CROSS_CUTTING


# ADR: web_search is an Anthropic built-in tool (server-side, not custom).
# Uses a different schema format (type instead of name+input_schema).
# Pricing: $10/1000 searches, billed to the same ANTHROPIC_API_KEY.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 10,
}

_CROSS_CUTTING_BASE = [
    t for t in TOOLS_CROSS_CUTTING if t["name"] != "recall_phase_context"
]
_RECALL_TOOL = [
    t for t in TOOLS_CROSS_CUTTING if t["name"] == "recall_phase_context"
]

_PHASE_TOOLS = {
    Phase.DECOMPOSE: TOOLS_DECOMPOSE,
    Phase.EXPLORE: TOOLS_EXPLORE,
    Phase.SYNTHESIZE: TOOLS_SYNTHESIZE,
    Phase.VALIDATE: TOOLS_VALIDATE,
    Phase.BUILD: TOOLS_BUILD,
    Phase.CRYSTALLIZE: TOOLS_CRYSTALLIZE,
}


def get_phase_tools(phase: Phase) -> list[dict]:
    """Return tools for the given phase + cross-cutting + web_search."""
    tools = list(_PHASE_TOOLS[phase])
    tools.extend(_CROSS_CUTTING_BASE)
    if phase != Phase.DECOMPOSE:
        tools.extend(_RECALL_TOOL)
    if phase != Phase.CRYSTALLIZE:
        tools.append(WEB_SEARCH_TOOL)
    return tools


# Backward compat: flat list of ALL tools
ALL_TOOLS: list[dict] = [
    *TOOLS_DECOMPOSE,        # 4 tools
    *TOOLS_EXPLORE,          # 4 tools
    *TOOLS_SYNTHESIZE,       # 3 tools
    *TOOLS_VALIDATE,         # 3 tools
    *TOOLS_BUILD,            # 3 tools
    *TOOLS_CRYSTALLIZE,      # 1 tool
    *TOOLS_CROSS_CUTTING,    # 3 tools (incl recall_phase_context)
    WEB_SEARCH_TOOL,         # 1 built-in
]
# Total: 21 custom + 1 built-in = 22
