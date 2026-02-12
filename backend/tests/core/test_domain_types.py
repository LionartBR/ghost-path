"""Domain Types — verifies rich type definitions and enum values.

Tests:
    - NewType wrappers exist and are callable
    - Enums have expected members and serialize to string
    - AnalysisGate has exactly 3 members (gates are the invariant)
"""

from uuid import uuid4

from app.core.domain_types import (
    SessionId, RoundId, PremiseId,
    PremiseScore, ObviousnessScore, MutationStrength,
    SessionStatus, AnalysisGate, PremiseType, ToolCategory,
)


def test_identity_types_wrap_uuid():
    uid = uuid4()
    sid = SessionId(uid)
    rid = RoundId(uid)
    pid = PremiseId(uid)
    assert sid == uid
    assert rid == uid
    assert pid == uid


def test_value_types_wrap_float():
    assert PremiseScore(7.5) == 7.5
    assert ObviousnessScore(0.3) == 0.3
    assert MutationStrength(0.8) == 0.8


def test_session_status_has_four_states():
    assert set(SessionStatus) == {
        SessionStatus.CREATED,
        SessionStatus.ACTIVE,
        SessionStatus.RESOLVED,
        SessionStatus.CANCELLED,
    }


def test_analysis_gate_has_exactly_three_gates():
    assert len(AnalysisGate) == 3
    assert AnalysisGate.DECOMPOSE.value == "decompose_problem"
    assert AnalysisGate.CONVENTIONAL.value == "map_conventional_approaches"
    assert AnalysisGate.AXIOMS.value == "extract_hidden_axioms"


def test_premise_type_has_four_types():
    assert set(PremiseType) == {
        PremiseType.INITIAL,
        PremiseType.CONSERVATIVE,
        PremiseType.RADICAL,
        PremiseType.COMBINATION,
    }


def test_enums_serialize_to_string():
    assert str(SessionStatus.CREATED) == "SessionStatus.CREATED"
    assert SessionStatus.CREATED.value == "created"
    assert AnalysisGate.DECOMPOSE.value == "decompose_problem"


def test_tool_category_has_five_categories():
    assert len(ToolCategory) == 5
