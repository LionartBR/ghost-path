"""ORM Models — SQLAlchemy declarative models for all domain entities.

Invariants:
    - All models inherit from Base (db/base.py)
    - Session is the aggregate root; all entities scoped by session_id

Design Decisions:
    - One file per entity for locality (ADR: ExMA max 3-4 files to understand a feature)
    - All models imported here so SQLAlchemy resolves string-based relationship()
      references before any query runs (ADR: standard SQLAlchemy pattern)
"""

from app.models.session import Session  # noqa: F401
from app.models.knowledge_claim import KnowledgeClaim  # noqa: F401
from app.models.evidence import Evidence  # noqa: F401
from app.models.claim_edge import ClaimEdge  # noqa: F401
from app.models.problem_reframing import ProblemReframing  # noqa: F401
from app.models.cross_domain_analogy import CrossDomainAnalogy  # noqa: F401
from app.models.contradiction import Contradiction  # noqa: F401
from app.models.tool_call import ToolCall  # noqa: F401
