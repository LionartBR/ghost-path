"""Define CRYSTALLIZE Tools — Anthropic tool schemas for Phase 6 final artifact generation.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code
    - generate_knowledge_document assembles from working document sections

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - Minimal finalizer: working document built incrementally across phases
    - Missing sections appear as placeholder text in final artifact
"""

TOOLS_CRYSTALLIZE = [
    {
        "name": "generate_knowledge_document",
        "description": (
            "Finalize the Knowledge Document by assembling all working sections.\n\n"
            "Before calling this, use update_working_document to write "
            '"implementation_guide" and "next_frontiers", and polish existing '
            "sections.\n"
            "This tool reads all 9 sections from the working document, assembles "
            "the final markdown artifact, saves it to disk, and pauses the agent "
            "loop.\n\n"
            'Missing sections appear as "[Section not yet written]".'
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title (concise, < 80 chars)",
                },
            },
            "required": ["title"],
        },
    }
]
