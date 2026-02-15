"""Define Cross-Cutting Tools — Anthropic tool schemas for session management and user collaboration.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code
    - Tools available across all phases

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - get_session_status has no inputs: stateless query pattern
    - submit_user_insight enables user co-creation: user becomes active collaborator, not just evaluator
"""

TOOLS_CROSS_CUTTING = [
    {
        "name": "get_session_status",
        "description": """Get current session status — phase, round, claims count, gaps count, context usage.

Use this to orient yourself after user input or when deciding what to do next. It shows:
- Current phase (DECOMPOSE/EXPLORE/SYNTHESIZE/VALIDATE/BUILD/CRYSTALLIZE)
- Round number within the phase
- Total claims generated/accepted/rejected
- Identified gaps count
- Token usage (1M context window limit)

This is a read-only informational tool with no side effects.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "submit_user_insight",
        "description": """Submit a user-contributed knowledge claim to the investigation.

This tool allows the user to actively participate in knowledge creation, not just evaluate your claims. When the user types a claim or insight in the UI, you call this tool to integrate it.

The user's claim should be treated with the same rigor as your own:
- Add it to the current buffer
- Subject it to obviousness_test (if appropriate)
- Eventually present it for verification (though the user already believes it, they may qualify it with evidence requirements)
- Add it to the knowledge graph with edges

This makes the investigation collaborative.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight_text": {
                    "type": "string",
                    "description": "The user's knowledge claim or insight"
                },
                "evidence_urls": {
                    "type": "array",
                    "description": "URLs the user provides as supporting evidence (optional)",
                    "items": {
                        "type": "string"
                    }
                },
                "relates_to_claim_id": {
                    "type": "string",
                    "description": "Optional UUID of an existing claim this insight relates to or extends"
                }
            },
            "required": ["insight_text"]
        }
    },
    {
        "name": "search_research_archive",
        "description": (
            "Search past research results by keyword, phase, or purpose. "
            "Returns matching entries with full summaries and source URLs.\n\n"
            "TOKEN COST WARNING: Each result is ~300 tokens. Default limit: "
            "3 results (~900 tokens). Use targeted keyword searches.\n\n"
            "When to use:\n"
            "- Need full details of a specific past search\n"
            "- Looking for cross-phase patterns (e.g., 'What did we learn about X?')\n"
            "- Need source URLs from earlier phases\n\n"
            "Your phase digest already contains compact summaries of recent "
            "research — check there first before searching."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search (AND logic: all must match)",
                },
                "phase": {
                    "type": "string",
                    "enum": [
                        "decompose", "explore", "synthesize",
                        "validate", "build",
                    ],
                    "description": "Limit to a specific phase (optional)",
                },
                "purpose": {
                    "type": "string",
                    "enum": [
                        "state_of_art", "evidence_for", "evidence_against",
                        "cross_domain", "novelty_check", "falsification",
                    ],
                    "description": "Limit to a specific research purpose (optional)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max entries to return (1-10). Each ~300 tokens.",
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "recall_phase_context",
        "description": (
            "Retrieve detailed artifacts from a completed phase. "
            "Use when you need specific data from an earlier phase. "
            "Returns raw structured data. Read-only, no side effects. "
            "Only call for phases already completed — calling for "
            "current or future phases returns an error.\n\n"
            "Valid phase-artifact combinations:\n"
            "- decompose: fundamentals, assumptions, reframings, web_searches\n"
            "- explore: morphological_box, analogies, contradictions, adjacent_possible, web_searches\n"
            "- synthesize: claims, web_searches\n"
            "- validate: claims, web_searches\n"
            "- build: graph_nodes, graph_edges, negative_knowledge, gaps, web_searches\n\n"
            "Note: web_searches returns compact summaries. For full detail "
            "with keyword filtering, use search_research_archive instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": [
                        "decompose", "explore", "synthesize",
                        "validate", "build",
                    ],
                    "description": "The completed phase to recall from",
                },
                "artifact": {
                    "type": "string",
                    "enum": [
                        "fundamentals", "assumptions", "reframings",
                        "morphological_box", "analogies",
                        "contradictions", "adjacent_possible",
                        "claims", "graph_nodes", "graph_edges",
                        "negative_knowledge", "gaps", "web_searches",
                    ],
                    "description": "The specific artifact to retrieve",
                },
            },
            "required": ["phase", "artifact"],
        },
    },
    {
        "name": "update_working_document",
        "description": (
            "Write or update a section of the working Knowledge Document.\n\n"
            "Call this during each phase to capture discoveries while context "
            "is fresh. Best practice: update at least one section per phase.\n\n"
            "Phase-to-section mapping:\n"
            '- DECOMPOSE: "problem_context" (problem landscape, reframings, gaps)\n'
            '- EXPLORE: "cross_domain_patterns" (analogies), "technical_details" (morphological params)\n'
            '- SYNTHESIZE: "core_insight" (the discovery), "reasoning_chain", "evidence_base"\n'
            '- VALIDATE: "evidence_base" (update with validation), "boundaries" (limitations)\n'
            '- BUILD: "technical_details" (update from graph), "boundaries" (negative knowledge)\n'
            '- CRYSTALLIZE: "implementation_guide", "next_frontiers", polish all\n\n'
            "Calling with an existing section key replaces it entirely. "
            "Write the complete updated version each time.\n"
            'Write as a knowledge artifact — "X works because Y" not '
            '"In Phase 2, we explored...".'
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": [
                        "core_insight", "problem_context", "reasoning_chain",
                        "evidence_base", "technical_details",
                        "cross_domain_patterns", "boundaries",
                        "implementation_guide", "next_frontiers",
                    ],
                    "description": "Which document section to write/update",
                },
                "content": {
                    "type": "string",
                    "description": "Full markdown content for this section",
                },
            },
            "required": ["section", "content"],
        },
    },
]
