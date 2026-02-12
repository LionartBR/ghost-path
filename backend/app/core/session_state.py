"""Session State — in-memory enforcement engine for per-session invariants.

Invariants:
    - All 3 gates (decompose, map_conventional, extract_axioms) must complete before generation
    - Gate results are immutable once completed
    - Buffer holds max 3 premises per round
    - Per-round flags reset on present_round (axiom_challenged, negative_context, buffer)

Design Decisions:
    - In-memory dict, not DB/Redis: single-process uvicorn, hackathon scope (ADR: speed over durability)
    - Dataclass with computed properties: pure, deterministic, testable without mocks
    - AnalysisGate imported from domain_types: single source of truth for gate names
"""

from dataclasses import dataclass, field

from app.core.domain_types import AnalysisGate


@dataclass
class SessionState:
    """Per-session enforcement state — pure dataclass, no IO."""

    # Completed analysis gates
    completed_gates: set[AnalysisGate] = field(default_factory=set)

    # Current round premises (buffer before present_round)
    current_round_buffer: list[dict] = field(default_factory=list)

    # Current round
    current_round_number: int = 0

    # Whether the agent has run obviousness_test on buffer premises
    obviousness_tested: set[int] = field(default_factory=set)

    # Extracted axioms (to validate that challenge_axiom uses real axioms)
    extracted_axioms: list[str] = field(default_factory=list)

    # Whether challenge_axiom has been called (required for radical premises)
    axiom_challenged: bool = False

    # Whether get_negative_context was called this round (required for rounds 2+)
    negative_context_fetched: bool = False

    # User interaction status
    awaiting_user_input: bool = False
    awaiting_input_type: str | None = None

    @property
    def all_gates_satisfied(self) -> bool:
        return {
            AnalysisGate.DECOMPOSE,
            AnalysisGate.CONVENTIONAL,
            AnalysisGate.AXIOMS,
        }.issubset(self.completed_gates)

    @property
    def missing_gates(self) -> list[str]:
        required = {
            AnalysisGate.DECOMPOSE,
            AnalysisGate.CONVENTIONAL,
            AnalysisGate.AXIOMS,
        }
        missing = required - self.completed_gates
        return [g.value for g in missing]

    @property
    def premises_in_buffer(self) -> int:
        return len(self.current_round_buffer)

    @property
    def premises_remaining(self) -> int:
        return 3 - self.premises_in_buffer

    @property
    def all_premises_tested(self) -> bool:
        return len(self.obviousness_tested) == len(self.current_round_buffer)

    def reset_for_next_round(self) -> None:
        """Reset per-round flags after present_round. Pure state mutation."""
        self.current_round_buffer.clear()
        self.obviousness_tested.clear()
        self.axiom_challenged = False
        self.negative_context_fetched = False
