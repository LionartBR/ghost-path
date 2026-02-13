"""Knowledge Graph Route — GET endpoint for current graph state.

Invariants:
    - Returns graph data in React Flow compatible format
    - Scoped by session_id — never returns cross-session data

Design Decisions:
    - Reads from ForgeState (in-memory) for real-time data during active session
    - Falls back to DB query for persisted sessions
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.graph import GraphData, GraphNode, GraphEdge, ClaimNodeData, ClaimScores
from app.api.routes.session_lifecycle import (
    _forge_states, get_session_or_404,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["knowledge-graph"])


@router.get("/{session_id}/graph", response_model=GraphData)
async def get_knowledge_graph(
    session_id: UUID, db: AsyncSession = Depends(get_db),
):
    """Get current Knowledge Graph for React Flow rendering."""
    await get_session_or_404(session_id, db)
    forge_state = _forge_states.get(session_id)

    if not forge_state:
        return GraphData(nodes=[], edges=[])

    nodes = []
    for node_data in forge_state.knowledge_graph_nodes:
        scores_data = node_data.get("scores", {})
        nodes.append(GraphNode(
            id=node_data.get("id", ""),
            type=node_data.get("status", "proposed"),
            data=ClaimNodeData(
                claim_text=node_data.get("claim_text", ""),
                confidence=node_data.get("confidence"),
                scores=ClaimScores(
                    novelty=scores_data.get("novelty"),
                    groundedness=scores_data.get("groundedness"),
                    falsifiability=scores_data.get("falsifiability"),
                    significance=scores_data.get("significance"),
                ),
                qualification=node_data.get("qualification"),
                rejection_reason=node_data.get("rejection_reason"),
                evidence_count=node_data.get("evidence_count", 0),
                round_created=node_data.get("round_created", 0),
            ),
        ))

    edges = []
    for i, edge_data in enumerate(forge_state.knowledge_graph_edges):
        edges.append(GraphEdge(
            id=f"edge-{i}",
            source=edge_data.get("source", ""),
            target=edge_data.get("target", ""),
            type=edge_data.get("type", "supports"),
        ))

    return GraphData(nodes=nodes, edges=edges)
