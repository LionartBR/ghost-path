"""Explore Handlers — Phase 2 tool implementations (4 methods).

Invariants:
    - search_cross_domain enforces web_search gate (Rule #13)
    - Morphological box requires >= 3 parameters x >= 3 values
    - Cross-domain search count tracked for Phase 2 completion gate

Design Decisions:
    - Analogies and contradictions persisted to DB for Knowledge Document generation
    - ForgeState updated in-memory for enforcement; DB for persistence
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.core.repository_protocols import SessionLike
from app.core.enforce_phases import check_web_search
from app.models.cross_domain_analogy import CrossDomainAnalogy
from app.models.contradiction import Contradiction


class ExploreHandlers:
    """Phase 2: EXPLORE — morphological box, cross-domain search, contradictions."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def build_morphological_box(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Map parameter space (Zwicky's morphological analysis)."""
        parameters = input_data.get("parameters", [])

        if len(parameters) < 3:
            return {
                "status": "error",
                "error_code": "INSUFFICIENT_PARAMETERS",
                "message": f"Need >= 3 parameters, got {len(parameters)}.",
            }

        for param in parameters:
            values = param.get("values", [])
            if len(values) < 3:
                return {
                    "status": "error",
                    "error_code": "INSUFFICIENT_VALUES",
                    "message": f"Parameter '{param.get('name')}' needs >= 3 values, got {len(values)}.",
                }

        self.state.morphological_box = {"parameters": parameters}

        return {
            "status": "ok",
            "parameters": parameters,
            "total_combinations": _count_combinations(parameters),
        }

    async def search_cross_domain(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Find analogies in distant domain. Gate: requires web_search (Rule #13)."""
        error = check_web_search(self.state, "cross_domain")
        if error:
            return error

        source_domain = input_data.get("source_domain", "")
        target_application = input_data.get("target_application", "")
        analogy_description = input_data.get("analogy_description", "")
        semantic_distance = input_data.get("semantic_distance", "medium")

        analogy_data = {
            "domain": source_domain,
            "target_application": target_application,
            "description": analogy_description,
            "semantic_distance": semantic_distance,
            "starred": False,
        }
        self.state.cross_domain_analogies.append(analogy_data)
        self.state.cross_domain_search_count += 1

        # Persist to DB
        analogy = CrossDomainAnalogy(
            session_id=session.id,
            source_domain=source_domain,
            target_application=target_application,
            analogy_description=analogy_description,
            semantic_distance=semantic_distance,
        )
        self.db.add(analogy)

        return {
            "status": "ok",
            "source_domain": source_domain,
            "analogy_description": analogy_description,
            "cross_domain_searches_done": self.state.cross_domain_search_count,
        }

    async def identify_contradictions(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Find competing requirements (TRIZ contradiction)."""
        property_a = input_data.get("property_a", "")
        property_b = input_data.get("property_b", "")
        description = input_data.get("description", "")

        contradiction_data = {
            "property_a": property_a,
            "property_b": property_b,
            "description": description,
        }
        self.state.contradictions.append(contradiction_data)

        # Persist to DB
        contradiction = Contradiction(
            session_id=session.id,
            property_a=property_a,
            property_b=property_b,
            description=description,
        )
        self.db.add(contradiction)

        return {
            "status": "ok",
            "property_a": property_a,
            "property_b": property_b,
            "total_contradictions": len(self.state.contradictions),
        }

    async def map_adjacent_possible(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Map what's one step from current knowledge."""
        current_capability = input_data.get("current_capability", "")
        adjacent_possibility = input_data.get("adjacent_possibility", "")
        prerequisites = input_data.get("prerequisites", [])

        entry = {
            "current_capability": current_capability,
            "adjacent_possibility": adjacent_possibility,
            "prerequisites": prerequisites,
        }
        self.state.adjacent_possible.append(entry)

        return {
            "status": "ok",
            "adjacent_possibility": adjacent_possibility,
            "prerequisites": prerequisites,
            "total_adjacent": len(self.state.adjacent_possible),
        }


def _count_combinations(parameters: list[dict]) -> int:
    """Count total morphological combinations."""
    result = 1
    for param in parameters:
        result *= len(param.get("values", []))
    return result
