"""Research Digest — compact summaries of past research for phase transition context.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Token budget: ~20 tokens per entry, ~200 tokens max for 10 entries
    - Empty archive or no matches -> empty string

Design Decisions:
    - Separate from phase_digest.py: distinct concern, own test file (ADR: ExMA locality)
    - Phase-filtered: caller specifies which phase's research to show
    - None phase_filter shows all entries (for cross-phase summaries)
    - Same inline i18n pattern as phase_digest.py (PT_BR header from format_messages_pt_br)
"""

from app.core.domain_types import Locale
from app.core import format_messages_pt_br as _pt_br

_SUMMARY_TRUNCATE = 100


def _format_entry_compact(entry: dict) -> str:
    """Format a single research entry as a compact one-liner.

    Format: [phase] query → summary[:100]
    """
    phase = entry.get("phase", "?")
    query = entry.get("query", "")
    summary = entry.get("summary", "")[:_SUMMARY_TRUNCATE]
    return f"  [{phase}] {query} → {summary}"


def build_research_digest(
    research_archive: list[dict],
    phase_filter: str | None,
    locale: Locale,
) -> str:
    """Build compact digest of research entries, optionally filtered by phase.

    Returns empty string if no entries match.
    """
    if not research_archive:
        return ""

    if phase_filter is not None:
        entries = [e for e in research_archive if e.get("phase") == phase_filter]
    else:
        entries = list(research_archive)

    if not entries:
        return ""

    pt = locale == Locale.PT_BR
    header = _pt_br.DIGEST_RESEARCH_HEADER if pt else "Previous phase research:"
    lines = [header] + [_format_entry_compact(e) for e in entries]
    return "\n" + "\n".join(lines) + "\n"
