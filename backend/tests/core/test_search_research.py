"""Search Research Archive tests — keyword-based lookup of past research entries.

Tests cover:
    - Empty keywords returns all entries
    - Keyword match in query field
    - Keyword match in summary field
    - Case-insensitive matching
    - AND logic: all keywords must match
    - Phase filter limits results
    - Purpose filter limits results
    - Combined keyword + phase filter
    - max_results limits output
    - max_results capped at 10
    - Reverse chronological order (most recent first)
    - Token estimate at 300 per result
    - Token warning message format
    - Empty archive returns zero results
    - No matches returns zero results

Design Decisions:
    - Pure core function: no mocks, no fixtures, just data in → data out
    - ForgeState entries built inline per test (project pattern)
"""

from app.core.search_research import search_research_archive


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
        "sources": sources or [{"url": "http://example.com", "title": "Example"}],
    }


def test_empty_keywords_returns_all_entries():
    archive = [_make_entry(query="A"), _make_entry(query="B")]
    result = search_research_archive(archive, [], None, None, 10)
    assert result["total_matches"] == 2
    assert result["returned"] == 2


def test_keyword_match_in_query_field():
    archive = [
        _make_entry(query="TRIZ methods for innovation"),
        _make_entry(query="biology patterns"),
    ]
    result = search_research_archive(archive, ["TRIZ"], None, None, 10)
    assert result["total_matches"] == 1
    assert "TRIZ" in result["results"][0]["query"]


def test_keyword_match_in_summary_field():
    archive = [
        _make_entry(query="general search", summary="Found TRIZ contradiction methods"),
        _make_entry(query="other search", summary="Found nothing relevant"),
    ]
    result = search_research_archive(archive, ["TRIZ"], None, None, 10)
    assert result["total_matches"] == 1
    assert "TRIZ" in result["results"][0]["summary"]


def test_keyword_match_is_case_insensitive():
    archive = [_make_entry(query="TRIZ Methods")]
    result = search_research_archive(archive, ["triz"], None, None, 10)
    assert result["total_matches"] == 1


def test_all_keywords_must_match_for_entry_inclusion():
    archive = [
        _make_entry(query="TRIZ innovation", summary="methods for design"),
        _make_entry(query="TRIZ patterns", summary="biological patterns"),
    ]
    result = search_research_archive(archive, ["TRIZ", "biological"], None, None, 10)
    assert result["total_matches"] == 1
    assert "biological" in result["results"][0]["summary"]


def test_phase_filter_limits_results():
    archive = [
        _make_entry(phase="decompose", query="decompose query"),
        _make_entry(phase="explore", query="explore query"),
    ]
    result = search_research_archive(archive, [], "decompose", None, 10)
    assert result["total_matches"] == 1
    assert result["results"][0]["query"] == "decompose query"


def test_purpose_filter_limits_results():
    archive = [
        _make_entry(purpose="state_of_art", query="art query"),
        _make_entry(purpose="evidence_for", query="evidence query"),
    ]
    result = search_research_archive(archive, [], None, "state_of_art", 10)
    assert result["total_matches"] == 1
    assert result["results"][0]["query"] == "art query"


def test_combined_keyword_and_phase_filter():
    archive = [
        _make_entry(phase="decompose", query="TRIZ in decompose"),
        _make_entry(phase="explore", query="TRIZ in explore"),
        _make_entry(phase="decompose", query="biology in decompose"),
    ]
    result = search_research_archive(archive, ["TRIZ"], "decompose", None, 10)
    assert result["total_matches"] == 1
    assert result["results"][0]["query"] == "TRIZ in decompose"


def test_max_results_limits_output():
    archive = [_make_entry(query=f"query {i}") for i in range(5)]
    result = search_research_archive(archive, [], None, None, 2)
    assert result["total_matches"] == 5
    assert result["returned"] == 2
    assert len(result["results"]) == 2


def test_max_results_capped_at_10():
    """Even if caller passes > 10, cap at 10."""
    archive = [_make_entry(query=f"query {i}") for i in range(15)]
    result = search_research_archive(archive, [], None, None, 20)
    assert result["returned"] == 10


def test_returns_reverse_chronological_order():
    archive = [
        _make_entry(query="first"),
        _make_entry(query="second"),
        _make_entry(query="third"),
    ]
    result = search_research_archive(archive, [], None, None, 10)
    assert result["results"][0]["query"] == "third"
    assert result["results"][1]["query"] == "second"
    assert result["results"][2]["query"] == "first"


def test_token_estimate_300_per_result():
    archive = [_make_entry(query=f"q{i}") for i in range(3)]
    result = search_research_archive(archive, [], None, None, 10)
    assert result["token_estimate"] == 900  # 3 * 300


def test_token_warning_includes_count_and_estimate():
    archive = [_make_entry(query=f"q{i}") for i in range(3)]
    result = search_research_archive(archive, [], None, None, 10)
    assert "3 results" in result["token_warning"]
    assert "900" in result["token_warning"]


def test_empty_archive_returns_zero_results():
    result = search_research_archive([], ["keyword"], None, None, 10)
    assert result["total_matches"] == 0
    assert result["returned"] == 0
    assert result["results"] == []


def test_no_matches_returns_zero_results():
    archive = [_make_entry(query="something else")]
    result = search_research_archive(archive, ["nonexistent"], None, None, 10)
    assert result["total_matches"] == 0
    assert result["returned"] == 0
