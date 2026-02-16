"""Session Lifecycle Messages — initial stream and phase resumption messages.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Every message includes locale prefix with problem excerpt
    - DECOMPOSE resume delegates to build_initial_stream_message (same content)

Design Decisions:
    - Extracted from format_messages.py (ADR: ExMA 400-line limit)
    - PT_BR bodies are fully translated to prevent English context drift
"""

from app.core.domain_types import Locale, Phase
from app.core import format_messages_pt_br as _pt_br


def build_initial_stream_message(
    locale_prefix: str, problem: str, locale: Locale = Locale.EN,
) -> str:
    """Build the initial message for Phase 1 (DECOMPOSE) stream."""
    if locale == Locale.PT_BR:
        body = _pt_br.INITIAL_BODY.format(problem=problem)
    else:
        body = (
            f'The user has submitted the following problem:\n\n'
            f'"{problem}"\n\n'
            f'Begin Phase 1 (DECOMPOSE). Use web_search to research '
            f'the domain, then call decompose_to_fundamentals, '
            f'map_state_of_art, extract_assumptions, and '
            f'reframe_problem (>= 3 reframings). When you are done '
            f'with all decompose tools, output a summary of your '
            f'findings for the user to review.'
        )
    return f'{locale_prefix}\n\n{body}'


def build_resume_message(
    locale_prefix: str, phase: Phase, problem: str,
    locale: Locale = Locale.EN,
) -> str:
    """Build a phase-appropriate message for resuming a session."""
    if phase == Phase.DECOMPOSE:
        return build_initial_stream_message(
            locale_prefix, problem, locale,
        )

    # ADR: lean resume messages — pipeline description already in system prompt.
    # Only the phase name + number is needed; the model sees PIPELINE_* and tools.
    pt = locale == Locale.PT_BR
    _RESUME = {
        Phase.EXPLORE: (
            _pt_br.RESUME_EXPLORE if pt else
            "Continue Phase 2 (EXPLORE)."
        ),
        Phase.SYNTHESIZE: (
            _pt_br.RESUME_SYNTHESIZE if pt else
            "Continue Phase 3 (SYNTHESIZE)."
        ),
        Phase.VALIDATE: (
            _pt_br.RESUME_VALIDATE if pt else
            "Continue Phase 4 (VALIDATE)."
        ),
        Phase.BUILD: (
            _pt_br.RESUME_BUILD if pt else
            "Continue Phase 5 (BUILD)."
        ),
        Phase.CRYSTALLIZE: (
            _pt_br.RESUME_CRYSTALLIZE if pt else
            "Continue Phase 6 (CRYSTALLIZE)."
        ),
    }
    body = _RESUME[phase]
    return f"{locale_prefix}\n\n{body}"
