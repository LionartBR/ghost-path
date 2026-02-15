"""Core Layer — pure domain logic, no IO, no async, no DB.

Invariants:
    - No module in core/ imports from services/, api/, infrastructure/, or db/
    - All functions are pure and deterministic

Design Decisions:
    - Functional core separated from imperative shell (ADR: ExMA impureim sandwich)
"""
