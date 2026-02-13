"""Tools Registry — flat list of all TRIZ tools for Anthropic API.

Invariants:
    - ALL_TOOLS is a flat list of tool schemas — Anthropic API expects this format
    - web_search is built-in (server-side) — included with type "web_search_20250305"
    - 20 custom tools + 1 built-in = 21 total

Design Decisions:
    - Explicit imports from each define_*_tools.py: no auto-discovery (ADR: ExMA anti-pattern)
    - Flat list: Anthropic messages.create() takes tools=ALL_TOOLS directly
    - max_uses=10 on web_search: TRIZ is research-heavy, needs more searches than v1
"""

from app.services.define_decompose_tools import TOOLS_DECOMPOSE
from app.services.define_explore_tools import TOOLS_EXPLORE
from app.services.define_synthesize_tools import TOOLS_SYNTHESIZE
from app.services.define_validate_tools import TOOLS_VALIDATE
from app.services.define_build_tools import TOOLS_BUILD
from app.services.define_crystallize_tools import TOOLS_CRYSTALLIZE
from app.services.define_cross_cutting_tools import TOOLS_CROSS_CUTTING


# ADR: web_search is an Anthropic built-in tool (server-side, not custom).
# Uses a different schema format (type instead of name+input_schema).
# Anthropic handles execution — no handler method needed.
# Pricing: $10/1000 searches, billed to the same ANTHROPIC_API_KEY.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 10,
}

ALL_TOOLS: list[dict] = [
    *TOOLS_DECOMPOSE,        # 4 tools
    *TOOLS_EXPLORE,          # 4 tools
    *TOOLS_SYNTHESIZE,       # 3 tools
    *TOOLS_VALIDATE,         # 3 tools
    *TOOLS_BUILD,            # 3 tools
    *TOOLS_CRYSTALLIZE,      # 1 tool
    *TOOLS_CROSS_CUTTING,    # 2 tools
    WEB_SEARCH_TOOL,         # 1 built-in
]
# Total: 20 custom + 1 built-in = 21
