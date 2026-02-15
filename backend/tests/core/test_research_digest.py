"""Research Digest tests — compact summaries of past research for phase transitions.

Tests cover:
    - Empty archive returns empty string
    - Single entry formatted as compact one-liner
    - Phase filtering limits entries to requested phase only
    - No matches for phase returns empty string
    - Summary truncation to 100 chars
    - Entry format includes phase tag and query
    - PT_BR and EN headers
    - None phase filter shows all entries
    - Multiple entries from same phase listed together

Design Decisions:
    - ForgeState populated inline per test (no shared fixtures — project pattern)
    - Covers both locales explicitly (EN and PT_BR have different headers)
"""

from app.core.domain_types import Locale
from app.core.research_digest import build_research_digest


def _make_entry(
    query: str = "test query",
    summary: str = "test summary",
    phase: str = "decompose",
    purpose: str = "state_of_art",
    sources: list | None = None,
) -> dict:
    return {
        "query": query,
        "summary": summary,
        "phase": phase,
        "purpose": purpose,
        "sources": sources or [],
    }


def test_empty_archive_returns_empty_digest():
    result = build_research_digest([], "decompose", Locale.EN)
    assert result == ""


def test_single_entry_formatted_compact():
    archive = [_make_entry(query="TRIZ methods", summary="Found 5 methods")]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert "TRIZ methods" in result
    assert "Found 5 methods" in result


def test_filters_entries_by_phase():
    archive = [
        _make_entry(phase="decompose", query="query A"),
        _make_entry(phase="explore", query="query B"),
        _make_entry(phase="decompose", query="query C"),
    ]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert "query A" in result
    assert "query C" in result
    assert "query B" not in result


def test_no_matches_for_phase_returns_empty():
    archive = [_make_entry(phase="explore")]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert result == ""


def test_truncates_summary_to_100_chars():
    long_summary = "A" * 200
    archive = [_make_entry(summary=long_summary)]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert "A" * 100 in result
    assert "A" * 101 not in result


def test_includes_phase_tag_and_query():
    archive = [_make_entry(query="cache invalidation", phase="decompose")]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert "decompose" in result
    assert "cache invalidation" in result


def test_pt_br_header():
    archive = [_make_entry()]
    result = build_research_digest(archive, "decompose", Locale.PT_BR)
    assert "Pesquisas da fase anterior:" in result


def test_en_header():
    archive = [_make_entry()]
    result = build_research_digest(archive, "decompose", Locale.EN)
    assert "Previous phase research:" in result


def test_none_phase_filter_shows_all():
    archive = [
        _make_entry(phase="decompose", query="A"),
        _make_entry(phase="explore", query="B"),
        _make_entry(phase="synthesize", query="C"),
    ]
    result = build_research_digest(archive, None, Locale.EN)
    assert "A" in result
    assert "B" in result
    assert "C" in result


def test_multiple_entries_from_same_phase():
    archive = [
        _make_entry(phase="explore", query="biology analogies"),
        _make_entry(phase="explore", query="music theory patterns"),
        _make_entry(phase="explore", query="architecture principles"),
    ]
    result = build_research_digest(archive, "explore", Locale.EN)
    assert "biology analogies" in result
    assert "music theory patterns" in result
    assert "architecture principles" in result
