"""Analysis Tool Schemas — Anthropic Tool Use format for mandatory gate tools.

Invariants:
    - All 3 tools are mandatory gates: generate_premise/mutate_premise/cross_pollinate
      return ERROR if any gate hasn't been called
    - Schema matches Anthropic Tool Use specification exactly

Design Decisions:
    - One file per category: keeps each under 100 lines (ExMA: 200-400 limit)
    - List export (not dict): Anthropic API expects a flat list of tool objects
"""

TOOLS_ANALYSIS = [
    {
        "name": "decompose_problem",
        "description": (
            "Decomposes the user's problem into key dimensions. "
            "MANDATORY GATE: must be called before any generation tool. "
            "Without this tool, generate_premise/mutate_premise/"
            "cross_pollinate return ERROR."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_statement": {
                    "type": "string",
                    "description": "The problem as described by the user",
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key dimensions identified in the problem",
                },
                "constraints_real": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Real constraints of the problem",
                },
                "constraints_assumed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Constraints that are ASSUMED but may not be real"
                    ),
                },
                "success_metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "How to measure if the problem has been solved"
                    ),
                },
            },
            "required": ["problem_statement", "dimensions"],
        },
    },
    {
        "name": "map_conventional_approaches",
        "description": (
            "Maps conventional approaches that most people would try. "
            "MANDATORY GATE: must be called before generating premises. "
            "The goal is to know WHAT TO AVOID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "approaches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "limitations": {"type": "string"},
                            "why_common": {"type": "string"},
                        },
                    },
                    "description": (
                        "List of conventional approaches with limitations"
                    ),
                },
            },
            "required": ["approaches"],
        },
    },
    {
        "name": "extract_hidden_axioms",
        "description": (
            "Identifies hidden axioms — assumptions everyone takes for granted. "
            "MANDATORY GATE: must be called before generating premises. "
            "The returned axioms become available for challenge_axiom."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "axioms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "axiom": {"type": "string"},
                            "why_assumed": {"type": "string"},
                            "what_if_violated": {"type": "string"},
                        },
                    },
                    "description": (
                        "List of axioms with justification and "
                        "violation consequences"
                    ),
                },
                "existing_axioms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Previously identified axioms (to avoid repetition)"
                    ),
                },
            },
            "required": ["axioms"],
        },
    },
]
