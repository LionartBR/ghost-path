"""Tool Dispatch — explicit routing from tool_name to handler function.

Invariants:
    - Every tool→handler mapping is visible — no getattr magic, no auto-discovery
    - Unknown tools return UNKNOWN_TOOL error (never raises)
    - Handlers instantiated per-dispatch with shared DB + state context

Design Decisions:
    - Explicit dict over getattr: every mapping visible in one place
      (ADR: ExMA no convention-over-config)
    - Split handlers by ToolCategory: max ~4 methods per class
      (ADR: ExMA no god objects)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.services.handle_analysis import AnalysisHandlers
from app.services.handle_generation import GenerationHandlers
from app.services.handle_innovation import InnovationHandlers
from app.services.handle_interaction import InteractionHandlers
from app.services.handle_memory import MemoryHandlers


class ToolDispatch:
    """Routes tool_name → handler. Explicit registration, no auto-discovery."""

    def __init__(self, db: AsyncSession, state: SessionState):
        analysis = AnalysisHandlers(db, state)
        generation = GenerationHandlers(db, state)
        innovation = InnovationHandlers(db, state)
        interaction = InteractionHandlers(db, state)
        memory = MemoryHandlers(db, state)

        # ADR: every mapping explicit — adding a tool requires editing this dict
        self._handlers = {
            # Analysis (gates)
            "decompose_problem": analysis.decompose_problem,
            "map_conventional_approaches": (
                analysis.map_conventional_approaches
            ),
            "extract_hidden_axioms": analysis.extract_hidden_axioms,
            # Generation (gate-checked, impureim sandwich)
            "generate_premise": generation.generate_premise,
            "mutate_premise": generation.mutate_premise,
            "cross_pollinate": generation.cross_pollinate,
            # Innovation
            "challenge_axiom": innovation.challenge_axiom,
            "import_foreign_domain": innovation.import_foreign_domain,
            "obviousness_test": innovation.obviousness_test,
            "invert_problem": innovation.invert_problem,
            # Interaction
            "ask_user": interaction.ask_user,
            "present_round": interaction.present_round,
            "generate_final_spec": interaction.generate_final_spec,
            # Memory
            "store_premise": memory.store_premise,
            "query_premises": memory.query_premises,
            "get_negative_context": memory.get_negative_context,
            "get_context_usage": memory.get_context_usage,
        }

    async def execute(
        self, tool_name: str, session, input_data: dict,
    ) -> dict:
        handler = self._handlers.get(tool_name)
        if not handler:
            return {
                "status": "error",
                "error_code": "UNKNOWN_TOOL",
                "message": f"Tool '{tool_name}' does not exist.",
            }
        return await handler(session, input_data)
