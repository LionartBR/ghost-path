"""Define Research Tool — Anthropic tool schema for delegated web research.

Invariants:
    - Opus calls research() instead of web_search directly
    - Backend intercepts, delegates to Haiku + web_search, returns summary
    - Opus never sees raw page_content (~200K chars per search)

Design Decisions:
    - Single tool replaces web_search in Opus's tool list (ADR: token optimization)
    - purpose enum maps to Haiku search strategies (state_of_art, evidence_for, etc.)
    - instructions field: free-form context from Opus to guide Haiku's search
    - max_results default 3: balances coverage vs token cost
"""

RESEARCH_TOOL = {
    "name": "research",
    "description": (
        "Search the web and return a structured summary of findings. "
        "This tool delegates to a research assistant that performs real-time "
        "web searches and synthesizes results into a concise summary.\n\n"
        "Use this tool whenever you need external evidence:\n"
        "- Before map_state_of_art (Rule #12)\n"
        "- Before search_cross_domain for each target domain (Rule #13)\n"
        "- Before find_antithesis for counter-evidence (Rule #14)\n"
        "- Before attempt_falsification to disprove claims (Rule #15)\n\n"
        "The research assistant searches multiple sources and returns "
        "only verified findings with URLs. If no relevant results are found, "
        "it reports that honestly rather than fabricating content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "What to search for. Be specific: "
                    "'TRIZ contradiction resolution methods 2025 2026' "
                    "not 'innovation methods'"
                ),
            },
            "purpose": {
                "type": "string",
                "enum": [
                    "state_of_art", "evidence_for", "evidence_against",
                    "cross_domain", "novelty_check", "falsification",
                ],
                "description": (
                    "Why you're searching. Determines search strategy:\n"
                    "- state_of_art: current state of a topic\n"
                    "- evidence_for: supporting evidence for a claim\n"
                    "- evidence_against: counter-evidence or challenges\n"
                    "- cross_domain: analogies from different domains\n"
                    "- novelty_check: whether a claim already exists\n"
                    "- falsification: evidence that disproves a claim"
                ),
            },
            "instructions": {
                "type": "string",
                "description": (
                    "Additional context to guide the search. "
                    "E.g. 'Focus on AI-augmented methods. Ignore classical TRIZ.'"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Max sources to return (default 3)",
                "default": 3,
            },
        },
        "required": ["query", "purpose"],
    },
}
