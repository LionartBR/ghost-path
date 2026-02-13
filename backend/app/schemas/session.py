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


# --- Claim feedback (Phase 3 review) -----------------------------------------

class ClaimFeedback(BaseModel):
    """Per-claim user feedback during claims_review."""
    claim_index: int = Field(ge=0)  # upper bound checked by check_claim_index_valid()
    evidence_valid: bool
    counter_example: str | None = Field(None, max_length=2000)
    synthesis_ignores: str | None = Field(None, max_length=2000)
    additional_evidence: str | None = Field(None, max_length=2000)


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
    confirmed_assumptions: list[int] | None = None
    rejected_assumptions: list[int] | None = None
    added_assumptions: list[str] | None = None
    selected_reframings: list[int] | None = None
    added_reframings: list[str] | None = None

    # type == "explore_review"
    starred_analogies: list[int] | None = None
    suggested_domains: list[str] | None = None
    added_contradictions: list[str] | None = None
    added_parameters: list[dict] | None = None

    # type == "claims_review"
    claim_feedback: list[ClaimFeedback] | None = None

    # type == "verdicts"
    verdicts: list[ClaimVerdict] | None = None

    # type == "build_decision"
    decision: Literal["continue", "deep_dive", "resolve", "add_insight"] | None = None
    deep_dive_claim_id: str | None = None
    user_insight: str | None = Field(None, max_length=5000)
    user_evidence_urls: list[str] | None = None

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "decompose_review":
            has_selection = (
                (self.selected_reframings and len(self.selected_reframings) > 0)
                or (self.added_reframings and len(self.added_reframings) > 0)
            )
            if not has_selection:
                raise ValueError(
                    "decompose_review requires >= 1 selected or added reframing",
                )

        elif self.type == "explore_review":
            has_starred = (
                self.starred_analogies and len(self.starred_analogies) > 0
            )
            if not has_starred:
                raise ValueError("explore_review requires >= 1 starred analogy")

        elif self.type == "claims_review":
            if not self.claim_feedback:
                raise ValueError("claims_review requires claim_feedback list")

        elif self.type == "verdicts":
            if not self.verdicts:
                raise ValueError("verdicts requires verdicts list")

        elif self.type == "build_decision":
            if not self.decision:
                raise ValueError("build_decision requires decision field")
            if self.decision == "deep_dive" and not self.deep_dive_claim_id:
                raise ValueError("deep_dive requires deep_dive_claim_id")
            if self.decision == "add_insight" and not self.user_insight:
                raise ValueError("add_insight requires user_insight")

        return self
