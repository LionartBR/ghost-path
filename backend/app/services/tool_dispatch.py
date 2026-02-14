"""Tool Dispatch — explicit routing from tool_name to handler function.

Invariants:
    - Every tool->handler mapping is visible — no getattr magic, no auto-discovery
    - Unknown tools return UNKNOWN_TOOL error (never raises)
    - web_search calls are intercepted and recorded in ForgeState for gate enforcement
    - Every tool call logged to ToolCall ORM for observability
    - Handlers instantiated per-dispatch with shared DB + state context

Design Decisions:
    - Explicit dict over getattr: every mapping visible in one place
      (ADR: ExMA no convention-over-config)
    - Split handlers by phase: max ~4 methods per class
      (ADR: ExMA no god objects)
    - web_search interception: we can't "require" the built-in tool, but we CAN track it
    - Tool call logging wrapped in try/except: never crashes the agent loop
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.services.handle_decompose import DecomposeHandlers
from app.services.handle_explore import ExploreHandlers
from app.services.handle_synthesize import SynthesizeHandlers
from app.services.handle_validate import ValidateHandlers
from app.services.handle_build import BuildHandlers
from app.services.handle_crystallize import CrystallizeHandlers
from app.services.handle_cross_cutting import CrossCuttingHandlers

logger = logging.getLogger(__name__)

# Tools that pause the agent loop (agent yields 'done', waits for user input)
PAUSE_TOOLS = frozenset({"generate_knowledge_document"})


class ToolDispatch:
    """Routes tool_name -> handler. Explicit registration, no auto-discovery."""

    def __init__(
        self, db: AsyncSession, state: ForgeState,
        session_id: UUID | None = None,
    ):
        self._session_id = session_id
        self._db = db
        decompose = DecomposeHandlers(db, state)
        explore = ExploreHandlers(db, state)
        synthesize = SynthesizeHandlers(db, state)
        validate = ValidateHandlers(db, state)
        build = BuildHandlers(db, state)
        crystallize = CrystallizeHandlers(db, state)
        cross_cutting = CrossCuttingHandlers(db, state)

        self._state = state

        # ADR: every mapping explicit — adding a tool requires editing this dict
        self._handlers = {
            # Phase 1: DECOMPOSE (4 tools)
            "decompose_to_fundamentals": decompose.decompose_to_fundamentals,
            "map_state_of_art": decompose.map_state_of_art,
            "extract_assumptions": decompose.extract_assumptions,
            "reframe_problem": decompose.reframe_problem,

            # Phase 2: EXPLORE (4 tools)
            "build_morphological_box": explore.build_morphological_box,
            "search_cross_domain": explore.search_cross_domain,
            "identify_contradictions": explore.identify_contradictions,
            "map_adjacent_possible": explore.map_adjacent_possible,

            # Phase 3: SYNTHESIZE (3 tools)
            "state_thesis": synthesize.state_thesis,
            "find_antithesis": synthesize.find_antithesis,
            "create_synthesis": synthesize.create_synthesis,

            # Phase 4: VALIDATE (3 tools)
            "attempt_falsification": validate.attempt_falsification,
            "check_novelty": validate.check_novelty,
            "score_claim": validate.score_claim,

            # Phase 5: BUILD (3 tools)
            "add_to_knowledge_graph": build.add_to_knowledge_graph,
            "analyze_gaps": build.analyze_gaps,
            "get_negative_knowledge": build.get_negative_knowledge,

            # Phase 6: CRYSTALLIZE (1 tool)
            "generate_knowledge_document": crystallize.generate_knowledge_document,

            # Cross-cutting (3 tools)
            "get_session_status": cross_cutting.get_session_status,
            "submit_user_insight": cross_cutting.submit_user_insight,
            "recall_phase_context": cross_cutting.recall_phase_context,
        }

    def record_web_search(self, query: str, result_summary: str) -> None:
        """Intercept web_search calls for enforcement tracking.

        Called by agent_runner when it detects a web_search tool result
        (server_tool_use / web_search_tool_result blocks).
        """
        self._state.record_web_search(query, result_summary)

    async def execute(
        self, tool_name: str, session: object, input_data: dict,
    ) -> dict:
        """Route tool_name to handler. Returns result dict. Logs every call."""
        handler = self._handlers.get(tool_name)
        if not handler:
            result = {
                "status": "error",
                "error_code": "UNKNOWN_TOOL",
                "message": f"Tool '{tool_name}' does not exist.",
            }
            self._log_tool_call(tool_name, input_data, result)
            return result
        result = await handler(session, input_data)
        self._log_tool_call(tool_name, input_data, result)
        return result

    def _log_tool_call(
        self, tool_name: str, input_data: dict, result: dict,
    ) -> None:
        """Log tool call to DB. No flush — batched with next commit.

        ADR: agent_runner commits at loop exit (_save_state). Flushing per-tool
        added N round-trips to DB per iteration. SQLAlchemy unit-of-work
        accumulates the adds and persists them on commit.
        """
        if not self._session_id:
            return
        try:
            from app.models.tool_call import ToolCall
            is_error = result.get("status") == "error"
            self._db.add(ToolCall(
                session_id=self._session_id,
                tool_name=tool_name,
                tool_input=input_data,
                tool_output=None if is_error else result,
                error_code=result.get("error_code") if is_error else None,
            ))
        except Exception as e:
            logger.warning(f"Failed to log tool call '{tool_name}': {e}")
