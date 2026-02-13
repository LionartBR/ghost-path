# TRIZ

Knowledge Creation Engine. Users submit a problem, the agent decomposes, explores, synthesizes, validates, builds a knowledge graph, and crystallizes findings. 6-phase pipeline with dialectical method (thesis -> antithesis -> synthesis). Final Knowledge Document generated on resolution.

## Stack
- **Backend**: Python 3.13, FastAPI 0.128, Uvicorn 0.40, SQLAlchemy 2.0, Alembic 1.18, PostgreSQL 18
- **Frontend**: React 19, TypeScript 5.9, Vite 7, Tailwind 4
- **LLM**: Claude Opus 4.6 via Anthropic Tool Use (native function calling)
- **Streaming**: SSE | **Infra**: Docker + Docker Compose

## Running Tests

All commands run from the repo root. Use **forward slashes** in paths — Windows Python/pytest handles them correctly; backslashes are interpreted as escape sequences and fail silently.

```bash
# All core tests (pure domain logic, no DB needed)
cd backend && python -m pytest tests/core/ -v

# A single test file
cd backend && python -m pytest tests/core/test_forge_state.py -v

# A single test by name
cd backend && python -m pytest tests/core/ -k "test_initial_phase_is_decompose" -v

# All tests (core + services — services require DB)
cd backend && python -m pytest tests/ -v
```

> **Note**: Do NOT use backslash paths like `tests\core\` — pytest on Windows silently collects 0 tests. Always use `tests/core/`.

## Reference Documents
- Full spec with code examples: `ghostpath-spec-v4.md`
- Architecture philosophy: `exma-manual.md`

## ExMA — Architecture Rules

Full rationale in `exma-manual.md`. These are **mandatory constraints**, not suggestions.

### Functional Core, Imperative Shell
Pure domain logic in core — no IO, no `async`, no DB, no Anthropic calls. Impure orchestration in shell — FastAPI routes, DB access, SSE streaming, API calls.
- `check_decompose_complete(state) -> str | None` → **core** (pure, deterministic)
- `agent_runner(session, message, forge_state)` → **shell** (async, calls Claude, writes DB)
- **Rule**: if a domain function needs `async` or receives a repository, it belongs in the shell

**Impureim Sandwich**: every handler follows: read (impure) → process (pure) → write (impure). Never interleave.
```python
async def create_synthesis(self, session, input_data):
    claim = input_data                             # read input
    error = validate_synthesis_prerequisites(       # pure: validate
        self.state, claim_index,
    )
    if error: return error
    self.state.current_round_claims.append(claim)  # write state
    await self.db.commit()                         # impure: persist
```

### Types as Documentation
Use rich types instead of bare primitives. Types are constraints the compiler enforces; comments are wishes.
```python
SessionId = NewType("SessionId", UUID)          # not bare UUID
ClaimId = NewType("ClaimId", UUID)              # not bare UUID

class Phase(str, Enum):
    DECOMPOSE = "decompose"
    EXPLORE = "explore"
    SYNTHESIZE = "synthesize"
    VALIDATE = "validate"
    BUILD = "build"
    CRYSTALLIZE = "crystallize"

class ClaimType(str, Enum):
    THESIS = "thesis"
    ANTITHESIS = "antithesis"
    SYNTHESIS = "synthesis"
```

### Module Header Template
Every Python file must start with:
```python
"""Phase Transition Enforcement — validates conditions for advancing between phases.

Invariants:
    - Cannot explore without decompose complete (fundamentals + state of art + assumptions + reframings)
    - Cannot synthesize without explore complete (morphological box + cross-domain + contradictions)
    - web_search must precede evidence-dependent tools

Design Decisions:
    - Phase gates checked via ForgeState (in-memory) not DB query (ADR: hackathon speed)
"""
```

### Protocols at Boundaries
Core never imports from shell. Dependencies always point inward. Use `Protocol` (typing) at boundaries:
```python
class ClaimRepository(Protocol):
    async def save(self, claim: KnowledgeClaim) -> None: ...
    async def list_by_session(self, session_id: SessionId) -> list[KnowledgeClaim]: ...
```

### Anti-Patterns (Enforced)
- **No convention-over-config**: register routes and handlers explicitly. No auto-discovery, no behavior inferred from file names
- **No deep inheritance**: prefer composition and `Protocol`. No `BaseToolHandler` hierarchies
- **No implicit global state**: inject dependencies via function parameters or constructor. Exception: `_forge_states` dict (see ADR below)
- **No god objects**: max ~7 methods per class. Handlers split by phase (1-4 methods each) with explicit dispatch

### Additional Rules
- **Locality**: max 3-4 files to understand a feature
- **Intent-revealing names**: `enforce_gates.py`, `score_premise.py` — NOT `helpers.py`, `utils.py`
- **Test names as behavior specs**: `test_rejects_premise_generation_before_all_gates_pass`, never `test_1`
- **ADR inline**: if you chose A over B, document why as a comment near the code

### Hard Limits

| Metric | Limit |
|---|---|
| Cyclomatic complexity / function | < 10 |
| Nesting depth | < 4 |
| Lines / function | < 50 |
| Lines / file | 200-400 |
| Imports (fan-out) / file | < 10 |
| Line length | < 120 chars |

## TDD — Test-Driven Development (Mandatory)

Tests are written **before or alongside** implementation, never after. No code is considered done without its corresponding test.

### Workflow
1. Write a failing test that describes the expected behavior
2. Write the minimum code to make it pass
3. Refactor while keeping tests green

### Backend: pytest + pytest-asyncio

**Pure core functions** — test directly, no mocks needed:
```python
# tests/core/test_forge_state.py
def test_initial_phase_is_decompose():
    state = ForgeState()
    assert state.current_phase == Phase.DECOMPOSE

def test_claims_remaining_zero_when_full():
    state = ForgeState()
    for i in range(3):
        state.current_round_claims.append({"claim_text": f"C{i}"})
    assert state.claims_remaining == 0

def test_reset_clears_round_claims():
    state = ForgeState()
    state.current_round_claims.append({"claim_text": "C1"})
    state.negative_knowledge_consulted = True
    state.reset_for_new_round()
    assert state.current_round_claims == []
    assert state.negative_knowledge_consulted is False

# tests/core/test_enforce_phases.py — pure phase validation, no mocks
def test_decompose_fails_without_fundamentals():
    state = ForgeState()
    error = check_decompose_complete(state)
    assert error is not None
    assert "fundamentals" in error.lower()

def test_web_search_fails_without_search_for_antithesis():
    state = ForgeState()
    error = check_web_search(state, "antithesis")
    assert error is not None

# tests/core/test_enforce_claims.py — pure claim validation, no mocks
def test_antithesis_fails_when_not_searched():
    state = ForgeState()
    state.current_round_claims.append({"claim_text": "C1"})
    error = check_antithesis_exists(state, 0)
    assert error is not None

def test_claim_limit_fails_at_3():
    state = ForgeState()
    for i in range(3):
        state.current_round_claims.append({"claim_text": f"C{i}"})
    error = check_claim_limit(state)
    assert error is not None
```

**Shell functions** (handlers, routes, agent runner) — use async fixtures with test DB:
```python
# tests/services/test_tool_dispatch.py
@pytest.mark.asyncio
async def test_dispatch_routes_to_correct_handler(db_session):
    state = ForgeState()
    dispatch = ToolDispatch(db_session, state)
    result = await dispatch.execute("get_session_status", session, {})
    assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_dispatch_returns_error_for_unknown_tool(db_session):
    state = ForgeState()
    dispatch = ToolDispatch(db_session, state)
    result = await dispatch.execute("nonexistent_tool", session, {})
    assert result["error_code"] == "UNKNOWN_TOOL"
```

### Frontend: Vitest

Component behavior tests, not implementation details:
```typescript
// src/components/__tests__/DecomposeReview.test.tsx
test("requires selecting at least one reframing before submit", () => { ... });
test("allows adding custom assumptions", () => { ... });

// src/hooks/__tests__/useAgentStream.test.ts
test("dispatches review_decompose event to render decompose review UI", () => { ... });
test("dispatches review_claims event with claims array", () => { ... });
```

### What MUST be tested
- Every enforcement rule (15 phase gates, web_search gates, claim validation)
- Every per-round reset behavior (ForgeState.reset_for_new_round)
- SSE event dispatch for each of the 15 event types
- `ForgeState` property calculations (`claims_remaining`, `all_claims_have_antithesis`, `max_rounds_reached`)
- API endpoint responses (status codes, body shapes)
- Error paths: what happens when the agent violates a rule

### Test file location
Backend: `backend/tests/` mirroring `app/` structure:
- `tests/core/test_forge_state.py`, `tests/core/test_enforce_phases.py`, `tests/core/test_enforce_claims.py` — pure, no mocks (96 tests)
- `tests/services/test_tool_dispatch.py`, `tests/services/test_handle_*.py`, `tests/services/test_agent_runner.py` — async fixtures with test DB
Frontend: colocated `__tests__/` folders next to the modules they test

## DDD — Domain-Driven Design

### Ubiquitous Language

These terms have precise meaning across all code, tests, API, and UI. Use them consistently — never invent synonyms.

| Domain Term | Meaning | NOT |
|---|---|---|
| **Session** | A complete knowledge-creation interaction from problem submission to crystallization | "conversation", "chat", "thread" |
| **Phase** | One of 6 pipeline stages (decompose, explore, synthesize, validate, build, crystallize) | "step", "gate", "stage" |
| **Claim** | A falsifiable knowledge statement produced via dialectical method (thesis→antithesis→synthesis) | "idea", "premise", "hypothesis" |
| **Round** | A cycle of up to 3 claims through synthesize→validate→build (max 5 rounds per session) | "iteration", "batch", "turn" |
| **ForgeState** | In-memory enforcement engine tracking phase state, claims, web searches per session | "session state", "context" |
| **Assumption** | A hidden presupposition identified by `extract_assumptions` in Phase 1 | "axiom" alone, "belief" |
| **Reframing** | An alternative formulation of the problem (scope_change, entity_question, variable_change, domain_change) | "rephrasing", "rewording" |
| **Contradiction** | Two competing requirements that can't both be satisfied (TRIZ-style) | "conflict", "tension" |
| **Analogy** | A structural mapping from a distant domain to the problem domain | "example", "metaphor" |
| **Evidence** | Web-sourced fact (URL + summary) supporting or contradicting a claim | "proof", "data" |
| **Verdict** | User's epistemic decision on a claim (accept, reject, qualify, merge) | "score", "rating" |
| **Knowledge Graph** | DAG of validated claims connected by typed edges (supports, contradicts, extends, supersedes, depends_on, merged_from) | "tree", "network" |
| **Knowledge Document** | The final 10-section .md artifact generated in Phase 6 (CRYSTALLIZE) | "spec", "report" |
| **Research** | Real-time web search (via Anthropic built-in `web_search`) to ground claims in evidence | "lookup", "google", "browse" |

### Aggregate: Session

`Session` is the aggregate root. All entities are scoped by `session_id`.

```
Session (aggregate root)
├── owns → KnowledgeClaim[] (up to 3 per round, across rounds)
│   └── owns → Evidence[] (web-sourced, supporting/contradicting/contextual)
├── owns → ClaimEdge[] (typed edges in the knowledge graph DAG)
├── owns → ProblemReframing[] (Phase 1 outputs, user selects >= 1)
├── owns → CrossDomainAnalogy[] (Phase 2 outputs, user stars >= 1)
├── owns → Contradiction[] (Phase 2 outputs, TRIZ-style)
├── tracks → ForgeState (in-memory enforcement engine)
└── stores → message_history (Anthropic conversation for resumption)
```

Rules:
- Never create a `KnowledgeClaim` without a `Session`
- Never query claims directly by ID across sessions — always scope by `session_id`
- `ForgeState` is the domain's enforcement engine — it holds the invariants, not the DB
- Phase transitions are user-initiated (never automatic) via review SSE events

### Value Objects vs Entities

**Entities** (have identity, persisted):
- `Session` (UUID), `KnowledgeClaim` (UUID), `Evidence` (UUID), `ClaimEdge` (UUID)
- `ProblemReframing` (UUID), `CrossDomainAnalogy` (UUID), `Contradiction` (UUID)

**Value Objects** (no identity, defined by content):
- `SessionId`, `ClaimId`, `EvidenceId`, `EdgeId`, `ReframingId`, `AnalogyId`, `ContradictionId`
- `Phase`, `SessionStatus`, `ClaimStatus`, `ClaimType`, `ClaimConfidence`
- `EvidenceType`, `EdgeType`, `VerdictType`, `ReframingType`, `SemanticDistance`

### Domain Events (for internal communication)

These map to SSE events emitted to the frontend. Phase reviews pause the agent loop:
- `review_decompose` — Phase 1 done: user reviews fundamentals, assumptions, reframings
- `review_explore` — Phase 2 done: user reviews morphological box, analogies, contradictions
- `review_claims` — Phase 3 done: user reviews up to 3 claims with evidence
- `review_verdicts` — Phase 4 done: user renders verdicts (accept/reject/qualify/merge)
- `review_build` — Phase 5 done: user decides continue/deep-dive/resolve/add-insight
- `knowledge_document` — Phase 6 done: final Knowledge Document generated

## Architecture: Layered with Pure Core (ADR)

The spec uses layered structure, not vertical slices. This is a deliberate hackathon trade-off: the spec's code examples, imports, and directory structure all assume layers. Follow the spec.

The **core layer** is pure (no IO, no async, no DB) — it contains domain types, enforcement rules, protocols, and session state. The **shell layer** (services, routes, infrastructure) orchestrates IO around pure core functions following the Impureim Sandwich.

```
backend/app/
├── main.py
├── config.py
│
│   ┌─── CORE (pure: no IO, no async, no DB) ──────────────────┐
├── core/
│   ├── domain_types.py            # Rich types: SessionId, ClaimId, Phase, enums
│   ├── repository_protocols.py    # Boundary contracts: ClaimRepository, SessionRepository
│   ├── enforce_phases.py          # Phase transition validators (Rules #1,#2,#4,#9-#15)
│   ├── enforce_claims.py          # Claim validation (Rules #3,#5-#8)
│   ├── forge_state.py             # ForgeState dataclass (in-memory enforcement engine)
│   └── errors.py                  # TrizError hierarchy (15 enforcement error classes)
│   └─────────────────────────────────────────────────────────────┘
│
│   ┌─── SHELL (impure: IO, async, DB, external APIs) ─────────┐
├── infrastructure/
│   ├── anthropic_client.py        # Resilient Anthropic wrapper (retry/backoff/1M context)
│   ├── database.py                # DB session manager (pool/rollback/health)
│   └── observability.py           # Structured JSON logging
├── db/
│   ├── base.py                    # SQLAlchemy Base
│   └── session.py                 # async session factory
├── models/
│   ├── session.py                 # Session ORM (aggregate root)
│   ├── knowledge_claim.py         # KnowledgeClaim ORM (thesis/antithesis/synthesis)
│   ├── evidence.py                # Evidence ORM (web-sourced, typed)
│   ├── claim_edge.py              # ClaimEdge ORM (knowledge graph DAG edges)
│   ├── problem_reframing.py       # ProblemReframing ORM (Phase 1)
│   ├── cross_domain_analogy.py    # CrossDomainAnalogy ORM (Phase 2)
│   ├── contradiction.py           # Contradiction ORM (Phase 2, TRIZ-style)
│   └── tool_call.py               # ToolCall ORM (logging)
├── schemas/
│   ├── session.py                 # SessionCreate, SessionResponse, UserInput (5 types)
│   ├── agent.py                   # SSE event data shapes
│   └── graph.py                   # Knowledge Graph API response (React Flow format)
├── api/routes/
│   ├── health.py                  # Health/readiness probes
│   ├── session_lifecycle.py       # Session CRUD + ForgeState management
│   ├── session_agent_stream.py    # SSE streaming, user-input, document download
│   └── knowledge_graph.py         # GET graph in React Flow format
└── services/
    ├── agent_runner.py            # Resilient runner (MAX_ITERATIONS=50, web_search interception)
    ├── tool_dispatch.py           # Explicit routing dict (tool_name → handler)
    ├── handle_decompose.py        # DecomposeHandlers: Phase 1 (4 methods)
    ├── handle_explore.py          # ExploreHandlers: Phase 2 (4 methods)
    ├── handle_synthesize.py       # SynthesizeHandlers: Phase 3 (3 methods)
    ├── handle_validate.py         # ValidateHandlers: Phase 4 (3 methods)
    ├── handle_build.py            # BuildHandlers: Phase 5 (3 methods)
    ├── handle_crystallize.py      # CrystallizeHandlers: Phase 6 (1 method)
    ├── handle_cross_cutting.py    # CrossCuttingHandlers: session status + user insight (2 methods)
    ├── define_decompose_tools.py  # Phase 1 tool schemas (Anthropic format)
    ├── define_explore_tools.py    # Phase 2 tool schemas
    ├── define_synthesize_tools.py # Phase 3 tool schemas
    ├── define_validate_tools.py   # Phase 4 tool schemas
    ├── define_build_tools.py      # Phase 5 tool schemas
    ├── define_crystallize_tools.py# Phase 6 tool schemas
    ├── define_cross_cutting_tools.py # Cross-cutting tool schemas
    ├── tools_registry.py          # ALL_TOOLS = flat list (20 custom + 1 web_search)
    └── system_prompt.py           # AGENT_SYSTEM_PROMPT constant
│   └─────────────────────────────────────────────────────────────┘

frontend/src/
├── api/client.ts                  # HTTP + SSE client for TRIZ backend
├── types/index.ts                 # TypeScript domain types (mirrors backend)
├── hooks/
│   ├── useAgentStream.ts          # SSE consumer, dispatches 15 event types
│   ├── useSession.ts              # Session CRUD hook
│   └── useContextUsage.ts         # Token usage tracking
├── components/
│   ├── ProblemInput.tsx           # Problem submission form
│   ├── PhaseTimeline.tsx          # 6-phase progress indicator
│   ├── DecomposeReview.tsx        # Phase 1 review: assumptions, reframings
│   ├── ExploreReview.tsx          # Phase 2 review: morphological box, analogies, contradictions
│   ├── ClaimReview.tsx            # Phase 3 review: claims with evidence
│   ├── ClaimCard.tsx              # Single claim display with evidence
│   ├── VerdictPanel.tsx           # Phase 4: accept/reject/qualify/merge per claim
│   ├── BuildDecision.tsx          # Phase 5: continue/deep-dive/resolve/add-insight
│   ├── KnowledgeGraph.tsx         # React Flow DAG visualization
│   ├── KnowledgeDocument.tsx      # Phase 6: final document display
│   ├── ContextMeter.tsx           # Token usage bar (1M limit)
│   ├── AgentActivity.tsx          # Agent text + tool call log
│   ├── EvidencePanel.tsx          # Evidence list with URLs
│   └── UserInsightForm.tsx        # User-contributed insight form
└── pages/
    ├── HomePage.tsx               # Problem input + session list
    ├── SessionPage.tsx            # 6-phase session UI with graph sidebar
    └── ReportPage.tsx             # Standalone report view
```

## The 20 Custom Tools + 1 Built-in (6 Phases + Cross-Cutting + Anthropic)

### Phase 1: DECOMPOSE (4 tools)
| Tool | Purpose |
|---|---|
| `decompose_to_fundamentals` | Break problem into irreducible elements |
| `map_state_of_art` | Research current state of art. **Requires `web_search` first (Rule #12)** |
| `extract_assumptions` | Identify hidden assumptions (>= 3 required) |
| `reframe_problem` | Generate alternative problem formulations (>= 3 required, user selects >= 1) |

### Phase 2: EXPLORE (4 tools)
| Tool | Purpose |
|---|---|
| `build_morphological_box` | Build parameter space for solution exploration |
| `search_cross_domain` | Find structural analogies from distant domains. **Requires `web_search` first (Rule #13)**. >= 2 required |
| `identify_contradictions` | Find TRIZ-style competing requirements (>= 1 required) |
| `map_adjacent_possible` | Map what's just beyond current capabilities |

### Phase 3: SYNTHESIZE (3 tools, max 3 claims per round)
| Tool | Purpose |
|---|---|
| `state_thesis` | State a knowledge direction with web-sourced evidence |
| `find_antithesis` | Search for counter-evidence. **Requires `web_search` first (Rule #14)**. Required before `create_synthesis` (Rule #3) |
| `create_synthesis` | Create a claim that transcends the thesis-antithesis contradiction |

### Phase 4: VALIDATE (3 tools)
| Tool | Purpose |
|---|---|
| `attempt_falsification` | Try to disprove a claim. **Requires `web_search` first (Rule #15)**. Required before scoring (Rule #5) |
| `check_novelty` | Verify claim isn't already known. Required before scoring (Rule #6) |
| `score_claim` | Score claim on novelty, groundedness, falsifiability, significance (0-1 each) |

### Phase 5: BUILD (3 tools)
| Tool | Purpose |
|---|---|
| `add_to_knowledge_graph` | Add accepted/qualified claim to the DAG with typed edges |
| `analyze_gaps` | Identify gaps and convergence locks in the graph |
| `get_negative_knowledge` | Get rejected claims. **Must be called before synthesis in rounds 2+ (Rule #10)** |

### Phase 6: CRYSTALLIZE (1 tool)
| Tool | Purpose |
|---|---|
| `generate_knowledge_document` | Generate final 10-section Knowledge Document. **Pauses agent loop** |

### Cross-Cutting (2 tools)
| Tool | Purpose |
|---|---|
| `get_session_status` | Get current phase, round, token usage, graph stats |
| `submit_user_insight` | Add user-contributed insight to the knowledge graph |

### Built-in Tool (Anthropic server-side)
| Tool | Purpose |
|---|---|
| `web_search` | Real-time web search via Anthropic API (`web_search_20250305`). **No extra API key** — uses same `ANTHROPIC_API_KEY`. $10/1000 searches. **Code-enforced gates**: must precede `map_state_of_art`, `search_cross_domain`, `find_antithesis`, `attempt_falsification` (Rules #12-15). Results intercepted by AgentRunner and recorded in ForgeState for enforcement. |

## Enforcement Rules (15 Code-Enforced Rules)

Pure validation logic lives in `core/enforce_phases.py` and `core/enforce_claims.py`. Tool handlers in `services/handle_*.py` call these pure functions in the impureim sandwich pattern. The agent receives ERROR responses when violated.

### Phase Transition Rules
1. **Decompose → Explore**: Requires fundamentals + state_of_art researched + >= 3 assumptions + >= 3 reframings + user selected >= 1 reframing. ERROR: `DECOMPOSE_INCOMPLETE`
2. **Explore → Synthesize**: Requires morphological box + >= 2 cross-domain searches + >= 1 contradiction + user starred >= 1 analogy. ERROR: `EXPLORE_INCOMPLETE`

### Synthesis Rules
3. **Antithesis before synthesis**: Every `create_synthesis` requires `find_antithesis` first for that claim index. ERROR: `ANTITHESIS_MISSING`
4. **All antitheses before validate**: All claims must have antithesis before advancing to validate. ERROR: `SYNTHESIS_INCOMPLETE`
8. **Claim limit**: Max 3 claims per synthesis round. ERROR: `CLAIM_LIMIT_EXCEEDED`

### Validation Rules
5. **Falsification required**: Every claim needs `attempt_falsification` before `score_claim`. ERROR: `FALSIFICATION_MISSING`
6. **Novelty required**: Every claim needs `check_novelty` before `score_claim`. ERROR: `NOVELTY_UNCHECKED`
7. **Evidence grounding**: Claims without external evidence are flagged. ERROR: `UNGROUNDED_CLAIM`

### Round 2+ Rules
9. **Cumulative**: Must reference >= 1 previous claim via `builds_on_claim_id`. ERROR: `NOT_CUMULATIVE`
10. **Negative knowledge**: Must call `get_negative_knowledge` before synthesis. ERROR: `NEGATIVE_KNOWLEDGE_MISSING`
11. **Max rounds**: Max 5 rounds per session. ERROR: `MAX_ROUNDS_EXCEEDED`

### web_search Gates (ForgeState tracks calls)
12. **`map_state_of_art`** requires `web_search` first. ERROR: `STATE_OF_ART_NOT_RESEARCHED`
13. **`search_cross_domain`** requires `web_search` for the target domain first. ERROR: `CROSS_DOMAIN_NOT_SEARCHED`
14. **`find_antithesis`** requires `web_search` for counter-evidence first. ERROR: `ANTITHESIS_NOT_SEARCHED`
15. **`attempt_falsification`** requires `web_search` to disprove first. ERROR: `FALSIFICATION_NOT_SEARCHED`

### Per-Round Reset (happens on BUILD → SYNTHESIZE transition)
After user chooses "continue", these reset for the next round:
- `current_round_claims` → cleared
- `theses_stated` → 0
- `antitheses_searched` → cleared
- `falsification_attempted` → cleared
- `novelty_checked` → cleared
- `negative_knowledge_consulted` → `False`
- `previous_claims_referenced` → `False`
- `web_searches_this_phase` → cleared
- `current_round` → incremented (starts at 0)
- **Preserved across rounds**: `knowledge_graph_nodes`, `knowledge_graph_edges`, `negative_knowledge`, `gaps`

## API Contract

### Endpoints
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/health/` | Liveness probe (200 if up) |
| `GET` | `/api/v1/health/ready` | Readiness probe (503 if DB unreachable) |
| `POST` | `/api/v1/sessions` | Create session. Body: `{problem: str}`. Returns `{id, problem, status, current_phase, current_round}` |
| `GET` | `/api/v1/sessions` | List sessions with pagination (`?limit=10&offset=0&status=...`) |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session and all associated data |
| `POST` | `/api/v1/sessions/{id}/cancel` | Cancel an active session |
| `GET` | `/api/v1/sessions/{id}/stream` | Initial SSE stream — triggers Phase 1 (DECOMPOSE) |
| `POST` | `/api/v1/sessions/{id}/user-input` | Send user response. Body: `UserInput`. Returns SSE stream |
| `GET` | `/api/v1/sessions/{id}/document` | Download Knowledge Document as .md file |
| `GET` | `/api/v1/sessions/{id}/graph` | Get Knowledge Graph in React Flow format |

### UserInput Types (5 review types)
```python
class UserInput(BaseModel):
    type: Literal["decompose_review", "explore_review", "claims_review", "verdicts", "build_decision"]

    # decompose_review: confirm/reject assumptions, select reframings
    confirmed_assumptions: list[int] | None
    rejected_assumptions: list[int] | None
    added_assumptions: list[str] | None
    selected_reframings: list[int] | None       # >= 1 required
    added_reframings: list[str] | None

    # explore_review: star analogies, suggest domains
    starred_analogies: list[int] | None          # >= 1 required
    suggested_domains: list[str] | None

    # claims_review: per-claim feedback
    claim_feedback: list[ClaimFeedback] | None

    # verdicts: per-claim verdict (accept/reject/qualify/merge)
    verdicts: list[ClaimVerdict] | None

    # build_decision: continue | deep_dive | resolve | add_insight
    decision: Literal["continue", "deep_dive", "resolve", "add_insight"] | None
    deep_dive_claim_id: str | None
    user_insight: str | None
    user_evidence_urls: list[str] | None
```

### SSE Event Types (15 types, emitted by `AgentRunner.run()` + routes)
| Event | Data | When |
|---|---|---|
| `agent_text` | `str` | Agent produces text output |
| `tool_call` | `{tool, input_preview}` | Agent calls a tool |
| `tool_error` | `{tool, error_code, message}` | Tool returned enforcement error |
| `tool_result` | tool output summary | Tool succeeded |
| `review_decompose` | `{fundamentals, assumptions, reframings}` | Phase 1 done — render decompose review UI |
| `review_explore` | `{morphological_box, analogies, contradictions, adjacent}` | Phase 2 done — render explore review UI |
| `review_claims` | `{claims: [...]}` | Phase 3 done — render claims review UI |
| `review_verdicts` | `{claims: [...]}` | Phase 4 done — render verdict UI |
| `review_build` | `{graph, gaps, negative_knowledge, round, max_rounds_reached}` | Phase 5 done — render build decision UI |
| `knowledge_document` | `{markdown: str}` | Phase 6 done — render Knowledge Document |
| `phase_change` | phase name | Phase transition notification |
| `context_usage` | `{tokens_used, tokens_limit, tokens_remaining, usage_percentage}` | After every API call |
| `done` | `{error: bool, awaiting_input: bool}` | Agent turn finished |
| `error` | `{code, message, severity, recoverable}` | Error occurred |

## Agent Runner Loop

`AgentRunner.run()` is an async generator that yields SSE events:

1. Build messages from `session.message_history` + new user message
2. `while iteration < MAX_ITERATIONS (50)`: call `anthropic.messages.create(model, system, tools, messages)`
3. Count tokens: `session.total_tokens_used += input_tokens + output_tokens`
4. Process response blocks: text → yield `agent_text`; tool_use → execute via `ToolDispatch`; server_tool_use/web_search_tool_result → intercept and record in ForgeState
5. If `stop_reason == "pause_turn"` (web_search long-running) → serialize and continue loop
6. If no tool_use blocks → yield `done`, break
7. If pause tool triggered (`generate_knowledge_document`) → save `session.message_history`, yield `done(awaiting_input=True)`, break
8. Otherwise → append assistant + tool_results to messages, continue loop

Key details:
- Uses `ResilientAnthropicClient` with retry/backoff and optional 1M context beta header
- web_search results intercepted: `dispatch.record_web_search(query, summary)` for ForgeState enforcement
- `ToolDispatch` instantiated per-iteration with fresh DB session
- Errors caught per-tool (`_execute_tool_safe`) — never crash the loop
- `TrizError` exceptions yield SSE error events and terminate gracefully

## ForgeState (ADR)

```python
# ADR: ForgeState is in-memory (not DB/Redis)
# Context: hackathon — single-process uvicorn, no multi-worker
# Trade-off: state lost on restart, acceptable for demo
# Implementation: module-level dict in session_lifecycle.py (deliberate exception to no-global-state rule)
_forge_states: dict[UUID, ForgeState] = {}
```

`ForgeState` dataclass tracks per session:
- **Phase tracking**: `current_phase: Phase`, `current_round: int`
- **web_search tracking**: `web_searches_this_phase: list[dict]` (reset on phase change)
- **Phase 1 (Decompose)**: `fundamentals`, `state_of_art_researched`, `assumptions`, `reframings`, `user_added_assumptions`, `user_added_reframings`
- **Phase 2 (Explore)**: `morphological_box`, `cross_domain_analogies`, `cross_domain_search_count`, `contradictions`, `adjacent_possible`
- **Phase 3 (Synthesize)**: `current_round_claims` (max 3), `theses_stated`, `antitheses_searched: set[int]`
- **Phase 4 (Validate)**: `falsification_attempted: set[int]`, `novelty_checked: set[int]`
- **Phase 5 (Build)**: `knowledge_graph_nodes`, `knowledge_graph_edges`, `negative_knowledge`, `gaps`, `negative_knowledge_consulted`, `previous_claims_referenced`
- **Phase 6 (Crystallize)**: `knowledge_document_markdown`
- **Deep-dive**: `deep_dive_active`, `deep_dive_target_claim_id`
- **Pause**: `awaiting_user_input`, `awaiting_input_type`
- **Computed**: `claims_remaining`, `all_claims_have_antithesis`, `all_claims_falsified`, `all_claims_novelty_checked`, `max_rounds_reached`, `starred_analogies`, `selected_reframings`, `confirmed_assumptions`

## Database Models (8 tables)

**Session**: `id` (UUID PK), `problem` (text), `status` (str: decomposing/exploring/synthesizing/validating/building/crystallized/cancelled), `current_phase` (int), `current_round` (int), `message_history` (JSON), `total_tokens_used` (int), `created_at`, `resolved_at`. Relationships: claims, reframings, analogies, contradictions (all cascade delete)

**KnowledgeClaim**: `id` (UUID PK), `session_id` (FK), `claim_text` (text), `claim_type` (thesis/antithesis/synthesis/user_contributed/merged), `thesis_text`, `antithesis_text`, `phase_created` (int), `round_created` (int), `status` (proposed/validated/rejected/qualified/superseded), `confidence` (speculative/emerging/grounded), `falsifiability_condition`, scores (novelty/groundedness/falsifiability/significance as floats 0-1), `rejection_reason`, `user_feedback`, `cross_domain_source`, `morphological_params` (JSON)

**Evidence**: `id` (UUID PK), `claim_id` (FK), `session_id` (FK), `source_url`, `source_title`, `content_summary`, `evidence_type` (supporting/contradicting/contextual), `contributed_by` (agent/user)

**ClaimEdge**: `id` (UUID PK), `session_id` (FK), `source_claim_id` (FK), `target_claim_id` (FK), `edge_type` (supports/contradicts/extends/supersedes/depends_on/merged_from)

**ProblemReframing**: `id` (UUID PK), `session_id` (FK), `original_problem`, `reframing_text`, `reframing_type` (scope_change/entity_question/variable_change/domain_change), `selected` (bool)

**CrossDomainAnalogy**: `id` (UUID PK), `session_id` (FK), `source_domain`, `target_application`, `analogy_description`, `semantic_distance` (near/medium/far), `starred` (bool)

**Contradiction**: `id` (UUID PK), `session_id` (FK), `property_a`, `property_b`, `description`, `resolution_direction`

**ToolCall**: `id` (UUID PK), `session_id` (FK), `tool_name`, `tool_input` (JSON), `tool_output` (JSON), `error_code`

## Agent System Prompt

Lives in `services/system_prompt.py`. Key aspects:
- Identity: "You are TRIZ, a Knowledge Creation Engine"
- Defines the 6-phase pipeline with explicit tool lists per phase
- All 15 enforcement rules documented with error_code and rationale
- Dialectical method (thesis → antithesis → synthesis) as core pattern
- Falsifiability: every claim must specify a concrete falsifiability condition
- web_search is mandatory and code-enforced (Rules #12-15)
- Examples: good vs bad dialectical reasoning, good vs bad falsifiability conditions
- Communication style: lead with surprising findings, cite sources inline, CLAIM → EVIDENCE → SO WHAT
- On "Knowledge Complete": generate 10-section Knowledge Document via `generate_knowledge_document`

## Environment

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://triz:triz@db:5432/triz
ANTHROPIC_CONTEXT_1M=true
```

### 1M Context Window (Beta)
- **Requires**: Anthropic account at **tier 4** (or custom rate limits)
- **Beta header**: `context-1m-2025-08-07` — sent automatically by `ResilientAnthropicClient` when `ANTHROPIC_CONTEXT_1M=true` (default)
- **Pricing**: prompts > 200K tokens get premium rates (2x input at $10/M, 1.5x output at $37.50/M)
- **Disable**: set `ANTHROPIC_CONTEXT_1M=false` to fall back to 200K context window
- **Implementation**: `ResilientAnthropicClient` routes to `client.beta.messages.create(betas=[...])` when enabled, `client.messages.create()` when disabled

Docker Compose services: `backend` (FastAPI/Uvicorn), `frontend` (Vite dev or nginx), `db` (PostgreSQL 18).

Backend needs CORS configured for frontend origin. Specs saved to `/tmp/triz/specs/{session_id}.md`.
