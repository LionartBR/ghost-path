"""Define DECOMPOSE Tools — Anthropic tool schemas for Phase 1.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - map_state_of_art requires web_search first (enforced in handler, documented in description)
"""

TOOLS_DECOMPOSE = [
    {
        "name": "decompose_to_fundamentals",
        "description": """Break a problem into its irreducible elements.

This tool identifies the fundamental building blocks of a problem — the core components that cannot be further simplified. Use different decomposition approaches like:
- Functional: what needs to be accomplished
- Structural: what components are involved
- Causal: what relationships drive the system
- Temporal: what sequence of events matters

Returns a list of fundamental elements that form the foundation for deeper analysis.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_text": {
                    "type": "string",
                    "description": "The problem statement to decompose"
                },
                "approach": {
                    "type": "string",
                    "description": "The decomposition approach being used (e.g., 'functional', 'structural', 'causal', 'temporal')"
                },
                "fundamentals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The irreducible elements identified — each a concise statement of a core component, constraint, or relationship",
                    "minItems": 1
                }
            },
            "required": ["problem_text", "approach", "fundamentals"]
        }
    },
    {
        "name": "map_state_of_art",
        "description": """Research and map the current state of knowledge in a domain.

CRITICAL: You MUST use web_search to gather current information BEFORE calling this tool. This tool synthesizes web search findings into a coherent state-of-art summary.

Captures:
- Current best practices and approaches
- Recent breakthroughs or innovations
- Known limitations and open problems
- Key researchers or organizations
- Performance benchmarks

This establishes the baseline against which novelty will be measured.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "The domain being researched (e.g., 'machine learning optimization', 'urban transportation')"
                },
                "key_findings": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of key findings from web_search — each should be a concise, factual statement about current state of art",
                    "minItems": 1
                }
            },
            "required": ["domain", "key_findings"]
        }
    },
    {
        "name": "extract_assumptions",
        "description": """Identify hidden assumptions embedded in the problem or current approaches.

Assumptions are beliefs taken for granted that constrain the solution space. Common categories:
- Structural: what components must exist
- Temporal: what must happen in sequence
- Resource: what is scarce or abundant
- Stakeholder: whose needs matter
- Causal: what causes what

Each assumption should cite its source (problem statement, current approaches, domain norms, etc.). Challenging these assumptions later (in EDGE phase) unlocks non-obvious solutions.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "assumptions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The assumption statement (e.g., 'Transportation must be individually owned')"
                            },
                            "source": {
                                "type": "string",
                                "description": "Where this assumption comes from (e.g., 'current market structure', 'problem statement', 'industry standard practice')"
                            },
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "2-4 contextual response options for this assumption. "
                                    "Each option represents a distinct stance (e.g., confirm, nuance, challenge). "
                                    "Order from most agreeable to most challenging.",
                                "minItems": 2,
                                "maxItems": 4
                            }
                        },
                        "required": ["text", "source", "options"]
                    },
                    "description": "List of hidden assumptions with their sources",
                    "minItems": 1
                }
            },
            "required": ["assumptions"]
        }
    },
    {
        "name": "reframe_problem",
        "description": """Generate an alternative formulation of the problem.

Reframing changes perspective to reveal new solution paths. Types:
- scope_change: zoom in/out (e.g., 'reduce traffic' → 'eliminate need for commute')
- entity_question: change who/what (e.g., 'how to move people' → 'how to move work to people')
- variable_change: optimize different metric (e.g., 'fastest route' → 'most predictable route')
- domain_change: view through different lens (e.g., transportation as information problem)

Each reframing should feel like looking at the same problem through a different lens, potentially revealing overlooked opportunities.

RESONANCE ASSESSMENT: You MUST generate a resonance_prompt (question probing how this reframing shifts the user's thinking) and resonance_options (3-4 graduated options). Option 0 MUST be a "doesn't shift my perspective" variant. Options 1+ represent increasing resonance. The user's selection tells Phase 2 HOW the reframing shifted their thinking, not just that it did.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "reframing_text": {
                    "type": "string",
                    "description": "The reframed problem statement"
                },
                "reframing_type": {
                    "type": "string",
                    "enum": ["scope_change", "entity_question", "variable_change", "domain_change"],
                    "description": "The type of reframing applied"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this reframing might reveal new solutions — what shift in perspective does it create?"
                },
                "resonance_prompt": {
                    "type": "string",
                    "description": "A question probing how this reframing shifts the user's perspective on their problem. Example: 'Does viewing transportation as an information coordination problem change how you think about your routing challenge?'"
                },
                "resonance_options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-4 options from 'no perspective shift' to 'fundamentally changes how I see the problem'. Option 0 MUST be a 'doesn't shift my perspective' variant. Example: ['Doesn\\'t shift my perspective', 'Interesting but doesn\\'t change my approach', 'Opens a new angle I hadn\\'t considered', 'Completely changes how I see the problem']",
                    "minItems": 3,
                    "maxItems": 4
                }
            },
            "required": ["reframing_text", "reframing_type", "reasoning", "resonance_prompt", "resonance_options"]
        }
    }
]
