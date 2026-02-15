"""Forge State — in-memory enforcement engine for the TRIZ pipeline.

Invariants:
    - Phase transitions are user-initiated (never automatic)
    - All phase gates must pass before transition
    - web_search must precede evidence-dependent tools
    - Max 3 claims per synthesis round, max 5 rounds per session

Design Decisions:
    - In-memory not DB (ADR: hackathon single-process, state loss acceptable)
    - Dict-based not ORM (ADR: speed of access during agent loop)
    - Module-level dict in routes (deliberate exception to no-global-state rule)
"""

from dataclasses import dataclass, field

from app.core.domain_types import Locale, Phase, MAX_ROUNDS_PER_SESSION


@dataclass
class ForgeState:
    """Per-session enforcement state — pure dataclass, no IO."""

    # === Locale (persists across rounds, set at session creation) ===
    locale: Locale = Locale.EN
    locale_confidence: float = 0.0

    # === Phase tracking ===
    current_phase: Phase = Phase.DECOMPOSE
    current_round: int = 0  # 0 = first round, increments on BUILD->SYNTHESIZE

    # === web_search tracking (reset on phase change) ===
    web_searches_this_phase: list[dict] = field(default_factory=list)

    # === Phase 1: Decompose ===
    fundamentals: list[str] = field(default_factory=list)
    state_of_art_researched: bool = False
    assumptions: list[dict] = field(default_factory=list)
    reframings: list[dict] = field(default_factory=list)
    user_suggested_domains: list[str] = field(default_factory=list)

    # === Phase 2: Explore ===
    morphological_box: dict | None = None
    cross_domain_analogies: list[dict] = field(default_factory=list)
    cross_domain_search_count: int = 0
    contradictions: list[dict] = field(default_factory=list)
    adjacent_possible: list[dict] = field(default_factory=list)

    # === Phase 3: Synthesize (per-round, reset on new round) ===
    current_round_claims: list[dict] = field(default_factory=list)  # max 3
    theses_stated: int = 0
    antitheses_searched: set[int] = field(default_factory=set)

    # === Phase 4: Validate ===
    falsification_attempted: set[int] = field(default_factory=set)
    novelty_checked: set[int] = field(default_factory=set)

    # === Phase 5: Build (cumulative across rounds) ===
    knowledge_graph_nodes: list[dict] = field(default_factory=list)
    knowledge_graph_edges: list[dict] = field(default_factory=list)
    negative_knowledge: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    negative_knowledge_consulted: bool = False
    previous_claims_referenced: bool = False

    # === Deep-dive tracking ===
    deep_dive_active: bool = False
    deep_dive_target_claim_id: str | None = None

    # === Pause state ===
    awaiting_user_input: bool = False
    awaiting_input_type: str | None = None

    # === Research archive (cumulative — persists across phases for recall) ===
    # ADR: research_archive stores all Haiku summaries for retrieval via
    # recall_phase_context. Unlike web_searches_this_phase (resets per phase),
    # this is cumulative so the agent can reference past research.
    research_archive: list[dict] = field(default_factory=list)

    # === Research token tracking (informational — does not affect ContextMeter) ===
    research_tokens_used: int = 0

    # === Research directives (ephemeral — user steers agent between iterations) ===
    research_directives: list[dict] = field(default_factory=list)

    # === Cancellation (transient — not persisted to snapshot) ===
    cancelled: bool = False

    # --- Computed properties ---------------------------------------------------

    @property
    def claims_in_round(self) -> int:
        """Number of claims generated this round."""
        return len(self.current_round_claims)

    @property
    def claims_remaining(self) -> int:
        """Slots left in this round's claim buffer."""
        return 3 - self.claims_in_round

    @property
    def has_web_search_this_phase(self) -> bool:
        """Whether any web_search was called in current phase."""
        return len(self.web_searches_this_phase) > 0

    @property
    def starred_analogies(self) -> list[dict]:
        """Analogies the user starred during explore review."""
        return [a for a in self.cross_domain_analogies if a.get("starred")]

    @property
    def selected_reframings(self) -> list[dict]:
        """Reframings the user selected during decompose review."""
        return [r for r in self.reframings if r.get("selected")]

    @property
    def reviewed_assumptions(self) -> list[dict]:
        """Assumptions where the user selected an option."""
        return [a for a in self.assumptions if a.get("selected_option") is not None]

    @property
    def confirmed_assumptions(self) -> list[dict]:
        """Backward-compat alias for reviewed_assumptions."""
        return self.reviewed_assumptions

    @property
    def all_claims_have_antithesis(self) -> bool:
        """Whether every claim in this round has been antithesis-searched."""
        if not self.current_round_claims:
            return False
        return len(self.antitheses_searched) >= len(self.current_round_claims)

    @property
    def all_claims_falsified(self) -> bool:
        """Whether every claim has had falsification attempted."""
        if not self.current_round_claims:
            return False
        return len(self.falsification_attempted) >= len(self.current_round_claims)

    @property
    def all_claims_novelty_checked(self) -> bool:
        """Whether every claim has had novelty checked."""
        if not self.current_round_claims:
            return False
        return len(self.novelty_checked) >= len(self.current_round_claims)

    @property
    def max_rounds_reached(self) -> bool:
        """Whether the session has hit the round limit (rounds 0..MAX-1)."""
        return self.current_round >= MAX_ROUNDS_PER_SESSION - 1

    # === Phase 6: Crystallize ===
    knowledge_document_markdown: str | None = None

    # === Working document (incremental — built across phases, never reset) ===
    working_document: dict[str, str] = field(default_factory=dict)

    # === Document gate (reset per phase — ensures agent captures context) ===
    document_updated_this_phase: bool = False

    # --- Mutation methods --------------------------------------------------------

    def transition_to(self, phase: Phase) -> None:
        """Move to a new phase. Resets web_search tracking and document gate."""
        self.current_phase = phase
        self.web_searches_this_phase = []
        self.document_updated_this_phase = False

    def add_research_directive(
        self, directive_type: str, query: str, domain: str,
    ) -> None:
        """Queue a user research directive for injection."""
        self.research_directives.append({
            "directive_type": directive_type,
            "query": query,
            "domain": domain,
        })

    def consume_research_directives(self) -> list[dict]:
        """Return queued directives and clear the list."""
        directives = self.research_directives
        self.research_directives = []
        return directives

    def record_web_search(self, query: str, summary: str) -> None:
        """Record a web_search call for enforcement tracking."""
        self.web_searches_this_phase.append({
            "query": query, "result_summary": summary,
        })

    def reset_for_new_round(self) -> None:
        """Reset per-round flags. Graph + negative knowledge persist."""
        self.current_round += 1
        self.current_round_claims = []
        self.theses_stated = 0
        self.antitheses_searched = set()
        self.falsification_attempted = set()
        self.novelty_checked = set()
        self.negative_knowledge_consulted = False
        self.previous_claims_referenced = False
        self.web_searches_this_phase = []
