"""Graph Schemas — Pydantic models for Knowledge Graph API responses.

Invariants:
    - GraphData shape matches React Flow expected format
    - Node types correspond to ClaimStatus values
    - Edge types correspond to EdgeType values

Design Decisions:
    - Separate from session schemas: graph data is consumed by React Flow,
      session data is consumed by the REST API (ADR: responsibility separation)
"""

from typing import Literal

from pydantic import BaseModel


class ClaimScores(BaseModel):
    """Agent-computed scores for a knowledge claim."""
    novelty: float | None = None
    groundedness: float | None = None
    falsifiability: float | None = None
    significance: float | None = None


class ClaimNodeData(BaseModel):
    """Data payload for a claim node in React Flow."""
    claim_text: str
    confidence: str | None = None
    scores: ClaimScores = ClaimScores()
    qualification: str | None = None
    rejection_reason: str | None = None
    evidence_count: int = 0
    round_created: int = 0


class GraphNode(BaseModel):
    """A node in the knowledge graph (React Flow format)."""
    id: str
    type: Literal[
        "validated", "proposed", "rejected", "qualified",
        "superseded", "gap", "user_contributed",
    ]
    data: ClaimNodeData


class GraphEdge(BaseModel):
    """An edge in the knowledge graph (React Flow format)."""
    id: str
    source: str
    target: str
    type: Literal[
        "supports", "contradicts", "extends",
        "supersedes", "depends_on", "merged_from",
    ]


class GraphData(BaseModel):
    """Complete knowledge graph data for React Flow rendering."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
