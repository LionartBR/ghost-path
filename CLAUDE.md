# GhostPath

Semi-autonomous agent for evolutionary idea generation. Users submit a problem, the agent analyzes it (mandatory gates), generates 3 non-obvious premises per round, and the user scores them. Repeats until the user marks "Problem Resolved", then a final .md spec is generated.

## Stack
- **Backend**: Python 3.13, FastAPI 0.128, Uvicorn 0.40, SQLAlchemy 2.0, Alembic 1.18, PostgreSQL 18
- **Frontend**: React 19, TypeScript 5.9, Vite 7, Tailwind 4
- **LLM**: Claude Opus 4.6 via Anthropic Tool Use (native function calling)
- **Streaming**: SSE | **Infra**: Docker + Docker Compose

## Reference Documents
- Full spec with code examples: `ghostpath-spec-v4.md`
- Architecture philosophy: `exma-manual.md`

## ExMA — Architecture Rules

Full rationale in `exma-manual.md`. These are **mandatory constraints**, not suggestions.

### Functional Core, Imperative Shell
Pure domain logic in core — no IO, no `async`, no DB, no Anthropic calls. Impure orchestration in shell — FastAPI routes, DB access, SSE streaming, API calls.
- `obviousness_test(premise, context) -> float` → **core** (pure, deterministic)
- `agent_runner(session_id)` → **shell** (async, calls Claude, writes DB)
- **Rule**: if a domain function needs `async` or receives a repository, it belongs in the shell

**Impureim Sandwich**: every handler follows: read (impure) → process (pure) → write (impure). Never interleave.
```python
async def handle_score_premise(session_id, premise_id, score):
    premise = await repo.get(premise_id)        # impure: read
    updated = apply_score(premise, score)        # pure: transform
    next_action = decide_next_step(session)      # pure: decide
    await repo.save(updated)                     # impure: write
```

### Types as Documentation
Use rich types instead of bare primitives. Types are constraints the compiler enforces; comments are wishes.
```python
SessionId = NewType("SessionId", str)          # not bare str
PremiseScore = NewType("PremiseScore", float)  # not bare float

class GateStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"

class ToolName(str, Enum):
    DECOMPOSE_PROBLEM = "decompose_problem"
    MAP_CONVENTIONAL = "map_conventional_approaches"
    EXTRACT_AXIOMS = "extract_hidden_axioms"
```

### Module Header Template
Every Python file must start with:
```python
"""Gate Analysis — enforces mandatory analysis tools before premise generation.

Invariants:
    - All 3 gates (decompose, map_conventional, extract_axioms) must complete before generation
    - Gate results are immutable once completed
    - Gate order does not matter, but all must pass

Design Decisions:
    - Gates checked via SessionState (in-memory) not DB query (ADR: hackathon speed)
"""
```

### Protocols at Boundaries
Core never imports from shell. Dependencies always point inward. Use `Protocol` (typing) at boundaries:
```python
class PremiseRepository(Protocol):
    async def save(self, premise: Premise) -> None: ...
    async def list_by_round(self, round_id: RoundId) -> list[Premise]: ...
```

### Anti-Patterns (Enforced)
- **No convention-over-config**: register routes and handlers explicitly. No auto-discovery, no behavior inferred from file names
- **No deep inheritance**: prefer composition and `Protocol`. No `BaseToolHandler` hierarchies
- **No implicit global state**: inject dependencies via function parameters or constructor. Exception: `_session_states` dict (see ADR below)
- **No god objects**: max ~7 methods per class. `ToolHandlers` is the largest class — if it grows, split by tool category

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
# tests/test_session_state.py
def test_rejects_premise_generation_before_all_gates_pass():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    # only 1 of 3 gates — should fail
    assert not state.all_gates_satisfied
    assert "map_conventional_approaches" in state.missing_gates

def test_buffer_holds_exactly_3_premises_per_round():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
    assert state.premises_remaining == 0

def test_obviousness_score_above_threshold_rejects_premise():
    # score > 0.6 must trigger removal from buffer
    ...

def test_round_reset_clears_buffer_and_flags():
    state = SessionState()
    state.axiom_challenged = True
    state.negative_context_fetched = True
    state.current_round_buffer.append({"title": "P1"})
    # after present_round, everything resets
    ...
```

**Shell functions** (handlers, routes, agent runner) — use async fixtures with test DB:
```python
# tests/test_tool_handlers.py
@pytest.mark.asyncio
async def test_generate_premise_returns_error_when_gates_not_satisfied(db_session):
    state = SessionState()  # no gates completed
    handlers = ToolHandlers(db_session, state)
    result = await handlers.generate_premise(session, {"title": "X", "body": "Y", "premise_type": "initial"})
    assert result["status"] == "error"
    assert result["error_code"] == "GATES_NOT_SATISFIED"

@pytest.mark.asyncio
async def test_present_round_rejects_untested_premises(db_session):
    ...
```

### Frontend: Vitest

Component behavior tests, not implementation details:
```typescript
// src/components/__tests__/RoundView.test.tsx
test("disables Next Round button until all premises are scored", () => { ... });
test("shows winner selection UI when Problem Resolved is clicked", () => { ... });

// src/hooks/__tests__/useAgentStream.test.ts
test("dispatches premises event to render 3 cards", () => { ... });
test("pauses stream on ask_user event and waits for response", () => { ... });
```

### What MUST be tested
- Every enforcement rule (6 gate/buffer/obviousness checks)
- Every per-round reset behavior
- SSE event dispatch for each of the 10 event types
- `SessionState` property calculations (`all_gates_satisfied`, `premises_remaining`, `all_premises_tested`)
- API endpoint responses (status codes, body shapes)
- Error paths: what happens when the agent violates a rule

### Test file location
Backend: `backend/tests/` mirroring `app/` structure (`tests/services/test_tool_handlers.py`, `tests/services/test_session_state.py`)
Frontend: colocated `__tests__/` folders next to the modules they test

## DDD — Domain-Driven Design

### Ubiquitous Language

These terms have precise meaning across all code, tests, API, and UI. Use them consistently — never invent synonyms.

| Domain Term | Meaning | NOT |
|---|---|---|
| **Session** | A complete problem-solving interaction from submission to resolution | "conversation", "chat", "thread" |
| **Gate** | One of 3 mandatory analysis steps (decompose, map_conventional, extract_axioms) | "step", "phase", "prerequisite" |
| **Premise** | A non-obvious solution hypothesis generated by the agent | "idea", "suggestion", "proposal", "hypothesis" |
| **Round** | A cycle of 3 premises presented to the user for scoring | "iteration", "batch", "turn" |
| **Buffer** | The in-memory list of premises being assembled before presentation (max 3) | "queue", "cache", "pending list" |
| **Axiom** | A hidden assumption identified by `extract_hidden_axioms` | "assumption" alone (too vague), "belief" |
| **Score** | User's 0.0–10.0 rating of a premise | "rating", "grade", "evaluation" |
| **Winner** | The premise the user selects when triggering "Problem Resolved" | "chosen", "selected", "best" |
| **Spec** | The final .md document generated from the winning premise | "report", "document", "output" |
| **Research** | Real-time web search (via Anthropic built-in `web_search`) to ground or validate premises | "lookup", "google", "browse" |

### Aggregate: Session

`Session` is the aggregate root. All access to `Round` and `Premise` goes through `Session`.

```
Session (aggregate root)
├── owns → Round[] (ordered by round_number)
│   └── owns → Premise[] (exactly 3 per round)
├── tracks → SessionState (in-memory enforcement)
└── stores → message_history (Anthropic conversation for resumption)
```

Rules:
- Never create a `Round` without a `Session`
- Never create a `Premise` without a `Round`
- Never query `Premise` directly by ID across sessions — always scope by `session_id`
- `SessionState` is the domain's enforcement engine — it holds the invariants, not the DB

### Value Objects vs Entities

**Entities** (have identity, persisted):
- `Session` (UUID), `Round` (UUID), `Premise` (UUID)

**Value Objects** (no identity, defined by content):
- `SessionId`, `PremiseScore`, `GateStatus`, `ToolName`, `AnalysisGate`
- `UserInput`, `PremiseScore` (schema), `WinnerInfo`

### Domain Events (for internal communication)

These are not persisted — they're the logical events that drive the agent loop:
- `GateCompleted(gate: AnalysisGate)` — a gate tool finished
- `PremiseAddedToBuffer(index: int, remaining: int)` — generation tool succeeded
- `PremiseRejectedAsObvious(index: int, score: float)` — obviousness_test > 0.6
- `RoundPresented(round_number: int)` — present_round succeeded, resets triggered
- `SessionResolved(winner_title: str)` — user triggered Problem Resolved
These map directly to SSE events emitted to the frontend.

## Architecture: Layered (ADR)

The spec uses layered structure, not vertical slices. This is a deliberate hackathon trade-off: the spec's code examples, imports, and directory structure all assume layers. Follow the spec.

```
backend/app/
├── main.py
├── config.py
├── db/
│   ├── base.py              # SQLAlchemy Base
│   └── session.py            # async session factory
├── models/
│   ├── session.py            # Session ORM (message_history JSON, total_tokens_used, status)
│   ├── round.py              # Round ORM (session_id, round_number)
│   ├── premise.py            # Premise ORM (title, body, premise_type, score, user_comment, is_winner, violated_axiom, cross_domain_source)
│   └── tool_call.py          # ToolCall ORM (logging)
├── schemas/
│   ├── session.py            # SessionCreate, SessionResponse, UserInput, PremiseScore, WinnerInfo
│   └── agent.py
├── api/routes/
│   ├── sessions.py           # CRUD + SSE + user-input + spec download
│   └── context.py
└── services/
    ├── agent_runner.py        # Agentic loop (while True until no tool_use)
    ├── tool_handlers.py       # ToolHandlers class — gate enforcement, buffer, DB writes
    ├── tool_definitions.py    # 17 tool JSON schemas (Anthropic format)
    ├── tools_registry.py      # ALL_TOOLS = analysis + generation + innovation + interaction + memory
    ├── session_state.py       # SessionState dataclass (in-memory per session)
    └── system_prompt.py       # AGENT_SYSTEM_PROMPT constant

frontend/src/
├── api/client.ts
├── types/index.ts
├── hooks/
│   ├── useAgentStream.ts      # SSE consumer, dispatches events by type
│   ├── useSession.ts
│   └── useContextUsage.ts
├── components/
│   ├── ProblemInput.tsx
│   ├── RoundView.tsx          # 3 premise cards + score sliders + "Problem Resolved" button
│   ├── PremiseCard.tsx
│   ├── ScoreSlider.tsx        # 0.0–10.0
│   ├── AskUser.tsx            # question + option buttons + free text
│   ├── ContextMeter.tsx       # token usage bar (1M limit)
│   ├── AgentActivityIndicator.tsx
│   ├── EvoTree.tsx
│   ├── ReportView.tsx
│   └── SpecDownload.tsx
└── pages/
    ├── HomePage.tsx
    ├── SessionPage.tsx
    └── ReportPage.tsx
```

## The 17 Custom Tools + 1 Built-in (5 Categories + Anthropic)

### Analysis Tools (mandatory gates)
| Tool | Purpose |
|---|---|
| `decompose_problem` | Break problem into dimensions, constraints, metrics |
| `map_conventional_approaches` | Map obvious approaches to AVOID |
| `extract_hidden_axioms` | Identify hidden assumptions; results feed `challenge_axiom` |

### Generation Tools (gate-checked)
| Tool | Purpose |
|---|---|
| `generate_premise` | Generate ONE premise, add to buffer. ERROR if gates incomplete or buffer full |
| `mutate_premise` | Mutate existing premise (strength 0.1–1.0), add to buffer. Same gate checks |
| `cross_pollinate` | Combine premises, add to buffer. Same gate checks |

### Innovation Tools
| Tool | Purpose |
|---|---|
| `challenge_axiom` | Challenge an extracted axiom. **Unlocks `radical` type premises** |
| `import_foreign_domain` | Find analogy from semantically distant domain |
| `obviousness_test` | Test premise in buffer. **Score > 0.6 = auto-removed, must regenerate** |
| `invert_problem` | Munger's inversion technique |

### Interaction Tools
| Tool | Purpose |
|---|---|
| `ask_user` | Question with selectable options + free text. **Pauses agent loop** |
| `present_round` | Present 3 premises. ERROR if buffer != 3 or any untested. **Pauses agent loop** |
| `generate_final_spec` | Generate .md spec from winner. **Pauses agent loop** |

### Memory Tools
| Tool | Purpose |
|---|---|
| `store_premise` | Save premise with score/comment to DB |
| `query_premises` | Query by filter: all, winners, top_scored, low_scored, by_type, by_round |
| `get_negative_context` | Get premises scored < 5.0. **Must be called before generation in rounds 2+** |
| `get_context_usage` | Token usage stats for the 1M context window |

### Built-in Tool (Anthropic server-side)
| Tool | Purpose |
|---|---|
| `web_search` | Real-time web search via Anthropic API (`web_search_20250305`). **No extra API key** — uses same `ANTHROPIC_API_KEY`. Executed server-side, not by ToolHandlers. $10/1000 searches. **System prompt mandates use before and during premise generation** — not a code-enforced gate, but a hard behavioral rule to eliminate training-data bias. |

## Enforcement Rules (Non-Obvious)

These are enforced server-side in `tool_handlers.py`. The agent receives ERROR responses when violated:

1. **Gate check**: `generate_premise`, `mutate_premise`, `cross_pollinate` → ERROR `GATES_NOT_SATISFIED` if any of the 3 analysis tools hasn't been called
2. **Buffer limit**: generation tools → ERROR `ROUND_BUFFER_FULL` if buffer already has 3
3. **Radical prerequisite**: generating with `premise_type: "radical"` → ERROR `AXIOM_NOT_CHALLENGED` if `challenge_axiom` wasn't called
4. **Negative context**: rounds 2+ generation → ERROR `NEGATIVE_CONTEXT_MISSING` if `get_negative_context` wasn't called
5. **Obviousness threshold**: `obviousness_test` with score > 0.6 → **auto-removes premise from buffer**, returns `REJECTED`/`TOO_OBVIOUS`
6. **Present validation**: `present_round` → ERROR `INCOMPLETE_ROUND` if buffer != 3, ERROR `UNTESTED_PREMISES` if any premise not tested

### Per-Round Reset (happens inside `present_round`)
After presenting, these flags reset for the next round:
- `current_round_buffer` → cleared
- `obviousness_tested` → cleared
- `axiom_challenged` → `False`
- `negative_context_fetched` → `False`
- `current_round_number` → incremented (starts at 0)

## API Contract

### Endpoints
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/sessions` | Create session. Body: `{problem: str}`. Returns `{id, problem, status}` |
| `GET` | `/api/v1/sessions/{id}/stream` | Initial SSE stream — triggers gates + round 1 |
| `POST` | `/api/v1/sessions/{id}/user-input` | Send user response. Body: `UserInput` (see below) |
| `GET` | `/api/v1/sessions/{id}/spec` | Download final .md spec file |

### UserInput Types
```python
class UserInput(BaseModel):
    type: str  # "scores" | "ask_user_response" | "resolved"
    scores: list[PremiseScore] | None       # when type == "scores"
    response: str | None                     # when type == "ask_user_response"
    winner: WinnerInfo | None                # when type == "resolved"
```

### SSE Event Types (emitted by `AgentRunner.run()`)
| Event | Data | When |
|---|---|---|
| `agent_text` | `str` | Agent produces text output |
| `tool_call` | `{tool, input_preview}` | Agent calls a tool |
| `tool_error` | `{tool, error_code, message}` | Tool returned error (gates, buffer, etc) |
| `tool_result` | tool output summary | Tool succeeded |
| `premises` | `list[{title, body, premise_type, ...}]` | `present_round` succeeded — render 3 cards |
| `ask_user` | `{question, options, allow_free_text, context}` | `ask_user` called — render question UI |
| `final_spec` | `str` (markdown) | `generate_final_spec` — render spec + download |
| `context_usage` | `{tokens_used, tokens_limit, ...}` | After every API call |
| `done` | — | Agent turn finished, awaiting user input |

## Agent Runner Loop

`AgentRunner.run()` is an async generator that yields SSE events:

1. Build messages from `session.message_history` + new user message
2. `while True`: call `anthropic.messages.create(model, system, tools, messages)`
3. Count tokens: `session.total_tokens_used += input_tokens + output_tokens`
4. Process response blocks: text → yield `agent_text`; tool_use → execute via `ToolHandlers`
5. If no tool_use blocks → yield `done`, break
6. If interaction tool paused (present_round, ask_user, generate_final_spec) → save `session.message_history`, yield `done`, break
7. Otherwise → append assistant + tool_results to messages, continue loop

Key details:
- Uses `anthropic.AsyncAnthropic().messages.create()` (not streaming API)
- SSE delivery to frontend is separate from Anthropic API streaming
- `ToolHandlers` is instantiated fresh each loop iteration
- Assistant content serialized via `block.model_dump()` for message history
- Tool results: `{"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}`

## Session State (ADR)

```python
# ADR: SessionState is in-memory (not DB/Redis)
# Context: hackathon — single-process uvicorn, no multi-worker
# Trade-off: state lost on restart, acceptable for demo
# Implementation: module-level dict in routes (deliberate exception to no-global-state rule)
_session_states: dict[UUID, SessionState] = {}
```

`SessionState` dataclass tracks per session:
- `completed_gates: set[AnalysisGate]` — which of the 3 gates passed
- `current_round_buffer: list[dict]` — premises awaiting present_round (max 3)
- `current_round_number: int` — starts 0, increments on present_round
- `obviousness_tested: set[int]` — buffer indices that passed the test
- `extracted_axioms: list[str]` — axiom strings from extract_hidden_axioms
- `axiom_challenged: bool` — unlocks radical premise type
- `negative_context_fetched: bool` — unlocks generation in rounds 2+
- `awaiting_user_input: bool` / `awaiting_input_type: str` — pause state

## Database Models

**Session**: `id` (UUID PK), `problem` (text), `status` (str: created/active/resolved), `message_history` (JSON — full Anthropic message array for resumption), `total_tokens_used` (int), `resolved_at` (datetime nullable), `rounds` (relationship)

**Round**: `id` (UUID PK), `session_id` (FK), `round_number` (int)

**Premise**: `id` (UUID PK), `round_id` (FK), `session_id` (FK), `title` (str), `body` (text), `premise_type` (str: initial/conservative/radical/combination), `score` (float nullable, 0.0–10.0), `user_comment` (text nullable), `is_winner` (bool), `violated_axiom` (str nullable), `cross_domain_source` (str nullable), `created_at` (datetime)

**ToolCall**: logging table for tool invocations

## Agent System Prompt

Lives in `services/system_prompt.py`. Key aspects:
- Personality: "Direct, no fluff. Each premise should make the user think 'I wouldn't have thought of that'. Never generate the obvious."
- The prompt explains the 6 inviolable rules (gates, buffer, obviousness, radical prerequisite, negative context, round flow)
- **Web research is mandatory in the prompt** (not code-enforced): the agent MUST search the web after gates and before/during premise generation to ground every premise in real-world evidence and avoid training-data bias
- The agent decides tool order freely — there is no hardcoded pipeline
- On "Problem Resolved": respond enthusiastically, then call `generate_final_spec` with complete Markdown (8 sections: Executive Summary, Problem, Solution, How It Works, Implementation, Risks, Metrics, Evolutionary Journey)

## Environment

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://ghostpath:ghostpath@db:5432/ghostpath
```

Docker Compose services: `backend` (FastAPI/Uvicorn), `frontend` (Vite dev or nginx), `db` (PostgreSQL 18).

Backend needs CORS configured for frontend origin. Specs saved to `/tmp/ghostpath/specs/{session_id}.md`.
