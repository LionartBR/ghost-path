"""Custom argument validation — response types accept optional user-written arguments.

Invariants:
    - custom_argument is optional (None by default)
    - custom_argument max length is 500 chars
    - custom_argument does NOT affect selected_option validity

Design Decisions:
    - custom_argument replaces added_assumptions/added_reframings/added_claims
    - An argument enriches an existing item rather than creating a new entity
"""

import pytest
from pydantic import ValidationError

from app.schemas.session import (
    AssumptionResponse,
    ReframingResponse,
    AnalogyResponse,
    ClaimResponse,
    UserInput,
)


# --- AssumptionResponse -------------------------------------------------------

def test_assumption_response_accepts_custom_argument():
    resp = AssumptionResponse(assumption_index=0, selected_option=4, custom_argument="My stance")
    assert resp.custom_argument == "My stance"


def test_assumption_response_custom_argument_defaults_to_none():
    resp = AssumptionResponse(assumption_index=0, selected_option=1)
    assert resp.custom_argument is None


def test_custom_argument_max_length_enforced():
    with pytest.raises(ValidationError):
        AssumptionResponse(assumption_index=0, selected_option=0, custom_argument="x" * 501)


# --- ReframingResponse --------------------------------------------------------

def test_reframing_response_accepts_custom_argument():
    resp = ReframingResponse(reframing_index=0, selected_option=4, custom_argument="New perspective")
    assert resp.custom_argument == "New perspective"


# --- AnalogyResponse ----------------------------------------------------------

def test_analogy_response_accepts_custom_argument():
    resp = AnalogyResponse(analogy_index=0, selected_option=3, custom_argument="Connects via X")
    assert resp.custom_argument == "Connects via X"


# --- ClaimResponse ------------------------------------------------------------

def test_claim_response_accepts_custom_argument():
    resp = ClaimResponse(claim_index=0, selected_option=3, custom_argument="Opens direction Y")
    assert resp.custom_argument == "Opens direction Y"


# --- UserInput integration ----------------------------------------------------

def test_decompose_review_validates_without_added_assumptions():
    """added_assumptions removed — custom_argument in responses replaces it."""
    user_input = UserInput(
        type="decompose_review",
        assumption_responses=[AssumptionResponse(assumption_index=0, selected_option=1)],
        reframing_responses=[ReframingResponse(reframing_index=0, selected_option=2)],
    )
    assert user_input.type == "decompose_review"


def test_decompose_review_custom_argument_counts_as_resonance():
    """Reframing with custom_argument (any selected_option) satisfies >= 1 resonance."""
    user_input = UserInput(
        type="decompose_review",
        reframing_responses=[ReframingResponse(
            reframing_index=0, selected_option=0, custom_argument="My view",
        )],
    )
    assert user_input.type == "decompose_review"


def test_claims_review_validates_without_added_claims():
    """added_claims removed — claim_responses alone is sufficient."""
    user_input = UserInput(
        type="claims_review",
        claim_responses=[ClaimResponse(claim_index=0, selected_option=2)],
    )
    assert user_input.type == "claims_review"
