"""Memory Tool Schemas — Anthropic Tool Use format for persistence and context tools.

Invariants:
    - get_negative_context must be called before generation in rounds 2+
    - get_context_usage reflects actual token counts from session.total_tokens_used
    - store_premise writes to DB — only tool in this category with side effects

Design Decisions:
    - query_premises filter as enum in schema: prevents arbitrary queries,
      Anthropic validates before reaching handler (ADR: security boundary)
"""

TOOLS_MEMORY = [
    {
        "name": "store_premise",
        "description": (
            "Stores a premise with user score and comment in the database."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "premise_type": {"type": "string"},
                "score": {"type": "number"},
                "user_comment": {"type": "string"},
                "is_winner": {"type": "boolean"},
                "round_number": {"type": "integer"},
            },
            "required": ["title", "premise_type", "round_number"],
        },
    },
    {
        "name": "query_premises",
        "description": (
            "Queries premises from the database. "
            "Filters by score, type, round."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "enum": [
                        "all", "winners", "top_scored",
                        "low_scored", "by_type", "by_round",
                    ],
                },
                "premise_type": {"type": "string"},
                "round_number": {"type": "integer"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["filter"],
        },
    },
    {
        "name": "get_negative_context",
        "description": (
            "Returns premises with score < 5.0 as negative context. "
            "MUST be called before generating premises in rounds 2+."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_context_usage",
        "description": (
            "Returns usage metrics for the 1M token context window."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
