"""Forge State Snapshot — serialization / deserialization for ForgeState.

Invariants:
    - to_snapshot produces a JSON-safe dict (no sets, no Enums)
    - from_snapshot reconstructs a ForgeState from any valid snapshot dict
    - Missing keys fall back to ForgeState defaults (forward-compatible)

Design Decisions:
    - Extracted from forge_state.py (ADR: ExMA ~7 methods per class)
    - Bulk field mappings keep serialization DRY over 60+ manual assignments
"""

from app.core.domain_types import Locale, Phase
from app.core.forge_state import ForgeState

# Field mappings for snapshot deserialization (ADR: DRY over 60+ manual lines)
_SIMPLE_FIELDS: dict[str, object] = {
    "current_round": 0, "locale_confidence": 0.0,
    "web_searches_this_phase": [], "fundamentals": [],
    "state_of_art_researched": False, "assumptions": [],
    "reframings": [], "user_suggested_domains": [],
    "cross_domain_analogies": [],
    "cross_domain_search_count": 0, "contradictions": [],
    "adjacent_possible": [], "current_round_claims": [],
    "theses_stated": 0, "knowledge_graph_nodes": [],
    "knowledge_graph_edges": [], "negative_knowledge": [],
    "gaps": [], "negative_knowledge_consulted": False,
    "previous_claims_referenced": False, "deep_dive_active": False,
    "awaiting_user_input": False, "research_directives": [],
    "research_archive": [], "research_tokens_used": 0,
    "working_document": {}, "document_updated_this_phase": False,
}
_NULLABLE_FIELDS: tuple[str, ...] = (
    "morphological_box", "deep_dive_target_claim_id",
    "knowledge_document_markdown", "awaiting_input_type",
)
_SET_FIELDS: tuple[str, ...] = (
    "antitheses_searched", "falsification_attempted", "novelty_checked",
)


def _serialize_phase_data(state: ForgeState) -> dict:
    """Serialize phase 1-6 data fields."""
    return {
        # Phase 1
        "fundamentals": state.fundamentals,
        "state_of_art_researched": state.state_of_art_researched,
        "assumptions": state.assumptions,
        "reframings": state.reframings,
        "user_suggested_domains": state.user_suggested_domains,
        # Phase 2
        "morphological_box": state.morphological_box,
        "cross_domain_analogies": state.cross_domain_analogies,
        "cross_domain_search_count": state.cross_domain_search_count,
        "contradictions": state.contradictions,
        "adjacent_possible": state.adjacent_possible,
        # Phase 3
        "current_round_claims": state.current_round_claims,
        "theses_stated": state.theses_stated,
        "antitheses_searched": sorted(state.antitheses_searched),
        # Phase 4
        "falsification_attempted": sorted(state.falsification_attempted),
        "novelty_checked": sorted(state.novelty_checked),
        # Phase 5
        "knowledge_graph_nodes": state.knowledge_graph_nodes,
        "knowledge_graph_edges": state.knowledge_graph_edges,
        "negative_knowledge": state.negative_knowledge,
        "gaps": state.gaps,
        "negative_knowledge_consulted": state.negative_knowledge_consulted,
        "previous_claims_referenced": state.previous_claims_referenced,
        # Phase 6
        "knowledge_document_markdown": state.knowledge_document_markdown,
        # Working document (incremental — built across phases)
        "working_document": state.working_document,
        "document_updated_this_phase": state.document_updated_this_phase,
    }


def forge_state_to_snapshot(state: ForgeState) -> dict:
    """Serialize ForgeState to JSON-safe dict. Pure, no IO.

    Sets are converted to sorted lists; Enums to their .value strings.
    """
    return {
        "current_phase": state.current_phase.value,
        "current_round": state.current_round,
        "locale": state.locale.value,
        "locale_confidence": state.locale_confidence,
        "web_searches_this_phase": state.web_searches_this_phase,
        **_serialize_phase_data(state),
        # Deep-dive
        "deep_dive_active": state.deep_dive_active,
        "deep_dive_target_claim_id": state.deep_dive_target_claim_id,
        # Pause state (persisted for session resume — ADR: reconnect
        # must re-emit the correct review event without re-running agent)
        "awaiting_user_input": state.awaiting_user_input,
        "awaiting_input_type": state.awaiting_input_type,
        # Research directives (ephemeral, but persisted for crash recovery)
        "research_directives": state.research_directives,
        # Research archive (cumulative — Haiku summaries for recall_phase_context)
        "research_archive": state.research_archive,
        "research_tokens_used": state.research_tokens_used,
    }


def forge_state_from_snapshot(data: dict) -> ForgeState:
    """Reconstruct ForgeState from snapshot dict. Pure, no IO.

    Missing keys fall back to ForgeState defaults. Lists are converted
    back to sets for set-typed fields.
    """
    state = ForgeState()
    if not data:
        return state

    # Enum fields (need explicit conversion)
    phase_val = data.get("current_phase")
    if phase_val:
        state.current_phase = Phase(phase_val)
    locale_val = data.get("locale")
    if locale_val:
        state.locale = Locale(locale_val)

    # Bulk restore: simple, nullable, and set fields
    for key, default in _SIMPLE_FIELDS.items():
        setattr(state, key, data.get(key, default))
    for key in _NULLABLE_FIELDS:
        setattr(state, key, data.get(key))
    for key in _SET_FIELDS:
        setattr(state, key, set(data.get(key, [])))

    return state
