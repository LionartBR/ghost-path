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

    pt = locale == Locale.PT_BR
    _RESUME = {
        Phase.EXPLORE: (
            _pt_br.RESUME_EXPLORE if pt else
            "Continue Phase 2 (EXPLORE). Build a morphological box, "
            "search >= 2 distant domains for analogies (use "
            "web_search first), identify contradictions, and map "
            "the adjacent possible."
        ),
        Phase.SYNTHESIZE: (
            _pt_br.RESUME_SYNTHESIZE if pt else
            "Continue Phase 3 (SYNTHESIZE). For each promising "
            "direction, state a thesis (with evidence), find "
            "antithesis (use web_search), then create a synthesis "
            "claim. Generate up to 3 claims this round."
        ),
        Phase.VALIDATE: (
            _pt_br.RESUME_VALIDATE if pt else
            "Continue Phase 4 (VALIDATE). For each claim, attempt "
            "falsification (use web_search to disprove), check "
            "novelty (use web_search), then score each claim."
        ),
        Phase.BUILD: (
            _pt_br.RESUME_BUILD if pt else
            "Continue Phase 5 (BUILD). Add accepted/qualified "
            "claims to the knowledge graph, analyze gaps, and "
            "present the build review."
        ),
        Phase.CRYSTALLIZE: (
            _pt_br.RESUME_CRYSTALLIZE if pt else
            "Continue Phase 6 (CRYSTALLIZE). Review the working document "
            "sections you've built. Write implementation_guide and "
            "next_frontiers. Polish all sections, then call "
            "generate_knowledge_document."
        ),
    }
    body = _RESUME[phase]
    return f"{locale_prefix}\n\n{body}"
