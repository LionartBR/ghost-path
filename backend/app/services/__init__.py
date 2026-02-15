"""Services Layer — tool handlers, agent runner, and tool dispatch.

Invariants:
    - Handlers split by phase (max 4 methods each)
    - Tool dispatch uses explicit dict mapping (no auto-discovery)

Design Decisions:
    - One handler file per phase for locality (ADR: ExMA no god objects)
"""
