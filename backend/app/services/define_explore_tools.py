"""Define EXPLORE Tools — Anthropic tool schemas for Phase 2.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - search_cross_domain requires web_search for target domain (enforced in handler, documented in description)
    - Morphological box requires minimum 3x3 parameter space for meaningful exploration
"""

TOOLS_EXPLORE = [
    {
        "name": "build_morphological_box",
        "description": """Map the multi-dimensional parameter space of possible solutions.

A morphological box is a matrix where:
- Rows = independent parameters/dimensions of the solution
- Columns = possible values for each parameter
- Each combination of values = a potential solution

Example for 'personal transportation':
- Power source: [human, electric, combustion, hybrid]
- Form factor: [two-wheel, four-wheel, single-track, flying]
- Ownership: [individual, shared, subscription, on-demand]

Minimum 3 parameters with 3 values each. This systematic mapping ensures comprehensive exploration of the solution space, preventing fixation on conventional combinations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "parameters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The parameter/dimension name (e.g., 'power source', 'interaction mode')"
                            },
                            "values": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Possible values for this parameter",
                                "minItems": 3
                            }
                        },
                        "required": ["name", "values"]
                    },
                    "description": "List of parameters with their possible values — minimum 3 parameters required for meaningful exploration",
                    "minItems": 3
                }
            },
            "required": ["parameters"]
        }
    },
    {
        "name": "search_cross_domain",
        "description": """Find structural analogies in a semantically distant domain.

CRITICAL: You MUST use web_search to research the source domain BEFORE calling this tool. This ensures analogies are grounded in real-world patterns, not training data.

The tool maps patterns from one domain to another based on structural similarity, not surface features. Semantic distance matters:
- near: same industry, different application (automotive → aerospace)
- medium: different industry, similar constraints (supply chain → blood distribution)
- far: completely different domain with no obvious surface similarity to the problem

The further the semantic distance, the more non-obvious the insight. Focus on HOW the source domain solves analogous problems (mechanisms, principles, trade-offs), not what it looks like.

RESONANCE ASSESSMENT: You MUST generate a resonance_prompt (question probing the structural connection) and resonance_options (3-4 options from 'no connection' to 'deep structural match'). Option 0 must always be a 'no structural connection' variant. The user's selection tells Phase 3 WHY this analogy resonated, not just that it did.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_domain": {
                    "type": "string",
                    "description": "The domain to borrow structural patterns from — derive from Phase 1 fundamentals, assumptions, or reframings rather than defaulting to generic domains"
                },
                "target_application": {
                    "type": "string",
                    "description": "How patterns from source domain could apply to the target problem"
                },
                "analogy_description": {
                    "type": "string",
                    "description": "Detailed explanation of the structural similarity — what patterns map from source to target and why?"
                },
                "semantic_distance": {
                    "type": "string",
                    "enum": ["near", "medium", "far"],
                    "description": "How distant is the source domain from the target problem domain"
                },
                "key_findings": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Key findings from web_search about the source domain — mechanisms, patterns, or principles that will be mapped",
                    "minItems": 1
                },
                "resonance_prompt": {
                    "type": "string",
                    "description": "A question probing the structural connection between this analogy and the user's problem. Example: 'Do you see a parallel between ant colony pheromone coordination and your microservices routing challenge?'"
                },
                "resonance_options": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "3-4 options from 'no connection' to 'deep structural match'. Option 0 MUST be a 'no connection' variant. Example: ['No structural connection', 'Surface similarity only', 'Partial structural match — coordination mechanism applies', 'Deep structural match — pheromone trail ≈ service mesh routing']",
                    "minItems": 3,
                    "maxItems": 4
                }
            },
            "required": ["source_domain", "target_application", "analogy_description", "semantic_distance", "key_findings", "resonance_prompt", "resonance_options"]
        }
    },
    {
        "name": "identify_contradictions",
        "description": """Identify competing requirements using TRIZ contradiction analysis.

A technical contradiction exists when improving one property degrades another:
- Strength vs. Weight (stronger materials are heavier)
- Speed vs. Safety (faster systems have less reaction time)
- Precision vs. Cost (tighter tolerances require expensive manufacturing)

TRIZ identifies contradictions to apply inventive principles that resolve them (separation in time, space, scale, or condition). Not all trade-offs are contradictions — only include pairs where improvement in A directly causes degradation in B within current paradigm.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "property_a": {
                    "type": "string",
                    "description": "First property in the contradiction (e.g., 'battery capacity', 'processing speed')"
                },
                "property_b": {
                    "type": "string",
                    "description": "Second property in the contradiction (e.g., 'charging time', 'energy consumption')"
                },
                "description": {
                    "type": "string",
                    "description": "Explanation of how improving property_a degrades property_b in the current system"
                }
            },
            "required": ["property_a", "property_b", "description"]
        }
    },
    {
        "name": "map_adjacent_possible",
        "description": """Identify what becomes possible one step beyond current capabilities.

The 'adjacent possible' (Stuart Kauffman) is the set of innovations that are just within reach — they require existing capabilities plus one new enabler. Not science fiction, not current state of art, but the next logical step.

Example: Given GPS + smartphones + payment systems, the adjacent possible includes ride-sharing (requires one new element: real-time matching algorithm).

Focus on:
- What current capability serves as foundation
- What single new element makes the leap
- What prerequisites must be in place""",
        "input_schema": {
            "type": "object",
            "properties": {
                "current_capability": {
                    "type": "string",
                    "description": "The existing capability or technology that serves as foundation"
                },
                "adjacent_possibility": {
                    "type": "string",
                    "description": "What becomes possible with one additional step or enabler"
                },
                "prerequisites": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of prerequisites that must exist for this adjacent possibility to be realized",
                    "minItems": 1
                }
            },
            "required": ["current_capability", "adjacent_possibility", "prerequisites"]
        }
    }
]
