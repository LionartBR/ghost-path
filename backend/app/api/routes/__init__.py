"""Route Modules — one file per resource/concern.

Invariants:
    - Each module defines its own APIRouter with prefix and tags
    - Routes never contain business logic (delegate to services/helpers)

Design Decisions:
    - Explicit registration in main.py over auto-discovery (ADR: ExMA anti-pattern)
"""
