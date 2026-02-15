"""Define BUILD Tools — Anthropic tool schemas for Phase 5 knowledge graph construction.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code
    - add_to_knowledge_graph requires user verdict gate (enforced by handler)

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - Edge types as enum in description: supports/contradicts/extends/supersedes/depends_on/merged_from
    - Negative knowledge separate tool: enables Rule #10 compliance tracking
"""

TOOLS_BUILD = [
    {
        "name": "add_to_knowledge_graph",
        "description": """Add a validated claim to the knowledge graph with typed edges to other claims.

GATE: The claim at claim_index must have a user verdict (accept/qualify). This tool will return an error if called on unverified claims.

Use this after the user has accepted or qualified a claim to integrate it into the growing knowledge structure.

Edge types:
- supports: This claim provides evidence for the target claim
- contradicts: This claim conflicts with the target claim
- extends: This claim builds upon or elaborates the target claim
- supersedes: This claim replaces or invalidates the target claim
- depends_on: This claim requires the target claim to be true
- merged_from: This claim was synthesized from the target claim (and others)

You should identify all relevant edges — don't just connect to the most recent claim. Look across the entire graph.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index of the claim in the current buffer (0-based)"
                },
                "edges": {
                    "type": "array",
                    "description": "Typed relationships to other claims in the graph",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target_claim_id": {
                                "type": "string",
                                "description": "UUID of the target claim to connect to"
                            },
                            "edge_type": {
                                "type": "string",
                                "enum": ["supports", "contradicts", "extends", "supersedes", "depends_on", "merged_from"],
                                "description": "Type of relationship between this claim and the target"
                            }
                        },
                        "required": ["target_claim_id", "edge_type"]
                    }
                }
            },
            "required": ["claim_index", "edges"]
        }
    },
    {
        "name": "analyze_gaps",
        "description": """Identify structural gaps in the knowledge graph — missing prerequisites, disconnected nodes, convergence locks.

Use this periodically (every 2-3 rounds) to step back and assess the graph's completeness. A convergence lock occurs when multiple claims depend on a missing foundational claim that hasn't been proven yet.

This tool helps you decide what to investigate next. If you find gaps, use the research tool or generate new claims to fill them.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "gaps": {
                    "type": "array",
                    "description": "List of identified gaps — missing claims, disconnected subgraphs, weak evidence areas",
                    "items": {
                        "type": "string"
                    }
                },
                "convergence_locks": {
                    "type": "array",
                    "description": "Areas where multiple claims depend on unproven prerequisites",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "What is blocked (e.g., '3 claims about X all assume Y is true')"
                            },
                            "missing_prerequisites": {
                                "type": "array",
                                "description": "The foundational claims that need to be proven",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["description", "missing_prerequisites"]
                    }
                }
            },
            "required": ["gaps", "convergence_locks"]
        }
    },
    {
        "name": "get_negative_knowledge",
        "description": """Retrieve all claims that were rejected by the user, along with their rejection reasons.

MANDATORY in Round 2+ (Rule #10). Call BEFORE state_thesis in rounds after the first.
Error: NEGATIVE_KNOWLEDGE_MISSING. Avoids re-proposing ideas the user already dismissed.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]
