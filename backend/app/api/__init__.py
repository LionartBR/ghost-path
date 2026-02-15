"""API Layer — FastAPI routes and error handlers.

Invariants:
    - Routes registered explicitly in main.py (no auto-discovery)
    - All endpoints return structured JSON responses

Design Decisions:
    - Thin routes delegate to services (ADR: ExMA impureim sandwich)
"""
