"""Tool schema regression tests — verify search_cross_domain has no cognitive anchors.

Invariants:
    - source_domain description must not hardcode specific domain examples
    - Semantic distance examples must not name concrete domains
    - Description must guide agent toward Phase 1 derivation

Design Decisions:
    - Separate test file: schema validation is a distinct concern from handler behavior
    - Tests check string content of tool definitions, not handler logic
"""

from app.services.define_explore_tools import TOOLS_EXPLORE


def _get_search_cross_domain_tool() -> dict:
    """Extract search_cross_domain from TOOLS_EXPLORE list."""
    return next(t for t in TOOLS_EXPLORE if t["name"] == "search_cross_domain")


def test_source_domain_no_hardcoded_examples():
    """source_domain field must not suggest specific domains as examples."""
    tool = _get_search_cross_domain_tool()
    desc = tool["input_schema"]["properties"]["source_domain"]["description"]
    desc_lower = desc.lower()
    for anchor in ["immune system", "jazz", "forest ecosystem", "ant colony"]:
        assert anchor not in desc_lower, f"Hardcoded anchor '{anchor}' found in source_domain"


def test_description_no_concrete_domain_in_distance_examples():
    """Semantic distance examples must not name specific source domains."""
    tool = _get_search_cross_domain_tool()
    desc_lower = tool["description"].lower()
    for anchor in ["ant colony", "internet routing"]:
        assert anchor not in desc_lower, f"Hardcoded anchor '{anchor}' found in description"


def test_description_encourages_phase1_derivation():
    """Tool description or source_domain field guides toward Phase 1 context."""
    tool = _get_search_cross_domain_tool()
    source_desc = tool["input_schema"]["properties"]["source_domain"]["description"].lower()
    assert "phase 1" in source_desc or "derive" in source_desc or "fundamentals" in source_desc
