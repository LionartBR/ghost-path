"""Generation Tool Schemas — Anthropic Tool Use format for premise creation tools.

Invariants:
    - All 3 tools are gate-checked: ERROR if analysis gates not satisfied
    - Buffer limit enforced: ERROR if buffer already has 3 premises
    - Radical type requires prior challenge_axiom call

Design Decisions:
    - premise_type enum defined in schema (not just domain_types): Anthropic validates
      the enum server-side before tool_use reaches our handlers
"""

TOOLS_GENERATION = [
    {
        "name": "generate_premise",
        "description": (
            "Generates ONE premise. Adds it to the current round buffer. "
            "RETURNS ERROR if analysis gates have not been satisfied. "
            "RETURNS ERROR if the buffer already has 3 premises. "
            "After generating 3 premises, run obviousness_test on each one "
            "then call present_round."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Concise premise title (1 line)",
                },
                "body": {
                    "type": "string",
                    "description": "Premise body (2-3 paragraphs)",
                },
                "premise_type": {
                    "type": "string",
                    "enum": [
                        "initial", "conservative", "radical", "combination",
                    ],
                },
                "direction_hint": {
                    "type": "string",
                    "description": "Conceptual direction being explored",
                },
                "violated_axiom": {
                    "type": "string",
                    "description": "Violated axiom (required for radical type)",
                },
                "cross_domain_source": {
                    "type": "string",
                    "description": "Inspiration source domain",
                },
            },
            "required": ["title", "body", "premise_type"],
        },
    },
    {
        "name": "mutate_premise",
        "description": (
            "Applies mutation to an existing premise and adds "
            "the result to the buffer. "
            "RETURNS ERROR if gates not satisfied or buffer full."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_title": {
                    "type": "string",
                    "description": "Source premise title",
                },
                "source_body": {
                    "type": "string",
                    "description": "Source premise body",
                },
                "title": {
                    "type": "string",
                    "description": "Mutated premise title",
                },
                "body": {
                    "type": "string",
                    "description": "Mutated premise body",
                },
                "premise_type": {
                    "type": "string",
                    "enum": ["conservative", "radical", "combination"],
                },
                "mutation_strength": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 1.0,
                    "description": "0.1 = subtle, 1.0 = complete inversion",
                },
                "violated_axiom": {"type": "string"},
                "cross_domain_source": {"type": "string"},
            },
            "required": [
                "source_title", "title", "body",
                "premise_type", "mutation_strength",
            ],
        },
    },
    {
        "name": "cross_pollinate",
        "description": (
            "Combines premises and adds the result to the buffer. "
            "RETURNS ERROR if gates not satisfied or buffer full."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "primary_title": {"type": "string"},
                "primary_body": {"type": "string"},
                "secondary_premises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "element_to_extract": {"type": "string"},
                        },
                    },
                },
                "title": {
                    "type": "string",
                    "description": "Title of the resulting combined premise",
                },
                "body": {
                    "type": "string",
                    "description": "Body of the resulting combined premise",
                },
                "premise_type": {
                    "type": "string",
                    "enum": ["combination"],
                },
                "synthesis_strategy": {"type": "string"},
                "violated_axiom": {"type": "string"},
                "cross_domain_source": {"type": "string"},
            },
            "required": [
                "primary_title", "title", "body",
                "premise_type", "synthesis_strategy",
            ],
        },
    },
]
