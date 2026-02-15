"""Define SYNTHESIZE Tools — Anthropic tool schemas for Phase 3.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - Evidence objects require url + title + summary for full provenance
    - Thesis must precede antithesis to enforce dialectical order
"""

TOOLS_SYNTHESIZE = [
    {
        "name": "state_thesis",
        "description": (
            "Declare your current knowledge or hypothesis on a specific direction. "
            "This is the 'thesis' in dialectical reasoning — your initial position backed by evidence. "
            "You must provide web-sourced evidence to support the thesis. "
            "Call this after completing reframing or analogy exploration to formalize your knowledge claim."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "thesis_text": {
                    "type": "string",
                    "description": "The knowledge claim or hypothesis you are stating"
                },
                "direction": {
                    "type": "string",
                    "description": "Which reframing or analogy this thesis pursues (reference the axis or domain)"
                },
                "supporting_evidence": {
                    "type": "array",
                    "description": "Web-sourced evidence supporting this thesis",
                    "minItems": 1,
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
                                "description": "Summary of how this evidence supports the thesis"
                            }
                        },
                        "required": ["url", "title", "summary"]
                    }
                }
            },
            "required": ["thesis_text", "direction", "supporting_evidence"]
        }
    },
    {
        "name": "find_antithesis",
        "description": (
            "Search for contradicting evidence or counter-arguments to a thesis. "
            "This is the 'antithesis' in dialectical reasoning — what challenges your position. "
            "You MUST call the research tool to find real contradicting evidence before this. "
            "Error: ANTITHESIS_NOT_SEARCHED. "
            "The stronger the antithesis, the more robust the eventual synthesis will be."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index of the claim (0-2) in the current round this antithesis challenges"
                },
                "antithesis_text": {
                    "type": "string",
                    "description": "The counter-evidence or contradicting position"
                },
                "contradicting_evidence": {
                    "type": "array",
                    "description": "Web-sourced evidence that contradicts the thesis",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL of the contradicting source"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title or brief identifier of the source"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Summary of how this contradicts the thesis"
                            }
                        },
                        "required": ["url", "title", "summary"]
                    }
                }
            },
            "required": ["claim_index", "antithesis_text", "contradicting_evidence"]
        }
    },
    {
        "name": "create_synthesis",
        "description": (
            "Synthesize thesis + antithesis into a knowledge claim. "
            "Requires: falsifiability_condition, confidence, evidence, and a prior antithesis "
            "for this claim_index. Error: ANTITHESIS_MISSING or CLAIM_LIMIT_EXCEEDED.\n\n"
            "In Round 2+, builds_on_claim_id is REQUIRED (Rule #9). "
            "Error: NOT_CUMULATIVE.\n\n"
            "RESONANCE: Generate resonance_prompt + resonance_options (3-4). "
            "Option 0 = 'doesn't resonate'. Focus on STRUCTURAL impact, not epistemic certainty."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_index": {
                    "type": "integer",
                    "description": "Index (0-2) for this claim in the current round buffer"
                },
                "claim_text": {
                    "type": "string",
                    "description": "The synthesized knowledge claim"
                },
                "reasoning": {
                    "type": "string",
                    "description": "How the thesis and antithesis were synthesized into this claim"
                },
                "falsifiability_condition": {
                    "type": "string",
                    "description": "HOW to disprove this claim — what observation or evidence would falsify it"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["speculative", "emerging", "grounded"],
                    "description": (
                        "Confidence level: speculative (weak evidence), "
                        "emerging (some evidence), grounded (strong evidence)"
                    )
                },
                "thesis_text": {
                    "type": "string",
                    "description": "The original thesis that was stated (from state_thesis)"
                },
                "antithesis_text": {
                    "type": "string",
                    "description": "The contradicting position found (from find_antithesis)"
                },
                "evidence": {
                    "type": "array",
                    "description": "All supporting evidence for this synthesis",
                    "minItems": 1,
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
                                "description": "Summary of how this evidence supports the synthesis"
                            }
                        },
                        "required": ["url", "title", "summary"]
                    }
                },
                "builds_on_claim_id": {
                    "type": "string",
                    "description": "Optional: UUID of a previous claim this synthesis builds on"
                },
                "resonance_prompt": {
                    "type": "string",
                    "description": (
                        "A question probing whether this synthesis transcends the "
                        "thesis-antithesis contradiction in a structurally meaningful way. "
                        "Example: 'Does framing distributed consensus as an information "
                        "routing problem open directions you hadn\\'t considered?'"
                    )
                },
                "resonance_options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "3-4 options from 'no resonance' to 'fundamentally shifts my "
                        "understanding'. Option 0 MUST be a 'doesn\\'t resonate' variant. "
                        "Example: ['Doesn\\'t open new directions', "
                        "'Interesting but incremental', "
                        "'Opens a direction I hadn\\'t considered', "
                        "'Fundamentally changes how I see the problem']"
                    ),
                    "minItems": 3,
                    "maxItems": 4
                }
            },
            "required": [
                "claim_index",
                "claim_text",
                "reasoning",
                "thesis_text",
                "antithesis_text",
                "falsifiability_condition",
                "confidence",
                "evidence",
                "resonance_prompt",
                "resonance_options"
            ]
        }
    }
]
