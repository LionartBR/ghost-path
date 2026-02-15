"""Pydantic Schemas — request/response validation for API endpoints.

Invariants:
    - Schemas validate at system boundary (user input, API responses)
    - Domain types from core/ used for enum fields

Design Decisions:
    - Separate from models: schemas are API contracts, models are persistence (ADR: DDD boundary)
"""
