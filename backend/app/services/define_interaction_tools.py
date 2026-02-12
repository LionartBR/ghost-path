"""Interaction Tool Schemas — Anthropic Tool Use format for user-facing tools.

Invariants:
    - All 3 tools pause the agent loop (awaiting_user_input = True)
    - present_round requires buffer == 3 AND all premises tested
    - generate_final_spec requires prior "Problem Resolved" from user

Design Decisions:
    - spec_content as single string field: the agent generates complete Markdown in one call,
      no incremental assembly — simpler persistence and download (ADR: hackathon)
"""

TOOLS_INTERACTION = [
    {
        "name": "ask_user",
        "description": (
            "Asks the user a question with selectable options. "
            "The flow PAUSES until the user responds."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to display to the user",
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short option text",
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional description",
                            },
                        },
                        "required": ["label"],
                    },
                    "minItems": 2,
                    "maxItems": 5,
                    "description": "Selectable options.",
                },
                "allow_free_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "Display a free text field",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context above the question",
                },
            },
            "required": ["question", "options"],
        },
    },
    {
        "name": "present_round",
        "description": (
            "Presents the round of 3 premises to the user. "
            "Premises are read from the internal buffer. "
            "RETURNS ERROR if buffer does not have exactly 3 premises. "
            "RETURNS ERROR if any premise has not passed obviousness_test. "
            "The flow PAUSES until the user submits scores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "round_summary": {
                    "type": "string",
                    "description": (
                        "Brief summary of the strategy used for "
                        "this round's premises"
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_final_spec",
        "description": (
            "Generates the final .md spec from the winning premise. "
            "Called ONLY after the user triggers 'Problem Resolved'. "
            "The generated content is saved as a .md file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "winning_premise_title": {"type": "string"},
                "winning_premise_body": {"type": "string"},
                "winning_score": {"type": "number"},
                "problem_statement": {"type": "string"},
                "evolution_summary": {
                    "type": "string",
                    "description": (
                        "Summary of the evolutionary journey"
                    ),
                },
                "spec_content": {
                    "type": "string",
                    "description": (
                        "The COMPLETE spec content in Markdown. "
                        "Must include: Executive Summary, The Problem, "
                        "The Solution, How It Works, Implementation, "
                        "Risks and Mitigations, Success Metrics, "
                        "Evolutionary Journey."
                    ),
                },
            },
            "required": [
                "winning_premise_title", "winning_premise_body",
                "problem_statement", "spec_content",
            ],
        },
    },
]
