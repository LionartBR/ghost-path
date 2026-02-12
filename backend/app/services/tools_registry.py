"""Tools Registry — explicit assembly of all 17 custom tools + 1 built-in.

Invariants:
    - ALL_TOOLS is the single source of truth passed to Anthropic messages.create()
    - web_search uses Anthropic built-in format (type instead of name+input_schema)
    - No auto-discovery — every tool is registered explicitly (ExMA: no convention-over-config)

Design Decisions:
    - Flat list over registry pattern: Anthropic API expects a list, no need for lookup
      (ADR: simplicity)
    - max_uses=5 on web_search: controls cost ($10/1000) and context token usage per turn
"""

from app.services.define_analysis_tools import TOOLS_ANALYSIS
from app.services.define_generation_tools import TOOLS_GENERATION
from app.services.define_innovation_tools import TOOLS_INNOVATION
from app.services.define_interaction_tools import TOOLS_INTERACTION
from app.services.define_memory_tools import TOOLS_MEMORY

# ADR: web_search is an Anthropic built-in tool (server-side, not custom).
# Uses a different schema format (type instead of name+input_schema).
# Anthropic handles execution — no handler method needed.
# Pricing: $10/1000 searches, billed to the same ANTHROPIC_API_KEY.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

ALL_TOOLS = (
    TOOLS_ANALYSIS
    + TOOLS_GENERATION
    + TOOLS_INNOVATION
    + TOOLS_INTERACTION
    + TOOLS_MEMORY
    + [WEB_SEARCH_TOOL]
)
