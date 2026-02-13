"""Define VALIDATE Tools — Anthropic tool schemas for Phase 4.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - Falsification and novelty are separate concerns, checked independently
    - Scoring requires both falsification and novelty to be completed first
    - All validation steps require web_search to ensure grounding in real-world evidence
"""

TOOLS_VALIDATE = [
    {
        "name": "attempt_falsification",
        "description": (
            "Attempt to disprove a knowledge claim using the falsifiability condition. "
            "This is Popperian falsification — actively trying to break your own claim. "
            "You MUST use web_search to find evidence that could disprove the claim. "
            "If the claim survives falsification attempts, it gains epistemic strength. "
            "If it fails, mark falsified=true and explain what disproved it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index (0-2) of the claim being tested for falsification"
                },
                "falsification_approach": {
                    "type": "string",
                    "description": "What approach or test you used to try to disprove the claim"
                },
                "result": {
                    "type": "string",
                    "description": "What you found when attempting falsification"
                },
                "falsified": {
                    "type": "boolean",
                    "description": "Whether the claim was actually disproved (true) or survived (false)"
                },
                "evidence": {
                    "type": "array",
                    "description": "Web-sourced evidence from the falsification attempt",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL of the evidence source"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title or brief identifier of the source"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Summary of what this evidence showed in the falsification attempt"
                            }
                        },
                        "required": ["url", "title", "summary"]
                    }
                }
            },
            "required": ["claim_index", "falsification_approach", "result", "falsified", "evidence"]
        }
    },
    {
        "name": "check_novelty",
        "description": (
            "Verify that a knowledge claim is not already well-known or documented. "
            "You MUST use web_search to find existing knowledge, research, or publications. "
            "If the claim is already known, mark is_novel=false and cite what exists. "
            "If the claim represents a new connection, framing, or insight, mark is_novel=true "
            "and explain what makes it novel compared to existing knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index (0-2) of the claim being checked for novelty"
                },
                "existing_knowledge": {
                    "type": "array",
                    "description": "What existing knowledge was found via web_search",
                    "items": {
                        "type": "string",
                        "description": "Description of existing knowledge or research found"
                    }
                },
                "is_novel": {
                    "type": "boolean",
                    "description": "Whether the claim is novel (true) or already known (false)"
                },
                "novelty_explanation": {
                    "type": "string",
                    "description": (
                        "If novel: what makes it new compared to existing knowledge. "
                        "If not novel: how it relates to or duplicates existing knowledge."
                    )
                }
            },
            "required": ["claim_index", "existing_knowledge", "is_novel", "novelty_explanation"]
        }
    },
    {
        "name": "score_claim",
        "description": (
            "Compute final scores for a validated knowledge claim. "
            "You can only call this AFTER both attempt_falsification and check_novelty for this claim. "
            "Provide four scores (0.0-1.0): novelty (how new), groundedness (evidence strength), "
            "falsifiability (how testable), significance (potential impact). "
            "Also provide reasoning explaining the scores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index (0-2) of the claim being scored"
                },
                "novelty_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How novel/new the claim is (0.0 = well-known, 1.0 = completely new)"
                },
                "groundedness_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How well-grounded in evidence (0.0 = speculative, 1.0 = strongly supported)"
                },
                "falsifiability_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How testable/falsifiable (0.0 = unfalsifiable, 1.0 = clearly testable)"
                },
                "significance_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Potential impact/importance (0.0 = trivial, 1.0 = highly significant)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of how you arrived at these scores"
                }
            },
            "required": [
                "claim_index",
                "novelty_score",
                "groundedness_score",
                "falsifiability_score",
                "significance_score",
                "reasoning"
            ]
        }
    }
]
