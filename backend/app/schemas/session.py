"""Session Schemas — Pydantic models with field-level validation for API boundaries.

Invariants:
    - SessionCreate.problem: 10-10000 chars, stripped, non-empty
    - UserInput cross-validates fields per type
    - ClaimFeedback and ClaimVerdict enforce valid values

Design Decisions:
    - Literal type for UserInput.type over str enum: Pydantic handles validation natively
    - field_validator for side-effect-free transforms (strip) — keeps models pure
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
from typing import Literal


class SessionCreate(BaseModel):
    """Session creation — validates problem length and whitespace."""
    problem: str = Field(min_length=10, max_length=10_000)
    locale: str | None = Field(
        None, pattern=r"^(en|pt-BR|es|fr|de|zh|ja|ko|it|ru)$",
    )

    @field_validator("problem")
    @classmethod
    def strip_problem(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("problem cannot be empty or whitespace")
        return v


class SessionResponse(BaseModel):
    """Session response — public-facing session data."""
    id: UUID
    problem: str
    status: str
    current_phase: int
    current_round: int
    locale: str = "en"


# --- Claim feedback (Phase 3 review) -----------------------------------------

class AssumptionResponse(BaseModel):
    """Per-assumption user response during decompose_review."""
    assumption_index: int = Field(ge=0)
    selected_option: int = Field(ge=0)
    custom_argument: str | None = Field(None, max_length=500)


class ReframingResponse(BaseModel):
    """Per-reframing user resonance response during decompose_review."""
    reframing_index: int = Field(ge=0)
    selected_option: int = Field(ge=0)
    custom_argument: str | None = Field(None, max_length=500)


class AnalogyResponse(BaseModel):
    """Per-analogy user resonance response during explore_review."""
    analogy_index: int = Field(ge=0)
    selected_option: int = Field(ge=0)
    custom_argument: str | None = Field(None, max_length=500)


class ClaimFeedback(BaseModel):
    """Per-claim user feedback during claims_review (legacy format)."""
    claim_index: int = Field(ge=0)  # upper bound checked by check_claim_index_valid()
    evidence_valid: bool
    counter_example: str | None = Field(None, max_length=2000)
    synthesis_ignores: str | None = Field(None, max_length=2000)
    additional_evidence: str | None = Field(None, max_length=2000)


class ClaimResponse(BaseModel):
    """Per-claim resonance selection during claims_review."""
    claim_index: int = Field(ge=0)
    selected_option: int = Field(ge=0)
    custom_argument: str | None = Field(None, max_length=500)


# --- Claim verdict (Phase 4 review) ------------------------------------------

class ClaimVerdict(BaseModel):
    """Per-claim user verdict during verdicts review."""
    claim_index: int = Field(ge=0)  # upper bound checked by check_claim_index_valid()
    verdict: Literal["accept", "reject", "qualify", "merge"]
    rejection_reason: str | None = Field(None, max_length=2000)
    qualification: str | None = Field(None, max_length=2000)
    merge_with_claim_id: str | None = None

    @model_validator(mode="after")
    def validate_verdict_fields(self):
        if self.verdict == "reject" and not self.rejection_reason:
            raise ValueError("reject verdict requires rejection_reason")
        if self.verdict == "qualify" and not self.qualification:
            raise ValueError("qualify verdict requires qualification")
        if self.verdict == "merge" and not self.merge_with_claim_id:
            raise ValueError("merge verdict requires merge_with_claim_id")
        return self


# --- UserInput (all review types) ---------------------------------------------

class UserInput(BaseModel):
    """User input — handles all 5 review types from the TRIZ pipeline."""
    type: Literal[
        "decompose_review", "explore_review",
        "claims_review", "verdicts", "build_decision",
    ]

    # type == "decompose_review"
    assumption_responses: list[AssumptionResponse] | None = None
    reframing_responses: list[ReframingResponse] | None = None
    selected_reframings: list[int] | None = None  # backward compat

    # type == "explore_review"
    analogy_responses: list[AnalogyResponse] | None = None
    starred_analogies: list[int] | None = None  # backward compat (legacy star-toggle UX)
    suggested_domains: list[str] | None = None
    added_contradictions: list[str] | None = None
    added_parameters: list[dict] | None = None

    # type == "claims_review"
    claim_responses: list[ClaimResponse] | None = None
    claim_feedback: list[ClaimFeedback] | None = None  # backward compat

    # type == "verdicts"
    verdicts: list[ClaimVerdict] | None = None

    # type == "build_decision"
    decision: Literal["continue", "deep_dive", "resolve", "add_insight"] | None = None
    deep_dive_claim_id: str | None = None
    user_insight: str | None = Field(None, max_length=5000)
    user_evidence_urls: list[str] | None = None
    selected_gaps: list[int] | None = None
    continue_direction: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "decompose_review":
            _validate_decompose_review(self)
        elif self.type == "explore_review":
            _validate_explore_review(self)
        elif self.type == "claims_review":
            _validate_claims_review(self)
        elif self.type == "verdicts":
            _validate_verdicts(self)
        elif self.type == "build_decision":
            _validate_build_decision(self)
        return self


# --- Validation helpers -------------------------------------------------------


def _validate_decompose_review(user_input: "UserInput") -> None:
    """Validate decompose_review fields."""
    # ADR: reframing_responses (new) OR selected_reframings (backward compat)
    has_resonance = (
        user_input.reframing_responses
        and any(r.selected_option > 0 for r in user_input.reframing_responses)
    )
    has_custom_arg = (
        user_input.reframing_responses
        and any(r.custom_argument for r in user_input.reframing_responses)
    )
    has_selection = (
        user_input.selected_reframings and len(user_input.selected_reframings) > 0
    )
    if not (has_resonance or has_custom_arg or has_selection):
        raise ValueError(
            "decompose_review requires >= 1 reframing with resonance "
            "(selected_option > 0), custom argument, or >= 1 selected reframing",
        )


def _validate_explore_review(user_input: "UserInput") -> None:
    """Validate explore_review fields."""
    # ADR: analogy_responses (new) OR starred_analogies (legacy backward compat)
    has_resonance = (
        user_input.analogy_responses
        and any(r.selected_option > 0 for r in user_input.analogy_responses)
    )
    has_custom_arg = (
        user_input.analogy_responses
        and any(r.custom_argument for r in user_input.analogy_responses)
    )
    has_legacy = (
        user_input.starred_analogies and len(user_input.starred_analogies) > 0
    )
    if not (has_resonance or has_custom_arg or has_legacy):
        raise ValueError(
            "explore_review requires >= 1 analogy with resonance "
            "(selected_option > 0), custom argument, or >= 1 legacy starred analogy",
        )


def _validate_claims_review(user_input: "UserInput") -> None:
    """Validate claims_review fields."""
    has_responses = (
        user_input.claim_responses and len(user_input.claim_responses) > 0
    )
    has_feedback = (
        user_input.claim_feedback and len(user_input.claim_feedback) > 0
    )
    if not (has_responses or has_feedback):
        raise ValueError(
            "claims_review requires claim_responses or claim_feedback",
        )


def _validate_verdicts(user_input: "UserInput") -> None:
    """Validate verdicts fields."""
    if not user_input.verdicts:
        raise ValueError("verdicts requires verdicts list")


def _validate_build_decision(user_input: "UserInput") -> None:
    """Validate build_decision fields."""
    if not user_input.decision:
        raise ValueError("build_decision requires decision field")
    if user_input.decision == "deep_dive" and not user_input.deep_dive_claim_id:
        raise ValueError("deep_dive requires deep_dive_claim_id")
    if user_input.decision == "add_insight" and not user_input.user_insight:
        raise ValueError("add_insight requires user_insight")
