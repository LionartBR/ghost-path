"""Infrastructure Layer — external service clients and cross-cutting concerns.

Invariants:
    - Infrastructure never imports from core/ domain logic
    - All external calls wrapped with retry/timeout/error mapping

Design Decisions:
    - Resilient wrappers over raw clients (ADR: ExMA single responsibility)
"""
