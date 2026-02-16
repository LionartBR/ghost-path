"""ForgeState Snapshot — tests for serialization/deserialization (to_snapshot/from_snapshot).

Invariants:
    - to_snapshot produces a JSON-safe dict (no sets, no enums, no objects)
    - from_snapshot reconstructs an equivalent ForgeState from that dict
    - Roundtrip (to_snapshot -> from_snapshot) preserves all fields
    - Missing keys in snapshot fall back to ForgeState defaults

Design Decisions:
    - Pure tests (no IO, no DB) — snapshot is a core concern
    - Tests cover every field group (phase tracking, claims, graph, etc.)
"""

from app.core.forge_state import ForgeState
from app.core.forge_state_snapshot import forge_state_to_snapshot, forge_state_from_snapshot
from app.core.domain_types import Phase, Locale


# -- Roundtrip -----------------------------------------------------------------

def test_roundtrip_default_state():
    """Default ForgeState survives roundtrip with all fields intact."""
    original = ForgeState()
    snapshot = forge_state_to_snapshot(original)
    restored = forge_state_from_snapshot(snapshot)

    assert restored.current_phase == original.current_phase
    assert restored.current_round == original.current_round
    assert restored.locale == original.locale
    assert restored.fundamentals == original.fundamentals
    assert restored.assumptions == original.assumptions
    assert restored.reframings == original.reframings
    assert restored.morphological_box == original.morphological_box
    assert restored.knowledge_graph_nodes == original.knowledge_graph_nodes
    assert restored.knowledge_graph_edges == original.knowledge_graph_edges
    assert restored.negative_knowledge == original.negative_knowledge
    assert restored.knowledge_document_markdown == original.knowledge_document_markdown


def test_roundtrip_populated_state():
    """Fully populated ForgeState survives roundtrip."""
    state = ForgeState()
    state.current_phase = Phase.VALIDATE
    state.current_round = 2
    state.locale = Locale.PT_BR
    state.locale_confidence = 0.95

    # Phase 1
    state.fundamentals = ["f1", "f2"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": "a1", "source": "s1", "options": ["Agree", "Nuance"], "selected_option": 0}]
    state.reframings = [{"text": "r1", "type": "scope_change", "selected": True}]
    state.user_suggested_domains = ["biology", "music"]

    # Phase 2
    state.morphological_box = {"parameters": [{"name": "p1", "values": ["v1"]}]}
    state.cross_domain_analogies = [{"domain": "biology", "resonated": True}]
    state.cross_domain_search_count = 3
    state.contradictions = [{"property_a": "speed", "property_b": "safety"}]
    state.adjacent_possible = [{"current_capability": "c1"}]

    # Phase 3
    state.current_round_claims = [
        {"claim_text": "claim1", "claim_id": "abc-123", "scores": {"novelty": 0.8}},
    ]
    state.theses_stated = 2
    state.antitheses_searched = {0, 1}

    # Phase 4
    state.falsification_attempted = {0}
    state.novelty_checked = {0, 1}

    # Phase 5
    state.knowledge_graph_nodes = [{"id": "n1", "claim_text": "c1"}]
    state.knowledge_graph_edges = [{"source": "n1", "target": "n2", "type": "supports"}]
    state.negative_knowledge = [{"claim_text": "rejected", "reason": "disproved"}]
    state.gaps = ["gap1", "gap2"]
    state.negative_knowledge_consulted = True
    state.previous_claims_referenced = True

    # Deep-dive
    state.deep_dive_active = True
    state.deep_dive_target_claim_id = "claim-xyz"

    # Phase 6
    state.knowledge_document_markdown = "# Document\nContent here"

    # web_search tracking
    state.web_searches_this_phase = [{"query": "test", "result_summary": "3 results"}]

    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)

    # Phase tracking
    assert restored.current_phase == Phase.VALIDATE
    assert restored.current_round == 2
    assert restored.locale == Locale.PT_BR
    assert restored.locale_confidence == 0.95

    # Phase 1
    assert restored.fundamentals == ["f1", "f2"]
    assert restored.state_of_art_researched is True
    assert restored.assumptions == [{"text": "a1", "source": "s1", "options": ["Agree", "Nuance"], "selected_option": 0}]
    assert restored.reframings == [{"text": "r1", "type": "scope_change", "selected": True}]
    assert restored.user_suggested_domains == ["biology", "music"]

    # Phase 2
    assert restored.morphological_box == {"parameters": [{"name": "p1", "values": ["v1"]}]}
    assert restored.cross_domain_analogies == [{"domain": "biology", "resonated": True}]
    assert restored.cross_domain_search_count == 3
    assert restored.contradictions == [{"property_a": "speed", "property_b": "safety"}]
    assert restored.adjacent_possible == [{"current_capability": "c1"}]

    # Phase 3
    assert restored.current_round_claims == state.current_round_claims
    assert restored.theses_stated == 2
    assert restored.antitheses_searched == {0, 1}

    # Phase 4
    assert restored.falsification_attempted == {0}
    assert restored.novelty_checked == {0, 1}

    # Phase 5
    assert restored.knowledge_graph_nodes == [{"id": "n1", "claim_text": "c1"}]
    assert restored.knowledge_graph_edges == [{"source": "n1", "target": "n2", "type": "supports"}]
    assert restored.negative_knowledge == [{"claim_text": "rejected", "reason": "disproved"}]
    assert restored.gaps == ["gap1", "gap2"]
    assert restored.negative_knowledge_consulted is True
    assert restored.previous_claims_referenced is True

    # Deep-dive
    assert restored.deep_dive_active is True
    assert restored.deep_dive_target_claim_id == "claim-xyz"

    # Phase 6
    assert restored.knowledge_document_markdown == "# Document\nContent here"

    # web_search
    assert restored.web_searches_this_phase == [{"query": "test", "result_summary": "3 results"}]


# -- Snapshot format -----------------------------------------------------------

def test_to_snapshot_produces_json_safe_dict():
    """Snapshot must contain only JSON-serializable types (no sets, no enums)."""
    import json

    state = ForgeState()
    state.antitheses_searched = {0, 1, 2}
    state.falsification_attempted = {0}
    state.novelty_checked = {1, 2}
    state.current_phase = Phase.BUILD

    snapshot = forge_state_to_snapshot(state)

    # Must serialize to JSON without error
    json_str = json.dumps(snapshot)
    assert isinstance(json_str, str)

    # Sets serialized as sorted lists
    assert isinstance(snapshot["antitheses_searched"], list)
    assert sorted(snapshot["antitheses_searched"]) == [0, 1, 2]
    assert isinstance(snapshot["falsification_attempted"], list)
    assert isinstance(snapshot["novelty_checked"], list)

    # Enums serialized as values
    assert snapshot["current_phase"] == "build"
    assert isinstance(snapshot["current_phase"], str)


def test_to_snapshot_captures_all_dataclass_fields():
    """Every non-computed field in ForgeState must appear in the snapshot."""
    from dataclasses import fields as dc_fields

    state = ForgeState()
    snapshot = forge_state_to_snapshot(state)

    # Get all dataclass field names (excludes @property)
    field_names = {f.name for f in dc_fields(ForgeState)}

    # Exclude transient fields that don't need persistence
    transient = {"awaiting_user_input", "awaiting_input_type", "cancelled"}
    expected = field_names - transient

    for field_name in expected:
        assert field_name in snapshot, f"Field '{field_name}' missing from snapshot"


# -- from_snapshot edge cases --------------------------------------------------

def test_from_snapshot_with_empty_dict_returns_defaults():
    """Empty dict produces a valid ForgeState with all defaults."""
    restored = forge_state_from_snapshot({})

    assert restored.current_phase == Phase.DECOMPOSE
    assert restored.current_round == 0
    assert restored.fundamentals == []
    assert restored.assumptions == []
    assert restored.antitheses_searched == set()
    assert restored.knowledge_graph_nodes == []
    assert restored.knowledge_document_markdown is None


def test_from_snapshot_with_partial_dict_fills_defaults():
    """Snapshot with some fields fills the rest from defaults."""
    restored = forge_state_from_snapshot({
        "current_phase": "explore",
        "current_round": 1,
        "fundamentals": ["f1"],
    })

    assert restored.current_phase == Phase.EXPLORE
    assert restored.current_round == 1
    assert restored.fundamentals == ["f1"]
    # Defaults for missing fields
    assert restored.assumptions == []
    assert restored.morphological_box is None
    assert restored.knowledge_graph_nodes == []


def test_from_snapshot_restores_sets_from_lists():
    """Lists in snapshot are converted back to sets for set-typed fields."""
    restored = forge_state_from_snapshot({
        "antitheses_searched": [0, 2, 1],
        "falsification_attempted": [0],
        "novelty_checked": [1, 2],
    })

    assert restored.antitheses_searched == {0, 1, 2}
    assert isinstance(restored.antitheses_searched, set)
    assert restored.falsification_attempted == {0}
    assert isinstance(restored.falsification_attempted, set)
    assert restored.novelty_checked == {1, 2}
    assert isinstance(restored.novelty_checked, set)


def test_from_snapshot_migrates_old_starred_key_to_resonated():
    """Old snapshots with 'starred' key in analogies migrate to 'resonated'."""
    restored = forge_state_from_snapshot({
        "cross_domain_analogies": [
            {"domain": "biology", "starred": True},
            {"domain": "physics", "starred": False},
        ],
    })
    assert restored.cross_domain_analogies[0].get("resonated") is True
    assert restored.cross_domain_analogies[1].get("resonated") is False
    assert "starred" not in restored.cross_domain_analogies[0]
    assert "starred" not in restored.cross_domain_analogies[1]
    assert len(restored.resonant_analogies) == 1


# -- Computed properties survive roundtrip ------------------------------------

def test_computed_properties_correct_after_roundtrip():
    """Computed properties should work correctly on restored state."""
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": "c1"}, {"claim_text": "c2"}, {"claim_text": "c3"},
    ]
    state.antitheses_searched = {0, 1, 2}
    state.current_round = 5  # MAX_ROUNDS_PER_SESSION (exceeded)

    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)

    assert restored.claims_in_round == 3
    assert restored.claims_remaining == 0
    assert restored.all_claims_have_antithesis is True
    assert restored.max_rounds_reached is True


# -- user_suggested_domains ---------------------------------------------------

def test_roundtrip_includes_user_suggested_domains():
    state = ForgeState()
    state.user_suggested_domains = ["biology", "physics"]
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert restored.user_suggested_domains == ["biology", "physics"]


def test_from_snapshot_ignores_removed_user_added_fields():
    """Old snapshots with user_added_* fields don't crash — graceful degradation."""
    old_snapshot = {
        "user_added_assumptions": ["old"],
        "user_added_reframings": ["old"],
        "user_added_claims": ["old"],
    }
    state = forge_state_from_snapshot(old_snapshot)
    assert state.user_suggested_domains == []


# -- research_archive --------------------------------------------------------

def test_roundtrip_includes_research_archive():
    state = ForgeState()
    state.research_archive = [
        {"query": "TRIZ", "purpose": "state_of_art", "summary": "Found", "sources": []},
    ]
    state.research_tokens_used = 150
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert len(restored.research_archive) == 1
    assert restored.research_archive[0]["query"] == "TRIZ"
    assert restored.research_tokens_used == 150


def test_from_snapshot_defaults_research_archive():
    """Old snapshots without research_archive default to empty list."""
    snapshot = {"current_phase": "decompose", "current_round": 0}
    restored = forge_state_from_snapshot(snapshot)
    assert restored.research_archive == []
    assert restored.research_tokens_used == 0


# -- working_document --------------------------------------------------------

def test_roundtrip_working_document():
    """Working document sections survive roundtrip."""
    state = ForgeState()
    state.working_document = {
        "core_insight": "The main discovery...",
        "problem_context": "Why this matters...",
    }
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert restored.working_document == {
        "core_insight": "The main discovery...",
        "problem_context": "Why this matters...",
    }


def test_roundtrip_document_updated_flag():
    """document_updated_this_phase survives roundtrip."""
    state = ForgeState()
    state.document_updated_this_phase = True
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert restored.document_updated_this_phase is True


def test_empty_snapshot_restores_empty_working_document():
    """Old snapshots without working_document default to empty dict."""
    snapshot = {"current_phase": "decompose", "current_round": 0}
    restored = forge_state_from_snapshot(snapshot)
    assert restored.working_document == {}
    assert restored.document_updated_this_phase is False
