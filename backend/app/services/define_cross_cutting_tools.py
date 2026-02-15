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
- Current phase (FRAME/DISCOVER/VERIFY/BUILD/CRYSTALLIZE)
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
            "- build: graph_nodes, graph_edges, negative_knowledge, gaps, web_searches"
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
]
