"""Define CRYSTALLIZE Tools — Anthropic tool schemas for Phase 6 final artifact generation.

Invariants:
    - All schemas follow Anthropic tool_use format
    - Required fields enforced by schema, not handler code
    - generate_knowledge_document expects 10 sections (enforced by required fields)

Design Decisions:
    - Tool schemas in dedicated files: explicit, no auto-discovery (ADR: ExMA anti-pattern)
    - Single tool for final doc: ensures atomic generation, no partial artifacts
    - All sections required: enforces completeness of knowledge artifact
"""

TOOLS_CRYSTALLIZE = [
    {
        "name": "generate_knowledge_document",
        "description": """Produce the final knowledge artifact — a comprehensive 10-section markdown document.

This tool is called when the user signals 'Knowledge Complete' (equivalent to 'Problem Resolved' in GhostPath).

You MUST include all 10 sections:
1. Executive Summary — 2-3 paragraphs distilling the entire investigation
2. Problem Analysis — The original problem, reframed with new understanding
3. Methodology — How you conducted the investigation (web research, claim generation, verification cycles)
4. Key Discoveries — The breakthrough insights that emerged
5. Knowledge Claims — All accepted/qualified claims with their evidence (numbered, with graph relationships noted)
6. Knowledge Graph Description — Visual description of the graph structure (nodes, edges, clusters)
7. Rejected Paths — Negative knowledge: what didn't work and why
8. Implementation Implications — How to apply this knowledge in practice
9. Open Questions — What remains unknown or uncertain
10. Evolutionary Journey — How understanding evolved across rounds (meta-analysis)

Write in clear, direct prose. Focus on WHY each claim matters, not just WHAT it states. Include URLs for all evidence.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title (concise, < 80 chars)"
                },
                "executive_summary": {
                    "type": "string",
                    "description": "Section 1: High-level synthesis (2-3 paragraphs)"
                },
                "problem_analysis": {
                    "type": "string",
                    "description": "Section 2: Original problem + reframed understanding"
                },
                "methodology": {
                    "type": "string",
                    "description": "Section 3: Investigation approach (tools, cycles, reasoning)"
                },
                "key_discoveries": {
                    "type": "string",
                    "description": "Section 4: Breakthrough insights that emerged"
                },
                "knowledge_claims": {
                    "type": "string",
                    "description": "Section 5: All validated claims with evidence (numbered, with graph edges noted)"
                },
                "knowledge_graph_description": {
                    "type": "string",
                    "description": "Section 6: Structure of the knowledge graph (nodes, edges, clusters, convergence points)"
                },
                "rejected_paths": {
                    "type": "string",
                    "description": "Section 7: Negative knowledge — rejected claims and why they failed"
                },
                "implementation_implications": {
                    "type": "string",
                    "description": "Section 8: How to apply this knowledge in practice"
                },
                "open_questions": {
                    "type": "string",
                    "description": "Section 9: What remains unknown, uncertain, or requires further investigation"
                },
                "evolutionary_journey": {
                    "type": "string",
                    "description": "Section 10: How understanding evolved across rounds — meta-analysis of the investigation process"
                }
            },
            "required": [
                "title",
                "executive_summary",
                "problem_analysis",
                "methodology",
                "key_discoveries",
                "knowledge_claims",
                "knowledge_graph_description",
                "rejected_paths",
                "implementation_implications",
                "open_questions",
                "evolutionary_journey"
            ]
        }
    }
]
