"""Innovation Tool Schemas — Anthropic Tool Use format for originality enforcement tools.

Invariants:
    - challenge_axiom unlocks radical premise type (enforced in handle_generation)
    - obviousness_test score > 0.6 triggers auto-removal from buffer
    - invert_problem has no prerequisites but feeds into generation strategy

Design Decisions:
    - obviousness_score range (0.0–1.0) enforced in schema: catches invalid scores
      before reaching core/enforce_round.evaluate_obviousness
"""

TOOLS_INNOVATION = [
    {
        "name": "challenge_axiom",
        "description": (
            "Challenges an axiom identified by extract_hidden_axioms. "
            "If the axiom was not previously extracted, returns WARNING. "
            "The agent CANNOT generate a radical variation without "
            "calling this tool first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "axiom": {"type": "string"},
                "violation_strategy": {
                    "type": "string",
                    "enum": [
                        "negate", "invert", "remove",
                        "replace", "exaggerate",
                    ],
                },
                "resulting_insight": {
                    "type": "string",
                    "description": (
                        "The insight that emerges from violating the axiom"
                    ),
                },
            },
            "required": [
                "axiom", "violation_strategy", "resulting_insight",
            ],
        },
    },
    {
        "name": "import_foreign_domain",
        "description": (
            "Finds an analogy from a completely different domain "
            "than the problem. "
            "The source domain MUST have maximum semantic distance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_domain": {"type": "string"},
                "source_domain": {"type": "string"},
                "analogy_seed": {"type": "string"},
                "translated_insight": {
                    "type": "string",
                    "description": (
                        "How the analogy translates to the original problem"
                    ),
                },
            },
            "required": [
                "problem_domain", "source_domain",
                "analogy_seed", "translated_insight",
            ],
        },
    },
    {
        "name": "obviousness_test",
        "description": (
            "Tests whether a premise in the buffer is obvious. "
            "MANDATORY for each premise before present_round. "
            "Returns how many premises still need testing. "
            "Score > 0.6 = discard and regenerate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "premise_buffer_index": {
                    "type": "integer",
                    "description": "Premise index in the buffer (0, 1, or 2)",
                },
                "premise_title": {"type": "string"},
                "obviousness_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "0.0 = completely novel, 1.0 = obvious",
                },
                "justification": {
                    "type": "string",
                    "description": "Why this premise is or is not obvious",
                },
            },
            "required": [
                "premise_buffer_index", "premise_title",
                "obviousness_score", "justification",
            ],
        },
    },
    {
        "name": "invert_problem",
        "description": (
            "Inverts the problem to find non-obvious solutions. "
            "Charlie Munger's technique: 'Invert, always invert.'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "original_problem": {"type": "string"},
                "inversion_type": {
                    "type": "string",
                    "enum": [
                        "cause_problem", "maximize_failure",
                        "remove_solution", "reverse_stakeholders",
                    ],
                },
                "inverted_framing": {
                    "type": "string",
                    "description": (
                        "The problem reframed in inverted form"
                    ),
                },
                "insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "2-3 insights that emerge from the inversion"
                    ),
                },
            },
            "required": [
                "original_problem", "inversion_type",
                "inverted_framing", "insights",
            ],
        },
    },
]
