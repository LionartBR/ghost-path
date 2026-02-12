"""Session Schemas — Pydantic models with field-level validation for API boundaries.

Invariants:
    - SessionCreate.problem: 10–10000 chars, stripped, non-empty
    - PremiseScore.score: 0.0–10.0, rounded to 1 decimal
    - UserInput cross-validates: scores requires 3 items, resolved requires winner
    - WinnerInfo.index: 0–2 (exactly 3 premises per round)

Design Decisions:
    - Literal type for UserInput.type over str enum: Pydantic handles validation natively
    - field_validator for side-effect-free transforms (strip, round) — keeps models pure
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
    id: UUID
    problem: str
    status: str


class PremiseScoreInput(BaseModel):
    """Score for a single premise — enforces 0.0–10.0 range."""
    premise_title: str = Field(min_length=1, max_length=200)
    score: float = Field(ge=0.0, le=10.0)
    comment: str | None = Field(None, max_length=2000)

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 1)


class WinnerInfo(BaseModel):
    """Winning premise — index must be 0, 1, or 2."""
    title: str = Field(min_length=1, max_length=200)
    score: float | None = Field(None, ge=0.0, le=10.0)
    index: int = Field(ge=0, le=2)


class UserInput(BaseModel):
    """User input — uses Literal for type, cross-field validation."""
    type: Literal["scores", "ask_user_response", "resolved"]
    scores: list[PremiseScoreInput] | None = None
    response: str | None = Field(None, max_length=5000)
    winner: WinnerInfo | None = None
    raw_text: str | None = Field(None, max_length=10_000)

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "scores":
            if not self.scores or len(self.scores) != 3:
                raise ValueError(
                    "scores input requires exactly 3 premise scores",
                )
        elif self.type == "ask_user_response":
            if not self.response:
                raise ValueError("ask_user_response requires a response")
        elif self.type == "resolved":
            if not self.winner:
                raise ValueError("resolved input requires winner info")
        return self
